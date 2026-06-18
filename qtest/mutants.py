import copy
from qiskit.circuit.library import (
    HGate, XGate, YGate, ZGate,
    RXGate, RYGate, RZGate,
    CXGate, CZGate, SwapGate
)

SINGLE_QUBIT_REPLACEMENTS = [HGate, XGate, YGate, ZGate]
PARAM_REPLACEMENTS = [RXGate, RYGate, RZGate]
TWO_QUBIT_REPLACEMENTS = [CXGate, CZGate, SwapGate]

def deletion_mutants(qc):
    mutants = []
    for i in range(len(qc.data)):
        new_qc = copy.deepcopy(qc)
        del new_qc.data[i]
        mutants.append(('deletion', i, new_qc))
    return mutants

def replacement_mutants(qc):
    mutants = []
    for i, inst in enumerate(qc.data):
        name = inst.operation.name
        params = inst.operation.params

        if params and inst.operation.num_qubits == 1:
            candidates = [g for g in PARAM_REPLACEMENTS if g(0).name != name]
        elif inst.operation.num_qubits == 2:
            candidates = [g for g in TWO_QUBIT_REPLACEMENTS if g().name != name]
        elif not params:
            candidates = [g for g in SINGLE_QUBIT_REPLACEMENTS if g().name != name]
        else:
            candidates = []
        for gate_class in candidates:
            new_qc = copy.deepcopy(qc)
            if inst.operation.num_qubits == 2:
                new_gate = gate_class()
            else:
                new_gate = gate_class(*params)
            new_qc.data[i] = inst.replace(operation=new_gate)
            mutants.append(('replacement', i, new_qc))

    return mutants

def param_negation_mutants(qc):
    mutants = []
    for i, inst in enumerate(qc.data):
        if inst.operation.params:
            new_qc = copy.deepcopy(qc)
            old_param = inst.operation.params[0]
            gate_class = type(inst.operation)
            new_gate = gate_class(-old_param)
            new_qc.data[i] = inst.replace(operation=new_gate)
            mutants.append(('param_negation', i, new_qc))
    return mutants

def qubit_swap_mutants(qc):
    mutants = []
    for i, inst in enumerate(qc.data):
        if inst.operation.num_qubits == 2:
            new_qc = copy.deepcopy(qc)
            swapped_qubits = list(reversed(inst.qubits))
            new_qc.data[i] = inst.replace(qubits=swapped_qubits)
            mutants.append(('qubit_swap', i, new_qc))
    return mutants

def generate_all_mutants(qc):
    return (
        deletion_mutants(qc) +
        replacement_mutants(qc) +
        param_negation_mutants(qc) +
        qubit_swap_mutants(qc)
    )