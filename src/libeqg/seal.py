"""Manifiesto canónico y cadena de eventos con firmas Ed25519.

Primitivas compatibles con la familia criptográfica de CSG (Ed25519 + SHA3-256).
Este módulo Python no invoca por sí mismo el notario Rust de CSG.
"""
from __future__ import annotations
import base64, hashlib, time
from typing import Any
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from .crypto import canonical_json
GENESIS = "0" * 64

def sha3(data: bytes) -> str: return hashlib.sha3_256(data).hexdigest()
def new_signer() -> tuple[bytes, bytes]:
    key=Ed25519PrivateKey.generate()
    return (key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()), key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))
def sign_manifest(manifest: dict[str, Any], private_key_raw: bytes) -> dict[str, Any]:
    body={k:v for k,v in manifest.items() if k not in {"signature_b64","signer_public_b64"}}
    key=Ed25519PrivateKey.from_private_bytes(private_key_raw)
    sig=key.sign(canonical_json(body))
    return {**body,"signer_public_b64":base64.b64encode(key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode(),"signature_b64":base64.b64encode(sig).decode()}
def verify_manifest(signed: dict[str, Any]) -> bool:
    try:
        body={k:v for k,v in signed.items() if k not in {"signature_b64","signer_public_b64"}}
        Ed25519PublicKey.from_public_bytes(base64.b64decode(signed["signer_public_b64"],validate=True)).verify(base64.b64decode(signed["signature_b64"],validate=True),canonical_json(body))
        return True
    except Exception: return False
def append_event(chain: list[dict[str, Any]], payload: dict[str, Any], private_key_raw: bytes) -> dict[str, Any]:
    prev=chain[-1]["event_hash"] if chain else GENESIS
    body={"sequence":len(chain),"previous_hash":prev,"timestamp":int(time.time()),"payload":payload}
    digest=sha3(canonical_json(body))
    key=Ed25519PrivateKey.from_private_bytes(private_key_raw)
    event={**body,"event_hash":digest,"signature_b64":base64.b64encode(key.sign(bytes.fromhex(digest))).decode()}
    chain.append(event); return event
def verify_chain(chain: list[dict[str, Any]], public_key_raw: bytes) -> bool:
    try:
        pub=Ed25519PublicKey.from_public_bytes(public_key_raw); prev=GENESIS
        for i,e in enumerate(chain):
            body={k:e[k] for k in ("sequence","previous_hash","timestamp","payload")}
            digest=sha3(canonical_json(body))
            if e["sequence"]!=i or e["previous_hash"]!=prev or e["event_hash"]!=digest: return False
            pub.verify(base64.b64decode(e["signature_b64"],validate=True),bytes.fromhex(digest)); prev=digest
        return True
    except Exception: return False
