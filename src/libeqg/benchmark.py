"""Esquema de prueba fija; el adaptador de proveedor no puede modificar el test."""
from __future__ import annotations
import base64, hashlib, time, uuid
from typing import Any
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from .crypto import canonical_json, encrypt_artifact
from .seal import append_event, sign_manifest

TESTBENCH_VERSION="libeqg-qpu-fixed-v1"
IMMUTABLE_WORKLOAD={"schema":"libeqg-workload-v1","circuits":[{"id":"bell-state","qubits":2,"shots":1024},{"id":"ghz-3","qubits":3,"shots":1024},{"id":"qft-3","qubits":3,"shots":512}],"metrics":["success_rate","fidelity_if_available","queue_seconds","execution_seconds","cost_usd","cost_per_success"],"mutable":False}
def run_id() -> str: return str(uuid.uuid4())
def build_manifest(*, rid: str, provider_id: str, service_id: str, workload_hash: str, results_hash: str) -> dict[str, Any]:
    return {"schema":"libeqg-manifest-v1","run_id":rid,"provider_id":provider_id,"service_id":service_id,"testbench_version":TESTBENCH_VERSION,"workload_hash":workload_hash,"results_hash":results_hash,"created_at":int(time.time()),"publication_authorized":False}
def package_evidence(*, rid: str, provider_id: str, service_id: str, results: dict[str, Any], user_public_key_pem: bytes, signer_private_raw: bytes) -> dict[str, Any]:
    workload_hash=hashlib.sha3_256(canonical_json(IMMUTABLE_WORKLOAD)).hexdigest(); result_bytes=canonical_json(results); result_hash=hashlib.sha3_256(result_bytes).hexdigest()
    chain=[]
    append_event(chain,{"type":"run_started","run_id":rid,"provider_id":provider_id,"service_id":service_id,"workload_hash":workload_hash},signer_private_raw)
    append_event(chain,{"type":"run_completed","run_id":rid,"results_hash":result_hash},signer_private_raw)
    manifest=build_manifest(rid=rid,provider_id=provider_id,service_id=service_id,workload_hash=workload_hash,results_hash=result_hash)
    signed=sign_manifest(manifest,signer_private_raw)
    event_pub=Ed25519PrivateKey.from_private_bytes(signer_private_raw).public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    return {"manifest":signed,"event_chain":chain,"event_public_key_raw_b64":base64.b64encode(event_pub).decode(),"encrypted_result":encrypt_artifact(result_bytes,user_public_key_pem,run_id=rid,artifact_name="results.json")}
