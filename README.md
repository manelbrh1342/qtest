# qtest (pytest-quantum)

Mutation testing for quantum circuits written in Qiskit.

## Install
pip install -e .

## Usage
```python
@pytest.fixture
def quantum_circuit():
    qc = QuantumCircuit(2)
    qc.h(0); qc.cx(0, 1)
    return qc

@pytest.mark.quantum_mutate(circuit="quantum_circuit")
def test_bell(quantum_circuit):
    sv = Statevector(quantum_circuit)
    assert sv.probabilities_dict().get('11', 0) > 0.4
```

## License
MIT