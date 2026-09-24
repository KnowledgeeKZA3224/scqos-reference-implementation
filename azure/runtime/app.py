from __future__ import annotations

import base64
import hmac
import json
import os
import time
from functools import lru_cache

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from azure.core.exceptions import ResourceExistsError
from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.keyvault.keys import KeyClient
from azure.keyvault.keys.crypto import CryptographyClient, SignatureAlgorithm
from azure.keyvault.secrets import SecretClient
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.storage.blob import BlobServiceClient

from integration import universal_gateway as base

ACCOUNT = os.environ["SCQOS_AZURE_STORAGE_ACCOUNT"]
VAULT_URL = os.environ["SCQOS_KEYVAULT_URL"]
SB_NAMESPACE = os.environ["SCQOS_SERVICEBUS_NAMESPACE"]
KEY_NAME = os.getenv("SCQOS_SIGNING_KEY", "scqos-signing-key")
SECRET_NAME = os.getenv("SCQOS_SECRET_NAME", "scqos-universal-secret")
API_KEY_NAME = os.getenv("SCQOS_API_KEY_NAME", "scqos-api-key")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")

if CLIENT_ID:
    CREDENTIAL = ManagedIdentityCredential(client_id=CLIENT_ID)
else:
    CREDENTIAL = DefaultAzureCredential(exclude_interactive_browser_credential=True)

TABLES = TableServiceClient(
    endpoint=f"https://{ACCOUNT}.table.core.windows.net",
    credential=CREDENTIAL,
)
RECEIPTS = TABLES.get_table_client("scqosreceipts")
CONTINUITY = TABLES.get_table_client("scqoscontinuity")
BLOBS = BlobServiceClient(
    account_url=f"https://{ACCOUNT}.blob.core.windows.net",
    credential=CREDENTIAL,
)
SECRETS = SecretClient(vault_url=VAULT_URL, credential=CREDENTIAL)
KEYS = KeyClient(vault_url=VAULT_URL, credential=CREDENTIAL)

ALLOWED_QUEUES = {
    "actions": "scqos-actions",
    "business": "scqos-business",
    "followup": "scqos-followup",
    "publish": "scqos-publish",
}


def _escape(value: str) -> str:
    return value.replace("'", "''")


@lru_cache(maxsize=1)
def governance_secret() -> str:
    return SECRETS.get_secret(SECRET_NAME).value


@lru_cache(maxsize=1)
def api_key() -> str:
    return SECRETS.get_secret(API_KEY_NAME).value


@lru_cache(maxsize=1)
def crypto_client() -> CryptographyClient:
    key = KEYS.get_key(KEY_NAME)
    return CryptographyClient(key, credential=CREDENTIAL)


def require_key(provided: str | None) -> None:
    if not provided or not hmac.compare_digest(provided, api_key()):
        raise HTTPException(status_code=401, detail="invalid governance key")


def previous_receipt_hash(tenant_id: str):
    rows = RECEIPTS.query_entities(
        query_filter=f"PartitionKey eq '{_escape(tenant_id)}'",
        select=["receipt_hash", "created_at"],
    )
    newest = None
    for row in rows:
        if newest is None or float(row["created_at"]) > float(newest["created_at"]):
            newest = row
    return newest["receipt_hash"] if newest else None


base._secret = governance_secret
base.previous_receipt_hash = previous_receipt_hash
base.persist = lambda result: None


def persist_azure(result: base.TransitionResponse) -> dict:
    receipt_hash = result.receipt_hash
    digest = bytes.fromhex(receipt_hash)
    signed = crypto_client().sign(SignatureAlgorithm.rs256, digest)
    signature = base64.b64encode(signed.signature).decode("ascii")
    key_id = crypto_client().key_id

    entity = {
        "PartitionKey": result.receipt["tenant_id"],
        "RowKey": result.transition_id,
        "created_at": float(result.receipt["created_at"]),
        "decision": result.decision,
        "execution_authorized": bool(result.execution_authorized),
        "prior_receipt_hash": result.prior_receipt_hash or "",
        "receipt_hash": receipt_hash,
        "receipt_json": json.dumps(
            result.receipt,
            sort_keys=True,
            separators=(",", ":"),
        ),
        "azure_signature": signature,
        "azure_key_id": key_id,
    }
    try:
        RECEIPTS.create_entity(entity)
    except ResourceExistsError:
        current = RECEIPTS.get_entity(
            entity["PartitionKey"],
            entity["RowKey"],
        )
        if current["receipt_hash"] != receipt_hash:
            raise RuntimeError("receipt identity collision")
        entity = current

    envelope = {
        "receipt": result.receipt,
        "receipt_hash": receipt_hash,
        "azure_witness": {
            "key_id": key_id,
            "signature_rs256_b64": signature,
        },
    }
    blob = BLOBS.get_blob_client(
        container="receipts",
        blob=f"{result.receipt['tenant_id']}/{result.transition_id}.json",
    )
    try:
        blob.upload_blob(
            json.dumps(
                envelope,
                sort_keys=True,
                separators=(",", ":"),
            ),
            overwrite=False,
        )
    except ResourceExistsError:
        pass
    return envelope


