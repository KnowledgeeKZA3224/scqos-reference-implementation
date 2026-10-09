import hashlib
import hmac
import json
import os
import sys
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import app


class FakeS3:
    def __init__(self):
        self.items = {}
    def put_object(self, **kw):
        from botocore.exceptions import ClientError
        if kw['Key'] in self.items:
            raise ClientError({'Error': {'Code': 'PreconditionFailed'}}, 'PutObject')
        self.items[kw['Key']] = kw
        return {'ResponseMetadata': {'RequestId': 'req-test'}}

class FakeSecrets:
    def get_secret_value(self, SecretId):
        return {'SecretString': {'signing': 'my-signing-secret', 'bot': 'test-bot'}[SecretId]}

class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.s3 = FakeS3()
        self.p1 = patch.object(app, '_clients', return_value=(self.s3, FakeSecrets()))
        self.p2 = patch.dict(os.environ, {
            'SLACK_SIGNING_SECRET_ARN': 'signing', 'SLACK_BOT_TOKEN_ARN': 'bot',
            'SLACK_TEAM_ID': 'T_TEST123', 'ARCHIVE_BUCKET': 'private-test',
            'ARCHIVE_PREFIX': 'bridge', 'ARCHIVE_CHANNEL_IDS': 'C_TEST123',
            'NOTIFY_CHANNEL_ID': 'C123', 'SNS_TOPIC_ARN': 'arn:aws:sns:us-east-1:123:topic',
            'ALARM_NAME_PREFIX': 'SC-'})
        self.p1.start(); self.p2.start()
        self.addCleanup(self.p1.stop); self.addCleanup(self.p2.stop)
    def event(self, channel='C_TEST123', offset=0, sign=True):
        payload=json.dumps({'type':'event_callback','team_id':'T_TEST123',
                            'event_id':'Ev123456789','event':{'type':'message','channel':channel,'text':'test'}})
        timestamp=str(int(time.time())+offset)
        sig='v0='+hmac.new(b'my-signing-secret',('v0:'+timestamp+':'+payload).encode(),hashlib.sha256).hexdigest()
        return {'headers': {'X-Slack-Request-Timestamp':timestamp,
                            'X-Slack-Signature':sig if sign else 'v0=bad'}, 'body':payload}
    def test_message_commits_once(self):
        event=self.event()
        first=app.archive_handler(event, None)
        self.assertEqual(json.loads(first['body'])['status'],'COMMITTED')
        self.assertEqual(len(self.s3.items),1)
        second=app.archive_handler(event, None)
        self.assertEqual(json.loads(second['body'])['status'],'ALREADY_COMMITTED')
        self.assertEqual(len(self.s3.items),1)
        obj=next(iter(self.s3.items.values()))
        self.assertEqual(obj['Metadata']['sha256'],hashlib.sha256(event['body'].encode()).hexdigest())
    def test_unsigned_fails(self):
        self.assertEqual(app.archive_handler(self.event(sign=False), None)['statusCode'],401)
        self.assertFalse(self.s3.items)
    def test_stale_fails(self):
        self.assertEqual(app.archive_handler(self.event(offset=-600), None)['statusCode'],401)
    def test_channel_hold(self):
        r=app.archive_handler(self.event(channel='C_ELSE'), None)
        self.assertEqual(json.loads(r['body'])['status'],'HOLD')
        self.assertFalse(self.s3.items)
    def test_workspace_rejected(self):
        ev=self.event()
        data=json.loads(ev['body']); data['team_id']='T_OTHER'
        ev['body']=json.dumps(data)
        ts=ev['headers']['X-Slack-Request-Timestamp']
        ev['headers']['X-Slack-Signature']='v0='+hmac.new(b'my-signing-secret',('v0:'+ts+':'+ev['body']).encode(),hashlib.sha256).hexdigest()
        self.assertEqual(app.archive_handler(ev, None)['statusCode'],403)
    def test_notify_source_is_gated(self):
        evt={'Records':[{'EventSource':'aws:sns','Sns':{'TopicArn':'arn:other','MessageId':'test',
                                                        'Message':json.dumps({'AlarmName':'SC-Test','NewStateValue':'ALARM'})}}]}
        with self.assertRaises(ValueError):app.notify_handler(evt,None)
    def test_notify_witness(self):
        evt={'Records':[{'EventSource':'aws:sns','Sns':{'TopicArn':'arn:aws:sns:us-east-1:123:topic','MessageId':'test',
                                                        'Message':json.dumps({'AlarmName':'SC-Test','NewStateValue':'ALARM'})}}]}
        with patch.object(app,'_post_slack',return_value='1699999999.000001') as send:
            r=app.notify_handler(evt,None)
        self.assertEqual(r['status'],'DELIVERED_AND_WITNESSED')
        self.assertEqual(len(self.s3.items),1)
        send.assert_called_once()
if __name__=='__main__': unittest.main()
