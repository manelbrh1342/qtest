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

    expected_qc = QuantumCircuit(2)
    expected_qc.h(0)
    expected_qc.cx(0, 1)
    expected_sv = Statevector(expected_qc)
    assert sv.equiv(expected_sv)


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

    expected_qc = QuantumCircuit(3)
    expected_qc.h(0)
    expected_qc.cx(0, 1)
    expected_qc.cx(1, 2)
    expected_sv = Statevector(expected_qc)
    assert sv.equiv(expected_sv)


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

    n = 2
    expected_qc = QuantumCircuit(n + 1)
    expected_qc.x(n)
    expected_qc.h(range(n + 1))
    expected_qc.cx(0, n)
    expected_qc.h(range(n))
    expected_sv = Statevector(expected_qc)
    assert sv.equiv(expected_sv)


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

    expected_qc = QuantumCircuit(2)
    expected_qc.h([0, 1])
    expected_qc.cz(0, 1)
    expected_qc.h([0, 1])
    expected_qc.x([0, 1])
    expected_qc.cz(0, 1)
    expected_qc.x([0, 1])
    expected_qc.h([0, 1])
    expected_sv = Statevector(expected_qc)
    assert sv.equiv(expected_sv)


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

# Strong counterpart: full statevector comparison against the correct QFT circuit.
@pytest.mark.quantum_mutate(circuit="qft_circuit")
def test_qft_strong(qft_circuit):
    sv = Statevector(qft_circuit)
    expected_qc = QuantumCircuit(3)
    for i in range(3):
        expected_qc.h(i)
        for j in range(i + 1, 3):
            expected_qc.cp(np.pi / 2 ** (j - i), j, i)
    expected_qc.swap(0, 2)
    expected_sv = Statevector(expected_qc)
    assert sv.equiv(expected_sv)


# ── Parameterized ─────────────────────────────────────
@pytest.fixture
def param_circuit():
    theta = Parameter('theta')
    qc = QuantumCircuit(1)
    qc.h(0)
    qc.rz(theta, 0)
    return qc.assign_parameters({theta: np.pi / 2})

# NOTE: intentionally weak assertion (probability-only check misses phase
# and angle-sensitivity). Demonstrates qtest surfacing a low mutation score.
@pytest.mark.quantum_mutate(circuit="param_circuit")
def test_parameterized(param_circuit):
    sv = Statevector(param_circuit)
    probs = sv.probabilities_dict()
    assert probs.get('0', 0) > 0.3

# Strong counterpart: full statevector comparison against the correct bound circuit.
@pytest.mark.quantum_mutate(circuit="param_circuit")
def test_parameterized_strong(param_circuit):
    sv = Statevector(param_circuit)
    theta = Parameter('theta')
    expected_qc = QuantumCircuit(1)
    expected_qc.h(0)
    expected_qc.rz(theta, 0)
    expected_qc = expected_qc.assign_parameters({theta: np.pi / 2})
    expected_sv = Statevector(expected_qc)
    assert sv.equiv(expected_sv)


# ── Shor's Algorithm ──────────────────────────────────
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
# Work-register-only mutations post-entanglement are physically undetectable this way.
# Full-state sv.equiv() check added alongside to catch everything else.
@pytest.mark.quantum_mutate(circuit="shor_circuit")
def test_shor_period_finding(shor_circuit):
    n_count = 4
    sv = Statevector(shor_circuit)
    probs = sv.probabilities_dict(qargs=range(n_count))
    peak_mass = probs.get('0000', 0) + probs.get('0100', 0) + probs.get('1000', 0) + probs.get('1100', 0)
    assert peak_mass > 0.8

    n_work = 4
    expected_qc = QuantumCircuit(n_count + n_work)
    expected_qc.h(range(n_count))
    expected_qc.x(n_count)
    a = 7
    for i in range(n_count):
        exponent = 2 ** i
        expected_qc.append(c_amod15(a, exponent), [i, n_count+0, n_count+1, n_count+2, n_count+3])
    qft_inv = QFT(n_count, inverse=True).to_gate()
    expected_qc.append(qft_inv, range(n_count))
    expected_sv = Statevector(expected_qc)
    assert sv.equiv(expected_sv)


# ── VQC ───────────────────────────────────────────────
@pytest.fixture
def vqc_circuit():
    n_count = 4
    qc = QuantumCircuit(n_count)
    qc.ry(0.5, 0)
    qc.ry(1, 1)
    qc.ry(1.5, 2)
    qc.ry(2, 3)
    qc.rz(0.3, 0)
    qc.rz(0.6, 1)
    qc.rz(0.9, 2)
    qc.rz(1.2, 3)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(2, 3)
    return qc

@pytest.mark.quantum_mutate(circuit="vqc_circuit")
def test_vqc(vqc_circuit):
    cx_gates = [
        (vqc_circuit.find_bit(inst.qubits[0]).index, vqc_circuit.find_bit(inst.qubits[1]).index)
        for inst in vqc_circuit.data if inst.operation.name == 'cx'
    ]
    assert cx_gates == [(0, 1), (1, 2), (2, 3)]
    sv = Statevector(vqc_circuit)
    probs = sv.probabilities_dict()
    assert len(probs) > 1  # not collapsed to a single basis state

    expected_qc = QuantumCircuit(4)
    expected_qc.ry(0.5, 0)
    expected_qc.ry(1, 1)
    expected_qc.ry(1.5, 2)
    expected_qc.ry(2, 3)
    expected_qc.rz(0.3, 0)
    expected_qc.rz(0.6, 1)
    expected_qc.rz(0.9, 2)
    expected_qc.rz(1.2, 3)
    expected_qc.cx(0, 1)
    expected_qc.cx(1, 2)
    expected_qc.cx(2, 3)
    expected_sv = Statevector(expected_qc)
    assert sv.equiv(expected_sv)