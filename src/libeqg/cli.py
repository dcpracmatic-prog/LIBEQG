import argparse
from .crypto import generate_user_keypair

def main():
    p=argparse.ArgumentParser(prog="libeqg",description="LIBEQG: claves locales y verificación de pruebas QPU")
    sub=p.add_subparsers(dest="cmd",required=True)
    k=sub.add_parser("keygen",help="Generar clave local RSA para cifrado envolvente")
    k.add_argument("--private",default="libeqg_private.pem"); k.add_argument("--public",default="libeqg_public.pem")
    a=p.parse_args()
    if a.cmd=="keygen":
        generate_user_keypair(a.private,a.public)
        print(f"Claves creadas: {a.private} (privada; no compartir), {a.public} (pública)")
if __name__=="__main__": main()
