# ProofGate AI — plug-and-play boundary

ProofGate is now usable without learning the rest of SCQOS first. A developer can call the live public boundary from Python, the command line, or a GitHub Actions workflow. The boundary remains fail-closed: PERMIT means the submitted transition satisfied the frozen contract; HOLD means proof is incomplete or stale; REJECT means the proposition crosses an explicit rule or authority boundary.

## Fastest possible test

```bash
pip install "git+https://github.com/KnowledgeeKZA3224/scqos-reference-implementation.git"
proofgate matrix
proofgate challenge --case valid
```

The CLI exits `0` only when the requested operation reaches its success condition. A challenge that returns HOLD or REJECT exits `2`, so it can be used directly in scripts and CI.

## Use it in another Python project

```python
from proofgate_ai import ProofGateClient

receipt = ProofGateClient().challenge_case("valid")
if receipt["decision"] != "PERMIT":
    raise SystemExit("execution blocked")
print(receipt["receipt_id"])
```

For a real application, submit your own transition object with `challenge_transition(...)`. The public challenge service is intentionally shadow-only: it decides whether the proposition qualifies, signs and stores the receipt, but does not perform the external side effect itself.

## Drop it into GitHub Actions

```yaml
steps:
  - uses: KnowledgeeKZA3224/scqos-reference-implementation/.github/actions/proofgate@main
    with:
      case_id: valid
```

For an application-specific gate, pass a JSON transition with the `transition` input. The action fails the job automatically unless the decision is PERMIT. It also emits `decision`, `decision_boundary`, and `receipt_id` as outputs.

## Public falsification challenge

The public endpoint exposes a frozen adversarial matrix and a custom-transition route. Anyone can submit a proposition and inspect the resulting signed receipt. A successful technical challenge is not a social-media claim; it is a reproducible request, response, receipt, source commit, and contract hash that another person can independently verify.

Public endpoint: `https://lcnk9bvtz5.execute-api.us-east-1.amazonaws.com/`

Routes:
- `GET /v1/health`
- `POST /v1/run-matrix`
- `POST /v1/challenge`
- `GET /v1/receipt/{receipt_id}`
- `GET /v1/public-key`

That turns the project from “read our repository” into “send the boundary a concrete transition and try to make it produce the wrong result.”
