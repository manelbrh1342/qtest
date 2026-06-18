from qiskit.quantum_info import Statevector
from qiskit import QuantumCircuit


def validate_circuit(qc):
    if qc.num_parameters > 0:
        raise ValueError(
            f"quantum_circuit has {qc.num_parameters} unbound parameter(s): "
            f"{list(qc.parameters)}. Call assign_parameters() before testing."
        )
    has_measurements = any(
        inst.operation.name == 'measure' for inst in qc.data
    )
    if has_measurements:
        raise ValueError(
            "quantum_circuit contains measurements. "
            "Remove them with qc.remove_final_measurements() before testing."
        )


def is_killed(original_qc, mutant_qc):
    sv_orig = Statevector(original_qc)
    sv_mut = Statevector(mutant_qc)
    return not sv_orig.equiv(sv_mut)