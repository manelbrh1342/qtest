import copy
from qiskit import transpile
from qiskit_aer.primitives import SamplerV2
from qiskit_aer.noise import depolarizing_error, NoiseModel
from qiskit.quantum_info import Statevector
from qiskit.quantum_info import hellinger_fidelity
from qiskit_ibm_runtime import SamplerV2 as IBMSamplerV2

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

def is_killed_noisy(test_function, original_qc, mutant_qc, noise_rate, shots=1024, threshold=0.95):
    ideal_killed = is_killed_by_test(test_function, mutant_qc)
    if not ideal_killed:
        return (False, None, False)

    single_qubit_error = depolarizing_error(noise_rate, 1)
    two_qubit_error = depolarizing_error(noise_rate * 5, 2)
    three_qubit_error = depolarizing_error(noise_rate * 10, 3)
    noise_model = NoiseModel()
    noise_model.add_all_qubit_quantum_error(single_qubit_error, ['x', 'y', 'z', 'h', 's', 'sdg', 't', 'tdg', 'rx', 'ry', 'rz'])
    noise_model.add_all_qubit_quantum_error(two_qubit_error, ['cx', 'cz', 'swap', 'cp'])
    noise_model.add_all_qubit_quantum_error(three_qubit_error, ['ccx', 'cswap', 'ccz'])
    original_measured = copy.deepcopy(original_qc)
    original_measured.measure_all()
    mutant_measured = copy.deepcopy(mutant_qc)
    mutant_measured.measure_all()
    sampler = SamplerV2(options={"backend_options": {"noise_model": noise_model}})
    job = sampler.run([original_measured, mutant_measured], shots=shots)
    result = job.result()
    counts_original = result[0].data.meas.get_counts()
    counts_mutant = result[1].data.meas.get_counts()
    fidelity = hellinger_fidelity(counts_original, counts_mutant)
    return (fidelity < threshold, fidelity, True)

def is_killed_hardware_batch(test_function, original_qc, mutants, backend, shots=1024, threshold=0.95):
    ideal_killed_flags = [is_killed_by_test(test_function, mutant) for _, _, mutant in mutants]

    results = [None] * len(mutants)
    to_run = []
    for i, (operator, gate_idx, mutant) in enumerate(mutants):
        if ideal_killed_flags[i]:
            to_run.append((i, operator, gate_idx, mutant))
        else:
            results[i] = (operator, gate_idx, mutant, False, None, False)

    if to_run:
        original_measured = copy.deepcopy(original_qc)
        original_measured.measure_all()
        isa_original = transpile(original_measured, backend=backend, optimization_level=1)

        isa_mutants = []
        for i, operator, gate_idx, mutant in to_run:
            mutant_measured = copy.deepcopy(mutant)
            mutant_measured.measure_all()
            isa_mutants.append(transpile(mutant_measured, backend=backend, optimization_level=1))

        all_circuits = [isa_original] + isa_mutants

        sampler = IBMSamplerV2(mode=backend)
        job = sampler.run(all_circuits, shots=shots)
        result = job.result()

        counts_original = result[0].data.meas.get_counts()

        for pos, (i, operator, gate_idx, mutant) in enumerate(to_run):
            counts_mutant = result[pos + 1].data.meas.get_counts()
            fidelity = hellinger_fidelity(counts_original, counts_mutant)
            killed = fidelity < threshold
            results[i] = (operator, gate_idx, mutant, killed, fidelity, True)

    return results

def is_killed_by_test(test_function, mutant_circuit):
    try:
        test_function(mutant_circuit)
        return False 
    except AssertionError:
        return True  