# LIBEQG

[![LIBEQG tests](https://github.com/dcpracmatic-prog/LIBEQG/actions/workflows/tests.yml/badge.svg)](https://github.com/dcpracmatic-prog/LIBEQG/actions/workflows/tests.yml)

Librería gratuita para ejecutar una prueba QPU fija, comprobar referencias locales, cifrar evidencia y mantener un índice comparativo con una sola versión vigente por proveedor/servicio.

## Inicio rápido: clonar y ejecutar una sola orden

Requisito previo: Python 3.10 o posterior y conexión a Internet para descargar dependencias.

```bash
git clone https://github.com/dcpracmatic-prog/LIBEQG.git
cd LIBEQG
python scripts/validate.py
```

El script prepara automáticamente un entorno virtual local `.venv`, instala el paquete y las dependencias de prueba, ejecuta `pytest`, y lanza la prevalidación de Fase C. No requiere instalar manualmente la librería ni editar variables de configuración.

- Qiskit Aer se ejecuta explícitamente en CPU.
- CUDA-Q solicita el backend `qpp-cpu`.
- Los circuitos Bell y GHZ-3 se comprueban con semillas deterministas, estados permitidos y tolerancias estadísticas.
- Se genera `reports/phase-c-cpu-validation.json`.
- El comando termina con código distinto de cero si las pruebas fallan o si un simulador obligatorio queda bloqueado.
- D-Wave no se instala ni se conecta durante este flujo.

**Nota sobre CUDA-Q:** su distribución depende de la plataforma y de la versión de Python. Si no se puede instalar en el sistema actual, el script continúa con las pruebas disponibles, informa CUDA-Q como `BLOCKED` y no declara la validación completa como aprobada. No se debe confundir `BLOCKED` con `PASS`.

## Comandos después de instalar

Para instalar el paquete y las pruebas base sin simuladores opcionales:

```bash
python -m pip install -e ".[test]"
python -m pytest -v
```

Para ejecutar únicamente la prevalidación local, una vez instalados los extras CPU:

```bash
python -m pip install -e ".[test,cpu]"
python -m libeqg validate --cpu --report reports/phase-c-cpu-validation.json
```

El comando de validación devuelve:
- `0`: Aer y CUDA-Q ejecutaron y superaron las comprobaciones.
- `2`: prevalidación no aprobada; revisa `BLOCKED` o `FAIL` en la salida y en el JSON.

## Arquitectura de atestación

CSG se trata como un **módulo de atestación intercambiable y configurable**. Ed25519 es la implementación de firma predeterminada del prototipo, no una restricción arquitectónica. La cobertura del sello y la cadena de eventos se especifican mediante manifiesto, eventos firmados y validación independiente. La interoperabilidad con la crate Rust de CSG requiere pruebas cruzadas antes de afirmar compatibilidad binaria o de sellos.

## Fase C: simuladores de referencia

La prevalidación usa dos backends locales obligatorios:
- **Qiskit Aer CPU:** circuitos Bell y GHZ-3, con semilla fija y repetición del circuito Bell.
- **CUDA-Q `qpp-cpu`:** los mismos invariantes, semilla fija y comprobación de repetibilidad.

No se exige que dos backends distintos produzcan conteos idénticos. Se validan invariantes físicos y tolerancias estadísticas. Estos probes no alteran ni sustituyen la carga de trabajo QPU fija de LIBEQG.

**D-Wave Leap gate-model beta** es un servicio remoto, no un simulador local/offline. Se mantiene desactivado por defecto; no se instala, no se contacta y no consume cuota en el inicio rápido. Cualquier prueba remota debe activarse de forma explícita, con acceso beta autorizado y revisión separada.

## Crear claves del cliente

```bash
libeqg keygen --private ~/.libeqg/private.pem --public ~/.libeqg/public.pem
```

Protege la clave privada y no la subas al repositorio. Perderla sin copia de recuperación puede impedir descifrar los resultados cifrados para esa clave.

## Política del índice

- Una entrada por combinación `provider_id::service_id`.
- Sólo se actualiza con manifiesto firmado válido, cadena de eventos válida, autorización explícita de publicación y corrida válida.
- Escritura en archivo temporal y sustitución atómica.
- El índice no guarda reportes cifrados, claves ni historiales de corridas.
- Los informes y la evidencia completa permanecen localmente con el usuario.

## Alcance y limitaciones

Esta librería no afirma compatibilidad de ejecución con todas las QPU ni una medición universal de fidelidad/costo. Eso requiere adaptadores concretos por proveedor y una definición común de métricas. El índice actual es local; un índice comunitario requerirá punto de publicación compartido, control de concurrencia y validación del lado servidor sin conservar historiales públicos.

La suite de simuladores valida la prevalidación local; **no certifica por sí sola una QPU física, la integración Rust de CSG ni todos los adaptadores de proveedor**.
