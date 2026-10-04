#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scqos_acs_lab.client import ACSClient, iso_now

DIRECT_IDS = {
    'v0577dc8ccd4d7e47', # valid-signature positive control
    'vb87b86b4930665ca', # invalid signature
    'vd67cd207a4eb6798', # signature covers subset
    'vf80a81054d3f0862', # signature absent
    'vef655ce2a45f618b', # replay
    'va6d6e952d417c5a1', # within timestamp window
    'vb10df32610db1173', # stale timestamp
    'v78927805373a6c06', # supported version handshake
    'v412653087b92cb07', # unsupported version handshake
}


def expected_match(vector: dict[str, Any], response: dict[str, Any]) -> bool:
    expected = vector['expected']
    code_value = expected.get('codeValue')
    verdict = expected.get('verdict')
    if code_value is not None:
        return response.get('error', {}).get('code') == code_value
    if verdict == 'allow':
        if vector['payload'].get('request', {}).get('method') == 'handshake/hello':
            return isinstance(response.get('result'), dict) and response['result'].get('negotiated_version') == '0.1.0'
        return response.get('result', {}).get('decision') == 'allow'
    if verdict == 'deny':
        return response.get('result', {}).get('decision') == 'deny' or isinstance(response.get('error'), dict)
    return False


def convert_tool_request(client: ACSClient, vector: dict[str, Any], *, request_id: str | None = None) -> dict[str, Any]:
    payload = vector['payload']
    old = payload.get('request') or payload.get('steps', [{}])[0].get('request')
    old_tool = old.get('params', {}).get('tool', {})
    target = 'acs://external-vector/' + vector['id']
    args = {
        'target': {'value': target},
        'effect': {'value': 'invoke:' + old_tool.get('name', 'records.lookup')},
        'evidence_present': {'value': True},
        'source_vector': {'value': vector['id']},
    }
    current_payload = {
        'tool': {'name': old_tool.get('name', 'records.lookup'), 'version': 'external-vector'},
        'capability': 'lab.transition',
        'arguments': args,
        'intent': {'description': 'adapted external ACS-Core vector', 'goal': 'exercise wire requirement'},
    }
    timestamp = None
    if vector['id'] == 'va6d6e952d417c5a1':
        timestamp = iso_now(-60)
    elif vector['id'] == 'vb10df32610db1173':
        timestamp = iso_now(-3600)
    sign = vector['id'] != 'vf80a81054d3f0862'
    env = client.envelope('steps/toolCallRequest', current_payload, request_id=request_id, timestamp=timestamp, sign=sign)
    if vector['id'] in {'vb87b86b4930665ca', 'vd67cd207a4eb6798'}:
        env['params']['signature']['value'] = 'AAAA'
    return env


def run(corpus: Path, endpoint: str, output: Path) -> int:
    vectors = {p.stem: json.loads(p.read_text()) for p in (corpus/'vectors').glob('*.json')}
    client = ACSClient(endpoint=endpoint, agent_id='external-vector-adapter')
    base_hs = client.handshake()
    rows = []
    for vid in sorted(vectors):
        v = vectors[vid]
        if vid not in DIRECT_IDS:
            rows.append({'id': vid, 'status':'NOT_DRIVEN', 'reason':'vector depends on policy/framework/artifact semantics outside the direct ACS wire surface exercised by this adapter', 'expected':v['expected']})
            continue
        if vid in {'v78927805373a6c06','v412653087b92cb07'}:
            versions = ['0.1.0'] if vid == 'v78927805373a6c06' else ['1.0.0']
            c = ACSClient(endpoint=endpoint, agent_id='external-vector-handshake')
            response = c.handshake(versions=versions)
        elif vid == 'vef655ce2a45f618b':
            rid = '11111111-1111-4111-8111-111111111111'
            env = convert_tool_request(client, v, request_id=rid)
            first = client.send(env)
            response = client.send(env, update_chain=False)
        else:
            env = convert_tool_request(client, v)
            response = client.send(env, update_chain=False)
        rows.append({
            'id':vid,
            'status':'PASS' if expected_match(v,response) else 'FAIL',
            'expected':v['expected'],
            'observed':response,
            'requirements':v.get('requirements',[]),
            'family':v.get('family'),
        })
    driven=[r for r in rows if r['status']!='NOT_DRIVEN']
    result={
        'schema':'scqos.acs.external-vector-adapter-run.v1',
        'corpus':str(corpus),
        'endpoint':endpoint,
        'baseline_handshake':base_hs,
        'directly_driven':len(driven),
        'passed':sum(r['status']=='PASS' for r in driven),
        'failed':sum(r['status']=='FAIL' for r in driven),
        'not_driven':sum(r['status']=='NOT_DRIVEN' for r in rows),
        'rows':rows,
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:result[k] for k in ('directly_driven','passed','failed','not_driven')},indent=2))
    return 0 if result['failed']==0 else 2


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--corpus',required=True)
    ap.add_argument('--endpoint',required=True)
    ap.add_argument('--output',required=True)
    args=ap.parse_args()
    return run(Path(args.corpus),args.endpoint,Path(args.output))

if __name__=='__main__':
    raise SystemExit(main())
