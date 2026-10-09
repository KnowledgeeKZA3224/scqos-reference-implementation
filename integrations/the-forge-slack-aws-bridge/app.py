"""Supreme Computation Slack/AWS continuity bridge.

Two Lambda handlers:
- archive_handler: verify signed Slack Events API requests and append allowlisted messages to S3.
- notify_handler: send allowlisted AWS SNS alarm notifications into a Slack channel.

Uses AWS Secrets Manager for credentials; never logs bodies or tokens.
"""
import base64
import datetime
import hashlib
import hmac
import json
import os
import re
import time
import urllib.error
import urllib.request

import boto3
from botocore.exceptions import ClientError

_s3 = None
_sm = None


def _clients():
    global _s3, _sm
    if _s3 is None:
        _s3 = boto3.client('s3')
    if _sm is None:
        _sm = boto3.client('secretsmanager')
    return _s3, _sm


def _secret(name):
    _, sm = _clients()
    return sm.get_secret_value(SecretId=os.environ[name])['SecretString'].strip()


def _env(name):
    value = os.environ.get(name, '').strip()
    if not value:
        raise ValueError(f'Missing configuration: {name}')
    return value


def _body(event):
    body = event.get('body') or ''
    if event.get('isBase64Encoded'):
        return base64.b64decode(body, validate=True)
    return body.encode('utf-8') if isinstance(body, str) else body


def _headers(event):
    return {k.lower(): str(v) for k, v in (event.get('headers') or {}).items() if v is not None}


def _signed(payload, headers, signing_secret, now=None):
    timestamp = headers.get('x-slack-request-timestamp', '')
    sig = headers.get('x-slack-signature', '')
    if not timestamp.isascii() or not timestamp.isdecimal() or not sig.startswith('v0='):
        return False
    now = int(now if now is not None else time.time())
    if abs(now - int(timestamp)) > 300:
        return False
    base = b'v0:' + timestamp.encode('ascii') + b':' + payload
    expected = 'v0=' + hmac.new(signing_secret.encode(), base, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def _http(status, obj):
    return {'statusCode': status, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps(obj)}


def _key(event_id):
    # Event-derived key is independent of the receive date: retries across midnight
    # cannot create a second archive object for the same Slack event.
    token = hashlib.sha256(event_id.encode('utf-8')).hexdigest()
    return f"{_env('ARCHIVE_PREFIX').rstrip('/')}/events/by-id/{token[:2]}/{token}.json"


def _put_immutable(key, data, sha):
    s3, _ = _clients()
    try:
        return s3.put_object(
            Bucket=_env('ARCHIVE_BUCKET'), Key=key, Body=data,
            ContentType='application/json', ServerSideEncryption='AES256',
            Metadata={'sha256': sha}, IfNoneMatch='*',
        ), True
    except ClientError as exc:
        code = exc.response.get('Error', {}).get('Code', '')
        if code in ('PreconditionFailed', '412'):
            return {}, False
        raise


def archive_handler(event, context):
    try:
        payload = _body(event)
        if len(payload) > 1024 * 1024:
            return _http(413, {'status': 'REJECT', 'reason': 'payload_limit'})
        if not _signed(payload, _headers(event), _secret('SLACK_SIGNING_SECRET_ARN')):
            return _http(401, {'status': 'REJECT', 'reason': 'signature_or_time'})
        doc = json.loads(payload)
        if doc.get('team_id') != _env('SLACK_TEAM_ID'):
            return _http(403, {'status': 'REJECT', 'reason': 'workspace_boundary'})
        if doc.get('type') == 'url_verification':
            return _http(200, {'challenge': doc.get('challenge', '')})
        if doc.get('type') != 'event_callback':
            return _http(200, {'status': 'IGNORED'})
        item = doc.get('event') or {}
        if item.get('type') != 'message':
            return _http(200, {'status': 'IGNORED'})
        channel = item.get('channel', '')
        allowed = set(_env('ARCHIVE_CHANNEL_IDS').split(','))
        if channel not in allowed:
            return _http(200, {'status': 'HOLD', 'reason': 'channel_not_allowlisted'})
        event_id = doc.get('event_id') or ''
        if not re.fullmatch(r'Ev[A-Za-z0-9]{5,128}', event_id):
            return _http(400, {'status': 'REJECT', 'reason': 'missing_event_identity'})
        # Save original signed envelope, not a possibly lossy transformation.
        sha = hashlib.sha256(payload).hexdigest()
        key = _key(event_id)
        receipt, created = _put_immutable(key, payload, sha)
        # No message text appears in logs or responses. Conditional put is replay-safe.
        print(json.dumps({'event': 'slack_archive', 'decision': 'COMMITTED' if created else 'DUPLICATE',
                          'key': key, 'sha256': sha, 'request_id': receipt.get('ResponseMetadata', {}).get('RequestId')}))
        return _http(200, {'status': 'COMMITTED' if created else 'ALREADY_COMMITTED', 'sha256': sha})
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, UnicodeDecodeError, base64.binascii.Error):
        return _http(400, {'status': 'REJECT', 'reason': 'invalid_input_or_configuration'})


def _post_slack(text):
    body = json.dumps({'channel': _env('NOTIFY_CHANNEL_ID'), 'text': text, 'unfurl_links': False}).encode()
    request = urllib.request.Request('https://slack.com/api/chat.postMessage',
                data=body, headers={'Authorization': 'Bearer ' + _secret('SLACK_BOT_TOKEN_ARN'),
                                    'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(request, timeout=10) as r:
        answer = json.load(r)
    if not answer.get('ok') or not answer.get('ts'):
        raise RuntimeError('Slack API delivery not acknowledged')
    return answer['ts']


def notify_handler(event, context):
    allowed_topic = _env('SNS_TOPIC_ARN')
    records = event.get('Records') or []
    if not records:
        raise ValueError('Missing SNS record')
    successes = []
    for record in records:
        sns = record.get('Sns') or {}
        if record.get('EventSource') != 'aws:sns' or sns.get('TopicArn') != allowed_topic:
            raise ValueError('Non-allowlisted notification source')
        message_id = sns.get('MessageId') or ''
        if not message_id:
            raise ValueError('Missing SNS message identity')
        raw = sns.get('Message') or ''
        try:
            alarm = json.loads(raw)
        except json.JSONDecodeError:
            raise ValueError('Unexpected SNS message format')
        name = alarm.get('AlarmName', '')
        state = alarm.get('NewStateValue', '')
        if not isinstance(name, str) or not name.startswith(_env('ALARM_NAME_PREFIX')):
            raise ValueError('Alarm outside allowed scope')
        if state not in ('ALARM', 'OK', 'INSUFFICIENT_DATA'):
            raise ValueError('Invalid alarm state')
        # Only whitelisted fields; avoid posting potentially secret-filled descriptions or raw SNS payloads.
        text = f"SC Cloud Signal | {name[:150]} | {state} | UTC {datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}"
        ts = _post_slack(text)
        witness = json.dumps({'sns_message_id': message_id, 'alarm': name, 'state': state,
                              'slack_ts': ts, 'workspace': _env('SLACK_TEAM_ID')}, sort_keys=True).encode()
        sha = hashlib.sha256(witness).hexdigest()
        key = f"{_env('ARCHIVE_PREFIX').rstrip('/')}/receipts/sns/{hashlib.sha256(message_id.encode()).hexdigest()}.json"
        receipt, created = _put_immutable(key, witness, sha)
        successes.append({'message_id': message_id, 'receipt_committed': created})
    return {'status': 'DELIVERED_AND_WITNESSED', 'records': successes}
