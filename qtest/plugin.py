import inspect

import pytest
from qtest.mutants import generate_all_mutants
from qtest.oracle import validate_circuit, is_killed
from qtest.diagnosis import diagnose_survivor
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
    validate_circuit(qc_fixture)
    mutants = generate_all_mutants(qc_fixture)
    killed = 0
    survived = []

    for operator, gate_idx, mutant in mutants:
        if is_killed(qc_fixture, mutant):
            killed += 1
        else:
            diagnosis = diagnose_survivor(qc_fixture, mutant,  inspect.getsource(item.function))
            survived.append((operator, gate_idx, diagnosis))

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
            for operator, gate_idx, diagnosis in survived:
                terminalreporter.write_line(f"    - {operator} at gate {gate_idx}")
                terminalreporter.write_line(f"      Reason: {diagnosis['reason']}")
                terminalreporter.write_line(f"      Explanation: {diagnosis['explanation']}")
                terminalreporter.write_line(f"      Suggestion: {diagnosis['suggestion']}")