from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional

DEFAULT_ENDPOINT = "https://lcnk9bvtz5.execute-api.us-east-1.amazonaws.com/"
DEMO_ENDPOINT = "https://brbdxmelpeaktvdpmjrk34upwq0pymad.lambda-url.us-east-1.on.aws/"


class ProofGateError(RuntimeError):
    """Raised when a ProofGate endpoint cannot be reached or returns invalid data."""


@dataclass(frozen=True)
class ProofGateClient:
    endpoint: str = DEFAULT_ENDPOINT
    timeout: float = 20.0

    def _url(self, path: str) -> str:
        return self.endpoint.rstrip("/") + "/" + path.lstrip("/")

    def _request(self, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = {"accept": "application/json"}
        if data is not None:
            headers["content-type"] = "application/json"
        request = urllib.request.Request(self._url(path), data=data, headers=headers, method="POST" if data is not None else "GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ProofGateError(f"HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ProofGateError(f"endpoint unavailable: {exc.reason}") from exc
        try:
            result = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ProofGateError("endpoint returned non-JSON data") from exc
        if not isinstance(result, dict):
            raise ProofGateError("endpoint returned an unexpected response shape")
        return result

    def health(self) -> Dict[str, Any]:
        return self._request("v1/health")

    def matrix(self) -> Dict[str, Any]:
        return self._request("v1/run-matrix", {})

    def challenge_case(self, case_id: str) -> Dict[str, Any]:
        return self._request("v1/challenge", {"case_id": case_id})

    def challenge_transition(self, transition: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("v1/challenge", {"transition": transition})

    def receipt(self, receipt_id: str) -> Dict[str, Any]:
        return self._request(f"v1/receipt/{receipt_id}")
