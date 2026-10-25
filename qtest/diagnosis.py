from qiskit.quantum_info import Statevector, Operator
import numpy as np

def _probabilities_match(original,mutant, tol=1e-6):
    """Check if the probabilities of the original and mutant circuits match."""
    original_probs = Statevector(original).probabilities_dict()
    mutant_probs = Statevector(mutant).probabilities_dict()
    all_keys = set(original_probs) | set(mutant_probs)
    for key in all_keys:
        if abs(original_probs.get(key, 0.0) - mutant_probs.get(key, 0.0)) > tol:
            return False
    return True

def diagnose_survivor(original_qc, mutant_qc,noise_enabled=False,fidelity=None,threshold=0.95):
    if noise_enabled and fidelity is not None:
        return {
            "reason": "noise_survival",
            "explanation": (
                f"This mutant survived under noise with a fidelity of {fidelity:.4f}, "
                f"which is above the threshold of {threshold}. The survival may be due "
                    "to noise masking the difference between the original and mutant circuits."
                ),
            "suggestion": (
                    "Consider adjusting the noise rate or threshold, or strengthening your test "
                    "assertions to better detect differences under noise."
            )
            }
    orig_op = Operator(original_qc)
    mut_op = Operator(mutant_qc)
    orig_sv = Statevector(original_qc)
    mut_sv = Statevector(mutant_qc)
    if np.allclose(orig_op.data, mut_op.data):
        return {
            "reason": "equivalent_circuit",
            "explanation": ("This mutant is mathematically identical to the original circuit "
                            "on every possible input ,the change was a structural no-op"),
            "suggestion":"No action needed. This mutant is unkillable by design."
        }
        
    elif orig_op.equiv(mut_op):
        return {
            "reason": "global_phase",
            "explanation": (
                "This mutant differs from the original only by a global phase "
                "factor. Global phase is physically undetectable, so no measurement "
                "or assertion can distinguish these two circuits."
            ),
            "suggestion": (
                "No action needed. This mutant is unkillable by physics: "
                "global phase cannot be observed."
            )
        }
    
    elif orig_sv.equiv(mut_sv):
        return {
            "reason": "input_masked",
            "explanation": (
                "This mutant differs from the original, "
                "but gives the same output when the circuit starts from |0...0>."
                "The change has no effect on this input only."
            ),
            "suggestion": (
                "Consider using a different input state that is more sensitive to the "
                "changes introduced by the mutation."
            )
        }
    elif _probabilities_match(original_qc, mutant_qc):
        return {
            "reason": "weak_assertion_phase_blind",
            "explanation": (
                "This mutant produces a different quantum state, but only in "
                "phase. Your test only checks measurement probabilities, which "
                "cannot detect phase differences."
            ),
            "suggestion": (
                "Strengthen your assertion: replace or supplement your "
                "probabilities_dict() check with sv.equiv(expected_statevector) "
                "to catch phase-level differences."
            )
        }
    else:   
        return {
            "reason": "weak_assertion_fully_blind",
            "explanation": (
                "This mutant produces a substantially different quantum state, "
                "but your test assertion did not detect it. Your assertion likely "
                "checks a structural property (e.g. is_unitary()) rather than "
                "the actual circuit output."
            ),
            "suggestion": (
                "Replace your assertion with a statevector comparison: "
                "compute the expected statevector and assert sv.equiv(expected_state)."
            )
        }
    