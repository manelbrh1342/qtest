import pytest
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit.circuit import Parameter
from qiskit.circuit.library import QFT

from tests.shor_helpers import c_amod15


# ── Bell ──────────────────────────────────────────────
@pytest.fixture
def bell_circuit():
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    return qc

@pytest.mark.quantum_mutate(circuit="bell_circuit")
def test_bell(bell_circuit):
    sv = Statevector(bell_circuit)
    probs = sv.probabilities_dict()
    assert probs.get('00', 0) > 0.4
    assert probs.get('11', 0) > 0.4
    assert '01' not in probs
    assert '10' not in probs


# ── GHZ ───────────────────────────────────────────────
@pytest.fixture
def ghz_circuit():
    qc = QuantumCircuit(3)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    return qc

@pytest.mark.quantum_mutate(circuit="ghz_circuit")
def test_ghz(ghz_circuit):
    sv = Statevector(ghz_circuit)
    probs = sv.probabilities_dict()
    assert probs.get('000', 0) > 0.4
    assert probs.get('111', 0) > 0.4


# ── Deutsch-Jozsa ─────────────────────────────────────
@pytest.fixture
def dj_circuit():
    n = 2
    qc = QuantumCircuit(n + 1)
    qc.x(n)
    qc.h(range(n + 1))
    qc.cx(0, n)
    qc.h(range(n))
    return qc

@pytest.mark.quantum_mutate(circuit="dj_circuit")
def test_deutsch_jozsa(dj_circuit):
    sv = Statevector(dj_circuit)
    probs = sv.probabilities_dict()
    balanced_outcomes = [k for k in probs if k[0] == '1']
    assert len(balanced_outcomes) > 0


# ── Grover ────────────────────────────────────────────
@pytest.fixture
def grover_circuit():
    qc = QuantumCircuit(2)
    qc.h([0, 1])
    qc.cz(0, 1)
    qc.h([0, 1])
    qc.x([0, 1])
    qc.cz(0, 1)
    qc.x([0, 1])
    qc.h([0, 1])
    return qc

@pytest.mark.quantum_mutate(circuit="grover_circuit")
def test_grover(grover_circuit):
    sv = Statevector(grover_circuit)
    probs = sv.probabilities_dict()
    assert probs.get('11', 0) > 0.8


# ── QFT ───────────────────────────────────────────────
@pytest.fixture
def qft_circuit():
    qc = QuantumCircuit(3)
    for i in range(3):
        qc.h(i)
        for j in range(i + 1, 3):
            qc.cp(np.pi / 2 ** (j - i), j, i)
    qc.swap(0, 2)
    return qc

# NOTE: intentionally weak assertion (is_unitary() checks format, not value).
# Demonstrates qtest surfacing a low mutation score on a naive test
@pytest.mark.quantum_mutate(circuit="qft_circuit")
def test_qft(qft_circuit):
    from qiskit.quantum_info import Operator
    op = Operator(qft_circuit)
    assert op.is_unitary()


# ── Parameterized ─────────────────────────────────────
@pytest.fixture
def param_circuit():
    theta = Parameter('theta')
    qc = QuantumCircuit(1)
    qc.rz(theta, 0)
    return qc.assign_parameters({theta: np.pi / 2})
# NOTE: intentionally weak assertion (probability-only check misses phase
# and angle-sensitivity). Demonstrates qtest surfacing a low mutation score.

@pytest.mark.quantum_mutate(circuit="param_circuit")
def test_parameterized(param_circuit):
    sv = Statevector(param_circuit)
    probs = sv.probabilities_dict()
    assert probs.get('0', 0) > 0.9

@pytest.fixture
def shor_circuit():
    n_count = 4
    n_work = 4
    qc = QuantumCircuit(n_count + n_work)
    qc.h(range(n_count))
    qc.x(n_count)
    a = 7
    for i in range(n_count):
        exponent = 2 ** i
        qc.append(c_amod15(a, exponent), [i, n_count+0, n_count+1, n_count+2, n_count+3])
    qft_inv = QFT(n_count, inverse=True).to_gate()
    qc.append(qft_inv, range(n_count))
    return qc

# Assertion checks counting-register marginal only, matching real Shor's measurement practice. 
# Work-register-only mutations post-entanglement are physically undetectable this way

@pytest.mark.quantum_mutate(circuit="shor_circuit")
def test_shor_period_finding(shor_circuit):
    n_count = 4
    sv= Statevector(shor_circuit)
    probs = sv.probabilities_dict(qargs=range(n_count))
    peak_mass =probs.get('0000', 0) + probs.get('0100', 0) + probs.get('1000', 0) + probs.get('1100', 0)
    assert peak_mass > 0.8