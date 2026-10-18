"""Pruebas de contrato y ejecución de los backends CPU opcionales."""
import json
import pytest

from libeqg.phase_c import BASE_SEED, REFERENCE_PROBES, REFERENCE_SIMULATORS, seed_for, validate_ideal_counts
from libeqg.validation import _check_distribution, run_cpu_validation


def test_reference_backend_contract():
    assert REFERENCE_SIMULATORS["qiskit_aer"]["kind"] == "local_cpu"
    assert REFERENCE_SIMULATORS["cudaq_sim"]["kind"] == "local_cpu"
    assert REFERENCE_SIMULATORS["dwave_leap_beta"]["kind"] == "remote_service"
    assert BASE_SEED == 20261016
    assert REFERENCE_PROBES["bell"]["shots"] == 2048


def test_seed_is_stable_and_backend_specific():
    assert seed_for("qiskit_aer", "bell") == seed_for("qiskit_aer", "bell")
    assert seed_for("qiskit_aer", "bell") != seed_for("cudaq_sim", "bell")
    assert seed_for("qiskit_aer", "bell") != seed_for("qiskit_aer", "ghz3")


@pytest.mark.parametrize(("circuit", "valid", "invalid"), [
    ("bell", {"00": 1000, "11": 1048}, {"00": 1000, "01": 1}),
    ("ghz3", {"000": 1000, "111": 1048}, {"000": 1000, "101": 1}),
])
def test_ground_truth_invariants(circuit, valid, invalid):
    assert validate_ideal_counts(valid, circuit)
    assert not validate_ideal_counts(invalid, circuit)
    assert not validate_ideal_counts({}, circuit)


def test_distribution_rejects_unbalanced_results():
    with pytest.raises(AssertionError):
        _check_distribution({"00": 2040, "11": 8}, "bell")


def test_aer_executes_on_cpu_when_installed():
    pytest.importorskip("qiskit")
    pytest.importorskip("qiskit_aer")
    result = __import__("libeqg.validation", fromlist=["validate_aer_cpu"]).validate_aer_cpu()
    assert result["status"] == "PASS", result


def test_cudaq_executes_on_qpp_cpu_when_installed():
    pytest.importorskip("cudaq")
    result = __import__("libeqg.validation", fromlist=["validate_cudaq_cpu"]).validate_cudaq_cpu()
    assert result["status"] == "PASS", result


def test_default_report_marks_dwave_disabled_and_does_not_require_it(tmp_path):
    report_path = tmp_path / "report.json"
    report = run_cpu_validation(report_path)
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["dwave"] == "DISABLED_BY_DEFAULT"
    assert saved["dwave"] == "DISABLED_BY_DEFAULT"
    assert "dwave_leap_beta" not in {item["backend"] for item in report["results"]}
