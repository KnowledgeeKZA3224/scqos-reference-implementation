#!/usr/bin/env python3
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from scqos_acs_lab.client import ACSClient


def main() -> int:
    run_id = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex[:8]
    client = ACSClient(endpoint='http://127.0.0.1:18888/acs', agent_id='cloud-action-probe')
    handshake = client.handshake()

    records = []

    valid_env, valid_resp = client.tool(
        target=f's3://scqos-acs-falsification/{run_id}/permit.txt',
        effect='create:permit-proof',
    )
    records.append({'name':'permit','key':f'runs/{run_id}/actions/permit.txt','request':valid_env,'response':valid_resp})

    deny_env, deny_resp = client.tool(
        target=f's3://scqos-acs-falsification/{run_id}/deny.txt',
        effect='create:deny-proof',
        roles=['read:only'],
    )
    records.append({'name':'deny','key':f'runs/{run_id}/actions/deny.txt','request':deny_env,'response':deny_resp})

    hold_env, hold_resp = client.tool(
        target=f's3://scqos-acs-falsification/{run_id}/hold.txt',
        effect='create:hold-proof',
        evidence_present=False,
    )
    records.append({'name':'hold','key':f'runs/{run_id}/actions/hold.txt','request':hold_env,'response':hold_resp})

    replay_env = client.envelope('steps/toolCallRequest', {
        'tool': {'name':'lab.write','version':'1'},
        'capability':'lab.transition',
        'arguments': {
            'target': {'value':f's3://scqos-acs-falsification/{run_id}/replay.txt'},
            'effect': {'value':'create:replay-proof'},
            'evidence_present': {'value':True},
        },
        'intent': {'description':'replay falsification case','goal':'create exactly once'},
    })
    replay_first = client.send(replay_env)
    replay_second = client.send(replay_env, update_chain=False)
    records.append({'name':'replay_first','key':f'runs/{run_id}/actions/replay.txt','request':replay_env,'response':replay_first})
    records.append({'name':'replay_second','key':f'runs/{run_id}/actions/replay.txt','request':replay_env,'response':replay_second})

    result = {
        'schema':'scqos.acs.cloud-action-plan.v1',
        'run_id':run_id,
        'guardian':'http://127.0.0.1:18888/acs',
        'handshake':handshake,
        'records':records,
    }
    path = Path('run-evidence/cloud-action-plan.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({
        'run_id':run_id,
        'records':[{
            'name':r['name'],
            'key':r['key'],
            'decision':r['response'].get('result',{}).get('decision'),
            'error':r['response'].get('error',{}).get('code'),
        } for r in records]
    }, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
