"""Ejecución automatizada de las pruebas de referencia de Fase C."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
import time
import traceback
from pathlib import Path
from typing import Any

from .phase_c import BASE_SEED, REFERENCE_PROBES, seed_for, validate_ideal_counts

TOLERANCE = 0.06


def _normalize_counts(counts: Any) -> dict[str, int]:
    return {str(key).replace(" ", ""): int(value) for key, value in dict(counts).items()}


def _check_distribution(counts: Any, circuit_id: str) -> dict[str, Any]:
    normalized = _normalize_counts(counts)
    if not validate_ideal_counts(normalized, circuit_id):
        raise AssertionError(f"{circuit_id}: estados observados no permitidos: {normalized}")
    total = sum(normalized.values())
    if total <= 0:
        raise AssertionError(f"{circuit_id}: el backend no devolvió mediciones")
    allowed = {"bell": ("00", "11"), "ghz3": ("000", "111")}[circuit_id]
    probabilities = {state: normalized.get(state, 0) / total for state in allowed}
    if any(abs(probability - 0.5) > TOLERANCE for probability in probabilities.values()):
        raise AssertionError(f"{circuit_id}: frecuencias fuera de tolerancia: {probabilities}")
    return {"shots": total, "probabilities": probabilities}


def _result(backend: str, status: str, detail: str, metrics: dict | None = None) -> dict:
    return {
        "backend": backend,
        "status": status,
        "detail": detail,
        "metrics": metrics or {},
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def validate_aer_cpu() -> dict:
    if importlib.util.find_spec("qiskit") is None or importlib.util.find_spec("qiskit_aer") is None:
        return _result("qiskit_aer_cpu", "BLOCKED", "Dependencias ausentes. Instala el extra [phase-c-aer].")
    try:
        from qiskit import QuantumCircuit, transpile
        from qiskit_aer import AerSimulator

        backend = AerSimulator(method="statevector", device="CPU")
        bell = QuantumCircuit(2, 2)
        bell.h(0)
        bell.cx(0, 1)
        bell.measure([0, 1], [0, 1])
        ghz = QuantumCircuit(3, 3)
        ghz.h(0)
        ghz.cx(0, 1)
        ghz.cx(1, 2)
        ghz.measure([0, 1, 2], [0, 1, 2])

        start = time.perf_counter()
        bell_compiled = transpile(bell, backend, seed_transpiler=seed_for("qiskit_aer", "bell"))
        ghz_compiled = transpile(ghz, backend, seed_transpiler=seed_for("qiskit_aer", "ghz3"))
        bell_seed = seed_for("qiskit_aer", "bell")
        bell_counts = backend.run(bell_compiled, shots=2048, seed_simulator=bell_seed).result().get_counts()
        ghz_counts = backend.run(ghz_compiled, shots=2048, seed_simulator=seed_for("qiskit_aer", "ghz3")).result().get_counts()
        bell_metrics = _check_distribution(bell_counts, "bell")
        ghz_metrics = _check_distribution(ghz_counts, "ghz3")
        repeated = backend.run(bell_compiled, shots=2048, seed_simulator=bell_seed).result().get_counts()
        repeatable = _normalize_counts(repeated) == _normalize_counts(bell_counts)
        if not repeatable:
            raise AssertionError("Bell no fue reproducible con la misma semilla")
        return _result("qiskit_aer_cpu", "PASS", "Bell/GHZ validados; repetición con semilla idéntica", {
            "device_requested": "CPU",
            "elapsed_seconds": round(time.perf_counter() - start, 4),
            "bell": bell_metrics,
            "ghz3": ghz_metrics,
            "same_seed_repeatable": repeatable,
        })
    except Exception as exc:
        return _result("qiskit_aer_cpu", "FAIL", f"{type(exc).__name__}: {exc}", {
            "traceback": traceback.format_exc(limit=8)
        })


def validate_cudaq_cpu() -> dict:
    if importlib.util.find_spec("cudaq") is None:
        return _result("cudaq_qpp_cpu", "BLOCKED", "Dependencia ausente. Instala [phase-c-cudaq] en un entorno compatible.")
    try:
        import cudaq
        cudaq.set_target("qpp-cpu")

        @cudaq.kernel
        def bell():
            q = cudaq.qvector(2)
            h(q[0])
            x.ctrl(q[0], q[1])
            mz(q)

        @cudaq.kernel
        def ghz3():
            q = cudaq.qvector(3)
            h(q[0])
            x.ctrl(q[0], q[1])
            x.ctrl(q[1], q[2])
            mz(q)

        def sample_counts(kernel, seed: int) -> dict[str, int]:
            cudaq.set_random_seed(seed)
            sample = cudaq.sample(kernel, shots_count=2048)
            try:
                counts = dict(sample.items())
            except (AttributeError, TypeError):
                counts = {str(bits): int(sample.count(bits)) for bits in sample}
            return _normalize_counts(counts)

        start = time.perf_counter()
        bell_seed = seed_for("cudaq_sim", "bell")
        bell_counts = sample_counts(bell, bell_seed)
        ghz_counts = sample_counts(ghz3, seed_for("cudaq_sim", "ghz3"))
        bell_metrics = _check_distribution(bell_counts, "bell")
        ghz_metrics = _check_distribution(ghz_counts, "ghz3")
        repeated = sample_counts(bell, bell_seed)
        repeatable = repeated == bell_counts
        if not repeatable:
            raise AssertionError("Bell no fue reproducible con la misma semilla")
        return _result("cudaq_qpp_cpu", "PASS", "Bell/GHZ validados; repetición con semilla idéntica", {
            "target_requested": "qpp-cpu",
            "elapsed_seconds": round(time.perf_counter() - start, 4),
            "bell": bell_metrics,
            "ghz3": ghz_metrics,
            "same_seed_repeatable": repeatable,
        })
    except Exception as exc:
        return _result("cudaq_qpp_cpu", "FAIL", f"{type(exc).__name__}: {exc}", {
            "traceback": traceback.format_exc(limit=8)
        })


def run_cpu_validation(report_path: str | Path | None = None) -> dict:
    """Ejecuta Aer y CUDA-Q localmente; no importa ni conecta D-Wave."""
    results = [validate_aer_cpu(), validate_cudaq_cpu()]
    passed = all(item["status"] == "PASS" for item in results)
    report = {
        "schema": "libeqg-cpu-validation-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "base_seed": BASE_SEED,
        "shots_per_probe": REFERENCE_PROBES["bell"]["shots"],
        "required_backends": ["qiskit_aer_cpu", "cudaq_qpp_cpu"],
        "dwave": "DISABLED_BY_DEFAULT",
        "overall": "PASS" if passed else "NOT_PASS",
        "results": results,
    }
    if report_path is not None:
        path = Path(report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.replace(path)
        report["report_path"] = str(path)
    return report
