"""Cifrado envolvente local: AES-256-GCM + RSA-OAEP SHA-256."""
from __future__ import annotations
import base64, json, os
from pathlib import Path
from typing import Any
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

FORMAT = "libeqg-envelope-v1"

def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")

def generate_user_keypair(private_path: str | Path, public_path: str | Path, *, password: bytes | None = None) -> None:
    """Generate a local 3072-bit RSA keypair; private key is encrypted on disk when password supplied."""
    private = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    enc = serialization.BestAvailableEncryption(password) if password else serialization.NoEncryption()
    Path(private_path).parent.mkdir(parents=True, exist_ok=True)
    Path(public_path).parent.mkdir(parents=True, exist_ok=True)
    Path(private_path).write_bytes(private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, enc))
    Path(public_path).write_bytes(private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    try: os.chmod(private_path, 0o600)
    except OSError: pass

def encrypt_artifact(plaintext: bytes, public_key_pem: bytes, *, run_id: str, artifact_name: str) -> dict[str, Any]:
    pub = serialization.load_pem_public_key(public_key_pem)
    if not isinstance(pub, rsa.RSAPublicKey) or pub.key_size < 3072:
        raise ValueError("La clave pública debe ser RSA de al menos 3072 bits")
    dek = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    aad = canonical_json({"format": FORMAT, "run_id": run_id, "artifact": artifact_name})
    ciphertext = AESGCM(dek).encrypt(nonce, plaintext, aad)
    wrapped = pub.encrypt(dek, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=aad))
    return {"format": FORMAT, "algorithm": "AES-256-GCM", "key_wrap": "RSA-OAEP-SHA256", "run_id": run_id, "artifact": artifact_name, "aad_b64": base64.b64encode(aad).decode(), "nonce_b64": base64.b64encode(nonce).decode(), "wrapped_dek_b64": base64.b64encode(wrapped).decode(), "ciphertext_b64": base64.b64encode(ciphertext).decode()}

def decrypt_artifact(envelope: dict[str, Any], private_key_pem: bytes, *, password: bytes | None = None) -> bytes:
    if envelope.get("format") != FORMAT or envelope.get("algorithm") != "AES-256-GCM" or envelope.get("key_wrap") != "RSA-OAEP-SHA256":
        raise ValueError("Formato o algoritmo de sobre no admitido")
    private = serialization.load_pem_private_key(private_key_pem, password=password)
    aad = base64.b64decode(envelope["aad_b64"], validate=True)
    expected = canonical_json({"format": FORMAT, "run_id": envelope["run_id"], "artifact": envelope["artifact"]})
    if aad != expected: raise ValueError("AAD no coincide con la identidad de corrida/artefacto")
    dek = private.decrypt(base64.b64decode(envelope["wrapped_dek_b64"], validate=True), padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=aad))
    return AESGCM(dek).decrypt(base64.b64decode(envelope["nonce_b64"], validate=True), base64.b64decode(envelope["ciphertext_b64"], validate=True), aad)
