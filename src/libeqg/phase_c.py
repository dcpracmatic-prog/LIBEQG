"""Contrato de la Fase C y configuración reproducible de simuladores."""
from __future__ import annotations

import hashlib
from types import MappingProxyType

BASE_SEED = 20261016

REFERENCE_SIMULATORS = MappingProxyType({
    "qiskit_aer": MappingProxyType({
        "kind": "local_cpu",
        "package": "qiskit-aer",
        "seed_supported": True,
        "purpose": "referencia ideal y modelos estándar de ruido",
    }),
    "cudaq_sim": MappingProxyType({
        "kind": "local_cpu",
        "package": "cuda-quantum",
        "seed_supported": True,
        "purpose": "referencia local mediante qpp-cpu",
    }),
    "dwave_leap_beta": MappingProxyType({
        "kind": "remote_service",
        "package": "dwave-gate",
        "seed_supported": False,
        "purpose": "servicio beta remoto; excluido de la validación local",
    }),
})

REFERENCE_PROBES = MappingProxyType({
    "bell": MappingProxyType({"qubits": 2, "shots": 2048}),
    "ghz3": MappingProxyType({"qubits": 3, "shots": 2048}),
})


def seed_for(simulator_id: str, circuit_id: str, base_seed: int = BASE_SEED) -> int:
    """Genera una semilla estable entre procesos, sin usar hash() de Python."""
    if simulator_id not in REFERENCE_SIMULATORS:
        raise ValueError(f"Unknown reference simulator: {simulator_id}")
    if circuit_id not in REFERENCE_PROBES:
        raise ValueError(f"Unknown reference probe: {circuit_id}")
    material = f"LIBEQG-FaseC-v1|{base_seed}|{simulator_id}|{circuit_id}".encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:4], "big")


def validate_ideal_counts(counts: dict[str, int], circuit_id: str) -> bool:
    """Valida estados permitidos para un circuito ideal, no conteos exactos."""
    if circuit_id not in REFERENCE_PROBES or not counts:
        return False
    if any(not isinstance(n, int) or n < 0 for n in counts.values()):
        return False
    allowed = {"bell": {"00", "11"}, "ghz3": {"000", "111"}}[circuit_id]
    return all(str(bits).replace(" ", "") in allowed for bits, n in counts.items() if n > 0)
