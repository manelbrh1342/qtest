import copy
from qiskit.circuit.library import (
    HGate, XGate, YGate, ZGate,
    RXGate, RYGate, RZGate,
    CXGate, CZGate, SwapGate
)

SINGLE_QUBIT_REPLACEMENTS = [HGate, XGate, YGate, ZGate]
PARAM_REPLACEMENTS = [RXGate, RYGate, RZGate]
TWO_QUBIT_REPLACEMENTS = [CXGate, CZGate, SwapGate]
CONTROLLED_GATE_NAMES = {'cx', 'cz', 'cy', 'ch', 'cp', 'crx', 'cry', 'crz', 'ccx', 'cswap'}
INSERTION_GATES       = [XGate, ZGate]   # I omitted: always a no-op, never killable
 
PERTURBATION_EPSILON  = 0.01
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
        elif inst.operation.num_qubits == 1 and not params:
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

def param_perturbation_mutants(qc, epsilon=PERTURBATION_EPSILON):
    """
    RZ(θ) → RZ(θ + ε).  Catches near-miss bugs where an angle is almost right.
    Complements param_negation: negation catches sign flips, perturbation catches
    small drifts.  Both are detectable by Statevector.equiv().
    """
    mutants = []
    for i, inst in enumerate(qc.data):
        if inst.operation.params:
            new_qc     = copy.deepcopy(qc)
            gate_class = type(inst.operation)
            new_gate   = gate_class(inst.operation.params[0] + epsilon)
            new_qc.data[i] = inst.replace(operation=new_gate)
            mutants.append(('param_perturbation', i, new_qc))
    return mutants
 
def gate_insertion_mutants(qc):
    """
    Insert an extra X or Z gate at every position in the circuit, on every qubit.
    I (identity) is intentionally excluded — it is always a no-op and produces
    mutants that can never be killed, inflating the total count without value.
    Each insertion produces a circuit that is one gate longer than the original.
    """
    mutants = []
    n_positions = len(qc.data) + 1   # before first gate, between each pair, after last
 
    for pos in range(n_positions):
        for qubit in qc.qubits:
            for gate_class in INSERTION_GATES:
                new_qc   = copy.deepcopy(qc)
                new_gate = gate_class()
                # Build a CircuitInstruction from the new gate + target qubit.
                # We re-use inst.replace() on the nearest existing instruction
                # so the CircuitInstruction type is correct.
                anchor    = qc.data[min(pos, len(qc.data) - 1)]
                new_inst  = anchor.replace(operation=new_gate, qubits=(qubit,), clbits=())
                new_qc.data.insert(pos, new_inst)
                mutants.append(('gate_insertion', pos, new_qc))
 
    return mutants
 
def control_flip_mutants(qc):
    """
    For every controlled gate, insert X before and after its control qubit.
    X·CX·X on the control is equivalent to flipping which basis state triggers
    the gate — a subtle semantic bug that probability-only tests often miss.
    """
    mutants = []
    for i, inst in enumerate(qc.data):
        if inst.operation.name not in CONTROLLED_GATE_NAMES:
            continue
        if len(inst.qubits) < 2:
            continue
 
        control_qubit = inst.qubits[0]   # by convention, first qubit is control
        new_qc        = copy.deepcopy(qc)
        x_gate        = XGate()
 
        # Build X instructions targeting the control qubit
        x_before = inst.replace(operation=x_gate, qubits=(control_qubit,), clbits=())
        x_after  = inst.replace(operation=x_gate, qubits=(control_qubit,), clbits=())
 
        # Insert after (i+1) first so index i stays valid, then insert before i
        new_qc.data.insert(i + 1, x_after)
        new_qc.data.insert(i,     x_before)
        mutants.append(('control_flip', i, new_qc))
 
    return mutants

def generate_all_mutants(qc):
    return (
        deletion_mutants(qc) +
        replacement_mutants(qc) +
        param_negation_mutants(qc) +
        qubit_swap_mutants(qc) +
        param_perturbation_mutants(qc) +
        gate_insertion_mutants(qc) +
        control_flip_mutants(qc)
    )
    
