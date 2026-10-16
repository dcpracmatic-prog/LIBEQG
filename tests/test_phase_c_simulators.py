"""Fase C: pruebas deterministas de contrato e integraciones opcionales."""
import os

import pytest

from libeqg.phase_c import (
    BASE_SEED, REFERENCE_PROBES, REFERENCE_SIMULATORS,
    seed_for, validate_ideal_counts,
)


def test_phase_c_01_three_reference_simulators_are_declared():
    assert set(REFERENCE_SIMULATORS) == {"qiskit_aer", "cudaq_sim", "dwave_leap_beta"}
    assert REFERENCE_SIMULATORS["qiskit_aer"]["kind"] == "local_cpu"
    assert REFERENCE_SIMULATORS["cudaq_sim"]["seed_supported"] is True
    assert REFERENCE_SIMULATORS["dwave_leap_beta"]["kind"] == "remote_service"
    assert REFERENCE_SIMULATORS["dwave_leap_beta"]["seed_supported"] is False


def test_phase_c_02_seeds_are_stable_and_backend_specific():
    a = seed_for("qiskit_aer", "bell")
    assert a == seed_for("qiskit_aer", "bell")
    assert a != seed_for("cudaq_sim", "bell")
    assert a != seed_for("qiskit_aer", "ghz3")
    assert BASE_SEED == 20261016
    assert REFERENCE_PROBES["bell"]["shots"] == 2048


@pytest.mark.parametrize(("circuit", "valid", "invalid"), [
    ("bell", {"00": 1000, "11": 1048}, {"00": 1000, "01": 1}),
    ("ghz3", {"000": 1000, "111": 1048}, {"000": 1000, "101": 1}),
])
def test_phase_c_03_ground_truth_invariants(circuit, valid, invalid):
    assert validate_ideal_counts(valid, circuit)
    assert not validate_ideal_counts(invalid, circuit)
    assert not validate_ideal_counts({}, circuit)


def test_phase_c_04_aer_local_cpu_deterministic_bell():
    pytest.importorskip("qiskit")
    pytest.importorskip("qiskit_aer")
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator

    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure_all()
    seed = seed_for("qiskit_aer", "bell")
    backend = AerSimulator(method="statevector")
    first = backend.run(circuit, shots=2048, seed_simulator=seed).result().get_counts()
    second = backend.run(circuit, shots=2048, seed_simulator=seed).result().get_counts()
    assert first == second
    assert validate_ideal_counts(first, "bell")


def test_phase_c_05_cudaq_local_simulator_seeded_bell():
    pytest.importorskip("cudaq")
    import cudaq

    @cudaq.kernel
    def bell():
        q = cudaq.qvector(2)
        h(q[0])
        x.ctrl(q[0], q[1])
        mz(q)

    cudaq.set_random_seed(seed_for("cudaq_sim", "bell"))
    counts = cudaq.sample(bell, shots_count=2048)
    observed = {str(bits).replace(" ", ""): int(counts.count(bits)) for bits in counts}
    assert validate_ideal_counts(observed, "bell")


@pytest.mark.skipif(
    os.getenv("LIBEQG_ENABLE_DWAVE_BETA") != "1",
    reason="D-Wave Leap beta es remoto; activar explícitamente con LIBEQG_ENABLE_DWAVE_BETA=1 y credenciales autorizadas",
)
def test_phase_c_06_dwave_leap_beta_bell_smoke():
    pytest.importorskip("dwave.gate")
    from dwave.gate.leap import LeapQCDLSimulator
    from dwave.gate.qcdl import qcdl
    from dwave.gate.qcdl.operations import cx, h, measure

    @qcdl(2)
    def bell_program(q0, q1):
        h(q0)
        cx(q0, q1)
        measure(q0)
        measure(q1)

    simulator = LeapQCDLSimulator()
    future = simulator.run(
        bell_program(), qpu="DRsim_21qubits", shots=512,
        label="LIBEQG-FaseC-Bell-Reference",
    )
    result = future.result().result
    counts = result.get_counts()
    # D-Wave's documented API returns a list of per-measurement count maps.
    if isinstance(counts, list):
        assert counts
        counts = counts[0]
    assert counts and sum(counts.values()) > 0
