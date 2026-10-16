import base64, json
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from libeqg.crypto import encrypt_artifact, decrypt_artifact
from libeqg.seal import new_signer, sign_manifest, verify_manifest, append_event, verify_chain
from libeqg.index import LatestIndex, IndexRejected
from libeqg.benchmark import package_evidence

def rsa_pair():
    priv=rsa.generate_private_key(public_exponent=65537,key_size=3072)
    return priv.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()), priv.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
def fixture():
    sk,pk=new_signer()
    manifest={"schema":"libeqg-manifest-v1","run_id":"run-1","provider_id":"vendor-a","service_id":"optimizer-x","publication_authorized":True}
    signed=sign_manifest(manifest,sk); chain=[]
    append_event(chain,{"type":"start"},sk); append_event(chain,{"type":"finish"},sk)
    return sk,pk,signed,chain,base64.b64decode(signed["signer_public_b64"])

# CSG / atestación: 3 pruebas
def test_csg_01_valid_seal():
    _,_,m,c,p=fixture(); assert verify_manifest(m); assert verify_chain(c,p)
def test_csg_02_manifest_modification_rejected():
    _,_,m,_,_=fixture(); m["provider_id"]="vendor-evil"; assert not verify_manifest(m)
def test_csg_03_event_chain_tampering_detected():
    _,_,_,c,p=fixture(); c[0]["payload"]["type"]="tampered"; assert not verify_chain(c,p)

# Claves/BYOK: 3 pruebas
def test_keys_01_user_isolation():
    priv_a,pub_a=rsa_pair(); priv_b,_=rsa_pair()
    env=encrypt_artifact(b"A-private",pub_a,run_id="r1",artifact_name="report")
    assert decrypt_artifact(env,priv_a)==b"A-private"
    with pytest.raises(Exception): decrypt_artifact(env,priv_b)
def test_keys_02_run_isolation():
    priv,pub=rsa_pair(); a=encrypt_artifact(b"run1",pub,run_id="r1",artifact_name="report"); b=encrypt_artifact(b"run2",pub,run_id="r2",artifact_name="report")
    assert decrypt_artifact(a,priv)==b"run1" and decrypt_artifact(b,priv)==b"run2"
    changed=dict(a); changed["run_id"]="r2"
    with pytest.raises(ValueError): decrypt_artifact(changed,priv)
def test_keys_03_key_loss_and_rotation():
    priv1,pub1=rsa_pair(); priv2,pub2=rsa_pair(); old=encrypt_artifact(b"recoverable",pub1,run_id="r1",artifact_name="report")
    assert decrypt_artifact(old,priv1)==b"recoverable"
    with pytest.raises(Exception): decrypt_artifact(old,priv2)
    new=encrypt_artifact(b"rotated",pub2,run_id="r2",artifact_name="report")
    assert decrypt_artifact(new,priv2)==b"rotated"

# Datos: 3 pruebas
def test_data_01_atomic_latest_replacement(tmp_path):
    sk,_,m,c,p=fixture(); idx=LatestIndex(tmp_path/"index.json")
    idx.update(provider_id="vendor-a",service_id="optimizer-x",public_metrics={"score":1},signed_manifest=m,event_chain=c,event_public_key=p,publication_authorized=True,valid_run=True)
    sk2,_,m2,c2,p2=fixture()
    m2=sign_manifest({"schema":"libeqg-manifest-v1","run_id":"run-2","provider_id":"vendor-a","service_id":"optimizer-x","publication_authorized":True},sk2)
    # Rebuild the event chain with the same signer as the new manifest.
    c2=[]; append_event(c2,{"type":"start"},sk2); append_event(c2,{"type":"finish"},sk2)
    p2=base64.b64decode(m2["signer_public_b64"])
    idx.update(provider_id="vendor-a",service_id="optimizer-x",public_metrics={"score":2},signed_manifest=m2,event_chain=c2,event_public_key=p2,publication_authorized=True,valid_run=True)
    data=idx.snapshot()["providers"]; assert len(data)==1 and next(iter(data.values()))["metrics"]["score"]==2
def test_data_02_unauthorized_publication_blocked(tmp_path):
    _,_,m,c,p=fixture(); idx=LatestIndex(tmp_path/"index.json")
    with pytest.raises(IndexRejected): idx.update(provider_id="vendor-a",service_id="optimizer-x",public_metrics={},signed_manifest=m,event_chain=c,event_public_key=p,publication_authorized=False,valid_run=True)
    assert idx.snapshot()["providers"]=={}
def test_data_03_invalid_run_preserves_last_good(tmp_path):
    _,_,m,c,p=fixture(); idx=LatestIndex(tmp_path/"index.json")
    idx.update(provider_id="vendor-a",service_id="optimizer-x",public_metrics={"score":7},signed_manifest=m,event_chain=c,event_public_key=p,publication_authorized=True,valid_run=True)
    before=idx.snapshot()
    with pytest.raises(IndexRejected): idx.update(provider_id="vendor-a",service_id="optimizer-x",public_metrics={"score":0},signed_manifest=m,event_chain=c,event_public_key=p,publication_authorized=True,valid_run=False)
    assert idx.snapshot()==before

# Flujo integral A/C/D/E: 1 prueba
def test_flow_01_acde_encrypted_verifiable_evidence():
    priv,pub=rsa_pair(); sk,_=new_signer()
    result=package_evidence(rid="flow-1",provider_id="vendor-a",service_id="optimizer-x",results={"success_rate":0.98,"execution_seconds":2.1,"cost_usd":0.03},user_public_key_pem=pub,signer_private_raw=sk)
    assert verify_manifest(result["manifest"])
    chain_pub=base64.b64decode(result["event_public_key_raw_b64"])
    assert verify_chain(result["event_chain"],chain_pub)
    import json
    clear=decrypt_artifact(result["encrypted_result"],priv)
    assert json.loads(clear)["success_rate"]==0.98
    assert result["manifest"]["run_id"]=="flow-1"
