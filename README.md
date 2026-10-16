# LIBEQG

Librería gratuita para ejecutar una prueba QPU fija y no ajustable, cifrar evidencia localmente y actualizar un índice comparativo con una sola versión vigente por proveedor/servicio.

## Arquitectura de atestación

CSG se trata como un **módulo de atestación intercambiable y configurable**. Ed25519 es la implementación de firma por defecto de este prototipo, no una restricción arquitectónica: el contrato del módulo permite adaptar el mecanismo a cada usuario, organización o política de auditoría. La cobertura del sello y la cadena de eventos se definen mediante manifiesto, eventos firmados y validación independiente; se pueden ampliar según el perfil de auditoría requerido. La integración directa con la crate Rust de CSG debe probarse por separado antes de afirmar compatibilidad binaria o interoperabilidad con sellos generados por esa crate.

## Ejecutar el notebook de prevalidación CPU

Abre [`LIBEQG_FaseC_Prevalidacion_CPU.ipynb`](./LIBEQG_FaseC_Prevalidacion_CPU.ipynb) desde la raíz del repositorio y ejecuta las celdas en orden. El notebook instala las dependencias opcionales de prueba, Qiskit Aer y CUDA-Q, selecciona explícitamente el target CUDA-Q `qpp-cpu`, valida Bell y GHZ-3 con semillas fijas y escribe un reporte local `phase_c_cpu_report.json`. La prueba de D-Wave Leap no se invoca.

En un entorno que ya tenga las dependencias, puedes desactivar la instalación en la celda correspondiente. Si CUDA-Q no puede instalarse o no dispone de `qpp-cpu`, la validación debe considerarse incompleta; no continúes a una QPU real.

## Fase C: prevalidación con simuladores de referencia

Antes de consumir créditos de una QPU física, LIBEQG incorpora un contrato de prevalidación con tres referencias:

- **Qiskit Aer**: simulación local CPU de vectores de estado y modelos de ruido estándar. Las pruebas pasan una semilla fija a la opción seed_simulator.
- **NVIDIA CUDA-Q**: simulación local cuando el backend de CPU está instalado y disponible. Las pruebas fijan la semilla mediante cudaq.set_random_seed.
- **D-Wave Leap gate-model beta (DRsim_21qubits)**: integración remota mediante Ocean/dwave-gate, con prueba opt-in y credenciales autorizadas. No es una simulación local/offline; el acceso depende de la beta de Leap y podría consumir cuota de servicio. La API documentada no ofrece una semilla de simulación en el ejemplo público, por lo que la prueba valida resultados e invariantes, no conteos bit a bit reproducibles.

La Fase C valida invariantes de referencia (por ejemplo, que el circuito Bell ideal sólo produzca 00 o 11) y repetibilidad donde el backend expone una semilla. No presupone que los tres simuladores compartan el mismo modelo de ruido ni que sus conteos sean idénticos. El ground truth debe etiquetarse por circuito, modo ideal/ruidoso, backend y versión. Los probes de referencia no modifican el testbench QPU inmutable de producción.

Instalación opcional para Aer:
```bash
python -m pip install -e '.[test,phase-c-aer]'
pytest -v
```

Instalación opcional para CUDA-Q:
```bash
python -m pip install -e '.[test,phase-c-cudaq]'
pytest -v
```

La prueba de D-Wave se excluye por defecto. Para habilitarla, instalar el SDK y configurar acceso beta autorizado:
```bash
python -m pip install -e '.[test,phase-c-dwave]'
LIBEQG_ENABLE_DWAVE_BETA=1 pytest -v tests/test_phase_c_simulators.py::test_phase_c_06_dwave_leap_beta_bell_smoke
```

## Estado de esta entrega

La implementación incluye cifrado envolvente local AES-256-GCM + RSA-OAEP-SHA256, manifiestos canónicos firmados Ed25519, cadena de eventos firmada y sustitución atómica del índice. La firma Python es el módulo de referencia actual; la interoperabilidad con sellos de la crate Rust CSG no se debe afirmar hasta ejecutar pruebas cruzadas con esa implementación.

La prueba fija está definida en src/libeqg/benchmark.py. Los proveedores aportan configuración de conexión y precios declarados; no pueden modificar la carga de trabajo. Las métricas que la API del proveedor no exponga deben quedar como no disponibles, no inventarse.

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

- Una entrada por combinación provider_id::service_id.
- Sólo se actualiza con manifiesto firmado válido, cadena de eventos válida, autorización explícita de publicación y corrida válida.
- Escritura en archivo temporal + os.replace para sustitución atómica.
- El índice no guarda reportes cifrados, claves ni historiales de corridas.
- Los informes y la evidencia completa se quedan localmente con el usuario.

## Limitaciones conocidas

Este repositorio no afirma todavía compatibilidad de ejecución con todas las QPU ni una medición universal de fidelidad/costo: eso requiere adaptadores concretos por proveedor y definición común de métricas. El índice local es un prototipo; el índice comunitario requiere un punto de publicación compartido, control de concurrencia y validación del lado servidor sin almacenar historiales. El temporizador de 15 segundos debe implementarse en el publicador/servicio de índice para coalescer actualizaciones por proveedor/servicio; no es una propiedad criptográfica.
