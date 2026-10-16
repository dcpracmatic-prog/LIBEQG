"""Fase C: contrato de prevalidación con simuladores de referencia.

Aer y CUDA-Q se ejecutan localmente cuando están instalados. D-Wave Leap es un
servicio remoto beta; su prueba se activa explícitamente y no se considera una
prueba CPU/offline. No se asume que los tres backends produzcan los mismos
conteos bit a bit: el ground truth son invariantes del circuito y tolerancias.
"""
from __future__ import annotations

import hashlib
from types import MappingProxyType

BASE_SEED = 20261016

REFERENCE_SIMULATORS = MappingProxyType({
    "qiskit_aer": MappingProxyType({
        "kind": "local_cpu",
        "package": "qiskit-aer",
        "seed_supported": True,
        "purpose": "statevector and standard noise-model reference",
    }),
    "cudaq_sim": MappingProxyType({
        "kind": "local_cpu_or_accelerated",
        "package": "cuda-quantum",
        "seed_supported": True,
        "purpose": "NVIDIA CUDA-Q reference simulator",
    }),
    "dwave_leap_beta": MappingProxyType({
        "kind": "remote_service",
        "package": "dwave-gate",
        "seed_supported": False,
        "purpose": "DRsim_21qubits gate-model beta via Leap/Ocean",
    }),
})

REFERENCE_PROBES = MappingProxyType({
    "bell": MappingProxyType({"qubits": 2, "shots": 2048, "invariant": "only correlated outcomes 00/11 in ideal mode"}),
    "ghz3": MappingProxyType({"qubits": 3, "shots": 2048, "invariant": "only 000/111 in ideal mode"}),
})


def seed_for(simulator_id: str, circuit_id: str, base_seed: int = BASE_SEED) -> int:
    """Stable 32-bit seed per simulator/circuit; independent of Python hash randomization."""
    if simulator_id not in REFERENCE_SIMULATORS:
        raise ValueError(f"Unknown reference simulator: {simulator_id}")
    if circuit_id not in REFERENCE_PROBES:
        raise ValueError(f"Unknown reference probe: {circuit_id}")
    material = f"LIBEQG-FaseC-v1|{base_seed}|{simulator_id}|{circuit_id}".encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:4], "big")


def validate_ideal_counts(counts: dict[str, int], circuit_id: str) -> bool:
    """Validate ideal-circuit invariants, not exact stochastic sample counts."""
    if circuit_id not in REFERENCE_PROBES or not counts:
        return False
    if any(not isinstance(n, int) or n < 0 for n in counts.values()):
        return False
    allowed = {"bell": {"00", "11"}, "ghz3": {"000", "111"}}[circuit_id]
    return all(bitstring.replace(" ", "") in allowed for bitstring, n in counts.items() if n > 0)
