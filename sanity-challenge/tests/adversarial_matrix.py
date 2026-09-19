from agent.gate_adapter import evaluate
base={'question':'What is proven?','agent':'sanity-context-agent','authoritative_time':'2026-09-18T00:00:00Z','references':[{'id':'source','version':'v1'}],'proposed_answer':'bounded claim','intended_consequence':'answer','invariants':{k:True for k in ['time','continuity','alignment','genesis','boundary','reference','causality','consciousness']}}
cases={'valid':'PERMIT','stale':'HOLD','missing_reference':'HOLD','boundary_violation':'REJECT','replay':'REJECT'}
for name,expected in cases.items():
 x=json.loads(json.dumps(base)) if False else {**base,'invariants':dict(base['invariants'])}
 if name=='stale': x['invariants']['time']=False
 if name=='missing_reference': x['invariants']['reference']=False
 if name=='boundary_violation': x['invariants']['boundary']=False
 if name=='replay': x['invariants']['continuity']=False
 got=evaluate(x)['decision']; assert got==expected,(name,got,expected)
print('PASS',cases)
