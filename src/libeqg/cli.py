"""CLI de LIBEQG: operaciones locales y prevalidación automatizada."""
import argparse
import json
import sys

from .crypto import generate_user_keypair


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="libeqg",
        description="LIBEQG: prueba de referencia, evidencia verificable y claves locales",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    keygen = sub.add_parser("keygen", help="Generar clave local RSA para cifrado envolvente")
    keygen.add_argument("--private", default="libeqg_private.pem")
    keygen.add_argument("--public", default="libeqg_public.pem")

    validate = sub.add_parser(
        "validate",
        help="Ejecutar automáticamente la prevalidación de simuladores locales",
    )
    validate.add_argument("--cpu", action="store_true", help="Ejecutar Aer CPU y CUDA-Q qpp-cpu")
    validate.add_argument(
        "--report",
        default="libeqg_cpu_validation.json",
        help="Ruta del informe JSON (por defecto: ./libeqg_cpu_validation.json)",
    )

    args = parser.parse_args(argv)
    if args.cmd == "keygen":
        generate_user_keypair(args.private, args.public)
        print(f"Claves creadas: {args.private} (privada; no compartir), {args.public} (pública)")
        return 0

    if args.cmd == "validate":
        if not args.cpu:
            parser.error("indica --cpu para ejecutar la prevalidación local")
        from .validation import run_cpu_validation

        report = run_cpu_validation(args.report)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        if report["overall"] != "PASS":
            print(
                "\nPrevalidación NO APROBADA: revisa estados BLOCKED/FAIL en el informe.",
                file=sys.stderr,
            )
            return 2
        print("\nPrevalidación aprobada: Aer y CUDA-Q pasaron las pruebas CPU.")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
