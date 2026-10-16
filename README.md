# LIBEQG

Librería gratuita para ejecutar una prueba QPU fija y no ajustable, cifrar evidencia localmente y actualizar un índice comparativo con una sola versión vigente por proveedor/servicio.

## Estado de esta entrega

Esta implementación incorpora cifrado envolvente local AES-256-GCM + RSA-OAEP-SHA256, manifiestos canónicos firmados Ed25519, cadena de eventos firmada y sustitución atómica del índice. **La firma Python es un adaptador de prototipo basado en primitivas compatibles; todavía no equivale a una integración invocada y verificada contra la crate Rust CSG.** La fase CSG no debe declararse cerrada hasta añadir el puente a la crate/notario de CSG y probar la verificación independiente con sus sellos reales.

La prueba fija está definida en `src/libeqg/benchmark.py`. Los proveedores aportan configuración de conexión y precios declarados; no pueden modificar la carga de trabajo. Las métricas que la API del proveedor no exponga deben quedar como no disponibles, no inventarse.

## Instalar y probar

```bash
python -m pip install -e '.[test]'
pytest
```

## Crear claves del cliente

```bash
libeqg keygen --private ~/.libeqg/private.pem --public ~/.libeqg/public.pem
chmod 600 ~/.libeqg/private.pem
```

La clave privada no debe subirse al repositorio ni enviarse al proveedor. En producción, protegerla con frase de paso o almacén seguro del sistema operativo. Perderla sin una copia de recuperación implica perder acceso a los resultados envueltos con su clave pública.

## Política del índice

- Una entrada por combinación `provider_id::service_id`.
- Sólo se actualiza con manifiesto firmado válido, cadena de eventos válida, autorización explícita de publicación y corrida válida.
- Escritura en archivo temporal + `os.replace` para sustitución atómica.
- El índice no guarda reportes cifrados, claves ni historiales de corridas.
- Los informes y la evidencia completa se quedan localmente con el usuario.

## Limitaciones

Este repositorio no afirma todavía compatibilidad de ejecución con todas las QPU ni una medición universal de fidelidad/costo: eso requiere adaptadores concretos por proveedor y definición común de métricas. El índice local es un prototipo; el índice comunitario requiere un punto de publicación compartido, control de concurrencia y validación del lado servidor sin almacenar historiales. El temporizador de 15 segundos debe implementarse en el publicador/servicio de índice para coalescer actualizaciones por proveedor/servicio; no es una propiedad criptográfica.
