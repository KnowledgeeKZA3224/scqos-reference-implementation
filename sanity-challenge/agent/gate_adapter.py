"""Fail-closed adapter between Sanity-derived evidence and the existing Supreme Totality gate."""
import hashlib,json,os,urllib.request

def canonical_hash(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def decide(envelope):
    vals=envelope['invariants']
    if not all(isinstance(vals.get(k),bool) for k in ('time','continuity','alignment','genesis','boundary','reference','causality','consciousness')): return 'HOLD'
    if not vals['reference'] or not vals['time']: return 'HOLD'
    return 'PERMIT' if all(vals.values()) else 'REJECT'
def evaluate(envelope):
    return {'decision':decide(envelope),'transition_hash':canonical_hash(envelope),'rule':'no consequence executes until the current transition proves itself'}