def find_receipt(transition_id: str):
    rows = RECEIPTS.query_entities(
        query_filter=f"RowKey eq '{_escape(transition_id)}'"
    )
    for row in rows:
        return row
    return None


class ExecuteRequest(BaseModel):
    confirm: bool = False
    lane: str = Field(default="actions")


app = FastAPI(
    title="SCQOS Azure Governance Plane",
    version="1.0.0",
    description="Supreme Computation universal transition boundary on Azure.",
)


@app.get("/v1/health")
def health():
    return {
        "status": "ONLINE",
        "cloud": "Azure",
        "contract_id": base.CONTRACT_ID,
        "rule": "Nothing executes until it proves itself.",
    }


@app.post("/v1/transition")
def transition(
    request: base.TransitionRequest,
    x_scqos_key: str | None = Header(default=None),
):
    require_key(x_scqos_key)
    result = base.govern_transition(request)
    try:
        envelope = persist_azure(result)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "fail-closed: durable witness unavailable: "
                f"{type(exc).__name__}"
            ),
        ) from exc

    payload = result.model_dump(mode="python")
    payload["azure_witness"] = envelope["azure_witness"]
    return payload


@app.get("/v1/receipt/{transition_id}")
def receipt(
    transition_id: str,
    x_scqos_key: str | None = Header(default=None),
):
    require_key(x_scqos_key)
    row = find_receipt(transition_id)
    if not row:
        raise HTTPException(status_code=404, detail="receipt not found")
    return {
        "receipt_hash": row["receipt_hash"],
        "receipt": json.loads(row["receipt_json"]),
        "azure_witness": {
            "key_id": row["azure_key_id"],
            "signature_rs256_b64": row["azure_signature"],
        },
    }


@app.post("/v1/execute/{transition_id}")
def execute(
    transition_id: str,
    request: ExecuteRequest,
    x_scqos_key: str | None = Header(default=None),
):
    require_key(x_scqos_key)
    if not request.confirm:
        raise HTTPException(
            status_code=400,
            detail="explicit confirmation required",
        )
    if request.lane not in ALLOWED_QUEUES:
        raise HTTPException(status_code=400, detail="unknown execution lane")

    row = find_receipt(transition_id)
    if not row:
        raise HTTPException(status_code=404, detail="receipt not found")

    receipt_data = json.loads(row["receipt_json"])
    if row["decision"] != "PERMIT" or not row["execution_authorized"]:
        raise HTTPException(
            status_code=409,
            detail="transition is not executable",
        )

    lock = {
        "PartitionKey": receipt_data["tenant_id"],
        "RowKey": transition_id,
        "status": "STAGED",
        "lane": request.lane,
        "created_at": time.time(),
    }
    try:
        CONTINUITY.create_entity(lock)
    except ResourceExistsError:
        current = CONTINUITY.get_entity(
            lock["PartitionKey"],
            lock["RowKey"],
        )
        if current.get("status") in {"QUEUED", "EXECUTED"}:
            return {
                "status": current["status"],
                "transition_id": transition_id,
            }
        CONTINUITY.delete_entity(
            lock["PartitionKey"],
            lock["RowKey"],
        )
        CONTINUITY.create_entity(lock)

    queue_name = ALLOWED_QUEUES[request.lane]
    message = {
        "transition_id": transition_id,
        "tenant_id": receipt_data["tenant_id"],
        "lane": request.lane,
        "receipt_hash": row["receipt_hash"],
        "receipt": receipt_data,
    }

    try:
        with ServiceBusClient(
            fully_qualified_namespace=(
                f"{SB_NAMESPACE}.servicebus.windows.net"
            ),
            credential=CREDENTIAL,
        ) as client:
            with client.get_queue_sender(queue_name=queue_name) as sender:
                sender.send_messages(
                    ServiceBusMessage(json.dumps(message))
                )

        lock["status"] = "QUEUED"
        lock["queued_at"] = time.time()
        CONTINUITY.update_entity(lock, mode="replace")
    except Exception as exc:
        lock["status"] = "FAILED"
        lock["failure_type"] = type(exc).__name__
        CONTINUITY.update_entity(lock, mode="replace")
        raise HTTPException(
            status_code=503,
            detail="execution queue unavailable",
        ) from exc

    return {
        "status": "QUEUED",
        "transition_id": transition_id,
        "lane": request.lane,
    }
