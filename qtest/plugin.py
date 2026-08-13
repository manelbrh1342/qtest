import inspect

import pytest
from qtest.mutants import generate_all_mutants
from qtest.oracle import is_killed_by_test, is_killed_hardware_batch, is_killed_noisy, validate_circuit, is_killed
from qtest.diagnosis import diagnose_survivor
from qiskit_ibm_runtime import QiskitRuntimeService
_mutation_results = {}

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "quantum_mutate: run quantum mutation testing on this test"
    )

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    if not item.get_closest_marker("quantum_mutate"):
        outcome = yield
        return

    marker = item.get_closest_marker("quantum_mutate")
    fixture_name = marker.kwargs.get("circuit", "quantum_circuit")
    qc_fixture = item.funcargs.get(fixture_name)
    if qc_fixture is None:
        raise ValueError(
            f"quantum_mutate marker requires a '{fixture_name}' fixture. "
            f"Define it or pass the correct name via @pytest.mark.quantum_mutate(circuit='your_fixture_name')"
        )
    noise_enabled = item.config.getoption("--noise")
    noise_rate = item.config.getoption("--noise-rate")
    backend_name = item.config.getoption("--backend")
    validate_circuit(qc_fixture)
    mutants = generate_all_mutants(qc_fixture)
    killed = 0
    survived = []
    if backend_name:
        service = QiskitRuntimeService()
        backend = service.backend(backend_name)
        hw_results = is_killed_hardware_batch(
            qc_fixture, mutants, backend,
            shots=item.config.getoption("--shots"),
            threshold=item.config.getoption("--threshold")
        )
        for operator, gate_idx, mutant_killed, fidelity in hw_results:
            if mutant_killed:
                killed += 1
            else:
                diagnosis = diagnose_survivor(qc_fixture, None, inspect.getsource(item.function), noise_enabled=True, fidelity=fidelity, threshold=item.config.getoption("--threshold"))
                survived.append((operator, gate_idx, diagnosis, fidelity))
    else:
        for operator, gate_idx, mutant in mutants:
            if noise_enabled:
                mutant_killed, fidelity = is_killed_noisy(qc_fixture, mutant, noise_rate, shots=item.config.getoption("--shots"), threshold=item.config.getoption("--threshold"))
                if mutant_killed:
                    killed += 1
                else:
                    diagnosis = diagnose_survivor(qc_fixture, mutant, inspect.getsource(item.function), noise_enabled=True, fidelity=fidelity, threshold=item.config.getoption("--threshold"))
                    survived.append((operator, gate_idx, diagnosis, fidelity))
            else:
                if is_killed_by_test(item.function, mutant):
                    killed += 1
                else:
                    diagnosis = diagnose_survivor(qc_fixture, mutant, inspect.getsource(item.function), noise_enabled=False, fidelity=None, threshold=item.config.getoption("--threshold"))
                    survived.append((operator, gate_idx, diagnosis, None))
    total = len(mutants)
    score = killed / total if total > 0 else 0.0

    _mutation_results[item.nodeid] = {
        "score": score,
        "killed": killed,
        "total": total,
        "survived": survived
    }

    outcome = yield

def pytest_terminal_summary(terminalreporter):
    if not _mutation_results:
        return

    terminalreporter.write_sep("=", "qtest mutation summary")

    for nodeid, result in _mutation_results.items():
        score = result["score"]
        killed = result["killed"]
        total = result["total"]
        survived = result["survived"]

        terminalreporter.write_line(f"\n{nodeid}")
        terminalreporter.write_line(f"  Mutation Score : {score:.0%} ({killed}/{total} mutants killed)")

        if survived:
            terminalreporter.write_line("  Survived mutants:")
            for operator, gate_idx, diagnosis, fidelity in survived:
                terminalreporter.write_line(f"    - {operator} at gate {gate_idx}")
                terminalreporter.write_line(f"      Reason: {diagnosis['reason']}")
                if fidelity is not None:
                    terminalreporter.write_line(f"      Fidelity: {fidelity:.4f}")
                terminalreporter.write_line(f"      Explanation: {diagnosis['explanation']}")
                terminalreporter.write_line(f"      Suggestion: {diagnosis['suggestion']}")
