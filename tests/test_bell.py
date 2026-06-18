import pytest
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
@pytest.fixture
def quantum_circuit():
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    return qc

@pytest.mark.quantum_mutate
def test_bell(quantum_circuit):
    sv = Statevector(quantum_circuit)
    probs = sv.probabilities_dict()
    assert probs.get('00', 0) > 0.4
    assert probs.get('11', 0) > 0.4
    assert '01' not in probs
    assert '10' not in probs