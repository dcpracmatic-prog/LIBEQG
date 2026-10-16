"""Índice comparativo de última versión por proveedor/servicio; no conserva historial."""
from __future__ import annotations
import base64, hashlib, json, os, tempfile, time
from pathlib import Path
from typing import Any
from .crypto import canonical_json
from .seal import verify_manifest, verify_chain

class IndexRejected(ValueError): pass

class LatestIndex:
    def __init__(self, path: str | Path): self.path=Path(path)
    def _read(self) -> dict[str, Any]:
        if not self.path.exists(): return {"schema":"libeqg-index-v1","providers":{}}
        data=json.loads(self.path.read_text("utf-8"))
        if data.get("schema")!="libeqg-index-v1" or not isinstance(data.get("providers"),dict): raise IndexRejected("Índice corrupto")
        return data
    def update(self, *, provider_id: str, service_id: str, public_metrics: dict[str, Any], signed_manifest: dict[str, Any], event_chain: list[dict[str, Any]], event_public_key: bytes, publication_authorized: bool, valid_run: bool) -> None:
        if not publication_authorized: raise IndexRejected("Publicación no autorizada")
        if not valid_run: raise IndexRejected("Corrida inválida")
        if not provider_id.strip() or not service_id.strip(): raise IndexRejected("Proveedor/servicio obligatorio")
        if not verify_manifest(signed_manifest): raise IndexRejected("Sello/manifiesto inválido")
        if not verify_chain(event_chain,event_public_key): raise IndexRejected("Cadena de eventos inválida")
        if signed_manifest.get("signer_public_b64") != base64.b64encode(event_public_key).decode("ascii"):
            raise IndexRejected("La clave del firmante no coincide entre manifiesto y cadena")
        if signed_manifest.get("provider_id")!=provider_id or signed_manifest.get("service_id")!=service_id: raise IndexRejected("Identidad no coincide con manifiesto")
        entry={"provider_id":provider_id,"service_id":service_id,"updated_at":int(time.time()),"metrics":public_metrics,"run_id":signed_manifest["run_id"],"manifest_hash":hashlib.sha3_256(canonical_json(signed_manifest)).hexdigest()}
        data=self._read(); key=f"{provider_id}::{service_id}"; data["providers"][key]=entry
        self.path.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(prefix=".libeqg-index-",dir=str(self.path.parent))
        try:
            with os.fdopen(fd,"wb") as f: f.write(canonical_json(data)); f.flush(); os.fsync(f.fileno())
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
    def snapshot(self) -> dict[str, Any]: return self._read()
