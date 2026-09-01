# qtest (pytest-quantum)

Mutation testing for Qiskit quantum circuits, delivered as a pytest plugin.

## Why qtest exists

Classical code fails loudly, most of the time. A wrong index throws an exception, a bad comparison crashes a test, a broken loop produces an obviously wrong number. Quantum circuits don't behave like that. A circuit is inherently probabilistic, its output is a distribution of possible measurement outcomes, not a single deterministic value. A bug in a quantum circuit, a wrong angle, a swapped qubit, a flipped control, usually doesn't crash anything or throw an error. It just quietly shifts the probabilities, and a test that only checks "did I get a plausible-looking answer most of the time" can pass on a genuinely broken circuit without anyone noticing.

This makes ordinary testing intuition unreliable for quantum code. A test suite can look complete, every function has a test, every test passes, and still be blind to real bugs, because probabilistic output gives a false sense of coverage that deterministic output never would. qtest exists to close that gap: instead of asking "does the circuit look right," it asks "if this circuit were subtly wrong, would the test suite actually notice." That is a question ordinary testing has no good way to answer on its own, and it is the reason mutation testing, not just testing, is the right tool for quantum software.

## What qtest does

qtest takes the circuit under test, generates a set of deliberately broken variants of it (mutants), runs your existing test function against each mutant, and records whether your test raised an assertion failure. A test that fails on a mutant "killed" it. A test that passes on a mutant, meaning it could not tell the broken circuit from the correct one, let that mutant "survive."

The proportion of killed mutants is the mutation score. A low score does not mean your circuit is wrong. It means your tests would not have caught it if it were.

When a mutant survives, qtest does not just report a number and move on. It runs a diagnosis step that figures out why the mutant survived: because the mutation was physically undetectable and no test could ever catch it, or because the mutation was genuinely a bug and the test simply wasn't checking the right thing. That distinction is the core of what makes the score actionable instead of just a statistic.

## The pipeline, end to end

1. The developer writes a normal Qiskit circuit and a normal pytest test function for it, and marks the test with `@pytest.mark.quantum_mutate`.
2. qtest generates the full set of mutants for that circuit (see Mutation Operators below).
3. Each mutant is run through the developer's own test function. qtest calls the test function with the mutant circuit in place of the original and watches whether an `AssertionError` is raised. There is no separate, built-in notion of correctness competing with this, the test function itself is the entire oracle for the default path.
4. Every mutant that raised an assertion error counts as killed. Every mutant that did not is a survivor.
5. Each survivor goes through the diagnosis engine, which classifies why it survived and tells the developer what, if anything, to do about it.
6. A summary is printed at the end of the pytest run: mutation score, killed/total, and a per-survivor breakdown with reason, explanation, and suggested fix.

This means the mutation score is always tied to what the test body actually checks, not to some separate notion of "the mutant looks different." If a test's assertions are weak, the score reflects that honestly.

## Installation and basic usage

```bash
pip install qtest
```

A test using qtest looks like an ordinary pytest test, with two additions: a fixture that builds the circuit, and the `quantum_mutate` marker.

```python
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

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
```

Running `pytest` executes the test normally, then, because of the marker, qtest mutates `bell_circuit`, replays this test function against every mutant, and appends the mutation report to the terminal output.

> **Default fixture name.** If the `quantum_mutate` marker is used without a `circuit=` argument, qtest looks for a fixture named exactly `quantum_circuit`. If your fixture is named anything else and you forget to pass `circuit="your_fixture_name"`, qtest will not find it and the test will fail with a missing-fixture error rather than silently skipping mutation. Always pass `circuit=` explicitly unless your fixture is genuinely named `quantum_circuit`.

## Circuit requirements

Before mutating a circuit, qtest validates it, and rejects it for two reasons:

**All parameters must be bound.** In Qiskit, `Parameter('theta')` is a named placeholder with no numeric value attached yet, the circuit equivalent of an algebra variable. A circuit built with `qc.rz(theta, 0)` has no concrete rotation until `assign_parameters({theta: some_number})` is called on it. Before that call, the circuit is symbolic, and there is no single quantum state to compute or compare, only a formula. qtest needs an actual, concrete statevector to run its comparisons against, so any circuit with an unbound ("free") parameter is rejected until it's bound to a real number.

**The circuit must not contain measurement instructions.** `Statevector()` represents the full quantum state, every amplitude, exactly as it exists before anything is observed. A measurement instruction collapses that state into one random classical outcome and destroys the information qtest needs to compare states precisely. The default oracle therefore requires a clean, unmeasured circuit, so it can compute one deterministic statevector rather than a randomized classical outcome. Strip measurements first with `qc.remove_final_measurements()`. The noisy and hardware oracles work differently and add their own measurements internally, on private copies of the circuit, immediately before running, since they need actual shot counts rather than a statevector.

## Mutation operators

qtest currently applies seven operators. Every operator produces one mutant per applicable location in the circuit, and all of them run by default through `generate_all_mutants`.

| Operator | What it changes | Example |
|---|---|---|
| Deletion | Removes one instruction from the circuit entirely | An `h(0)` gate simply disappears |
| Replacement | Swaps a gate for a different gate acting on the same qubits | `h` becomes `x`, `y`, or `z`; `cx` becomes `cz` or `swap`; a parameterized gate becomes a different rotation axis around the same angle |
| Parameter negation | Flips the sign of a gate's rotation angle | `rz(theta)` becomes `rz(-theta)` |
| Qubit swap | Reverses the qubit order a two-qubit gate acts on | `cx(0, 1)` becomes `cx(1, 0)` |
| Parameter perturbation | Nudges a rotation angle by a small fixed epsilon | `rz(theta)` becomes `rz(theta + 0.01)`, catching near-miss angle bugs that negation would miss |
| Gate insertion | Inserts an extra X or Z gate at every position, on every qubit | Simulates a stray or duplicated operation slipping into the circuit |
| Control flip | Wraps the control qubit of a controlled gate with an X before and after | Equivalent to flipping which basis state triggers the controlled operation |

Identity insertion is deliberately excluded from gate insertion, since an inserted identity is always a no-op and would only inflate the mutant count without ever being killable.

## How a mutant is judged killed or survived

**Default oracle.** qtest calls the developer's own test function with the mutant circuit substituted in for the fixture, and catches the outcome. The test raises `AssertionError`: the mutant is killed. The test runs to completion without error: the mutant survived. This is why the mutation score is tied to the actual content of the test body. A test that only checks `Operator(qc).is_unitary()` will pass on almost any mutant, since nearly every mutation still produces a valid unitary, so its score will be low. A test that compares the full statevector against an independently built reference circuit will catch far more, and score accordingly.

**Noisy oracle**, enabled with `--noise`. Real hardware is never perfectly clean, gates introduce small errors, and this oracle simulates that. It first checks whether the developer's test would have killed the mutant under ideal, noiseless conditions, using the exact same check as the default oracle. If the test would not have caught the mutant even ideally, the mutant is routed straight to the normal weak-assertion diagnosis, noise is never blamed for a gap that was never about noise. Only if the test would have caught the mutant ideally does qtest proceed to the noisy comparison: both the original and the mutant are run with shots through a depolarizing noise model on the Aer simulator, and their resulting measurement distributions are compared using Hellinger fidelity.

Hellinger fidelity is a similarity score between 0 and 1 for two probability distributions, built from shot counts rather than exact amplitudes. 1 means the two distributions look identical, 0 means they share no overlap at all. It's used here because noisy or real-hardware execution never gives you a clean, exact statevector, only a histogram of outcomes across many repeated runs, so an exact `.equiv()` comparison isn't available and a tolerance-based similarity score is used instead. If fidelity stays above the configured `--threshold`, the mutant counts as surviving under noise.

**Hardware oracle**, enabled with `--backend`. Same idea as the noisy oracle, but run on a real IBM quantum device instead of a simulated noise model. It also checks ideal killability first, for every mutant, before spending real hardware time on any of them, only mutants the test would have caught ideally are actually submitted to hardware. The rest go straight to weak-assertion diagnosis without consuming a single real shot.

To use `--backend`, you need access to an actual IBM device:

1. Create a free account at quantum.ibm.com (the Open Plan tier is sufficient for the circuit sizes used here).
2. Save your credentials once locally: `QiskitRuntimeService.save_account(channel="ibm_quantum", token="your_token_here")`.
3. List the backends currently available to your account: `QiskitRuntimeService().backends()`. This returns the real, current device names for your specific account, don't guess or hardcode a name, since availability varies by account and can change over time. Always check what your own call to `.backends()` returns rather than assuming a fixed list.
4. Pass the chosen name to pytest: `pytest --backend ibm_marrakesh`.

## Diagnosis engine

When a mutant survives, qtest doesn't stop at "your test missed this." It works out which of several distinct situations is actually the case, using `Operator.equiv()`, `Statevector.equiv()`, and a probability comparison, in that order, as direct, physical ground-truth checks:

**Equivalent circuit.** The mutant is unitarily identical to the original on every possible input, not just the specific state under test. The mutation was a structural no-op. No test could ever kill it, and none should try. Nothing to fix.

**Global phase.** The statevectors differ only by an overall phase factor. This is physically unobservable: no measurement, on any basis, can distinguish the two circuits. This is expected behavior, not a weakness in the test, and is documented as such rather than flagged as something to fix.

**Weak assertion, phase blind.** The two circuits produce identical measurement probabilities, but different statevectors. The test only checked probabilities (for example `probabilities_dict()`), which cannot see phase, so it missed a real, physically detectable difference. The suggested fix is to add a statevector-level comparison, `sv.equiv(expected_state)`, alongside or instead of the probability check.

**Weak assertion, fully blind.** The statevectors are substantially different and the difference is measurable, but the test's assertion still didn't catch it, typically because it was checking a structural property like `is_unitary()` rather than the actual output state. This is the strongest case of a genuine test gap. The fix is the same: replace the structural check with a direct comparison against an independently computed expected statevector.

**Noise survival.** Specific to the noisy and hardware oracles, and only ever reached for a mutant the developer's test would have killed under ideal, noiseless conditions. It means the underlying difference is real and would ordinarily be caught, but under noise or on real hardware, the fidelity between original and mutant stayed above threshold anyway, the noise blurred the signal enough to hide a genuine bug statistically. The suggestion is to lower the noise rate, increase shots, or tighten the threshold, unlike global phase, this is not a permanent, unfixable situation, it's a measurement sensitivity problem.

## CLI options

| Flag | Purpose | Default |
|---|---|---|
| `--noise` | Switch the oracle from exact statevector comparison to the noisy sampler oracle | off |
| `--noise-rate` | Depolarizing error rate applied per gate under `--noise` (0 to 0.05) | 0.01 |
| `--shots` | Number of shots used by the noisy or hardware oracle | 1024 |
| `--threshold` | Minimum Hellinger fidelity for a mutant to count as survived under noise or hardware | 0.95 |
| `--backend` | Name of an IBM Quantum backend to run the hardware oracle against (for example `ibm_marrakesh`) | none |

## Reading the report

At the end of a run, qtest prints a summary per test:

```
qtest mutation summary

tests/test_standard_circuits.py::test_qft
  Mutation Score : 12% (3/25 mutants killed)
  Survived mutants:
    - replacement at gate 4
      Reason: weak_assertion_fully_blind
      Explanation: This mutant produces a substantially different quantum state,
      but your test assertion did not detect it...
      Suggestion: Replace your assertion with a statevector comparison...
```

Each survivor line names the operator and location that produced the mutant, the diagnosis reason, and the explanation and suggestion generated for that reason. When the noisy or hardware oracle was used, the fidelity value is included as well.

## Supported circuits

qtest's own test suite exercises the plugin against eight standard circuit types, each included specifically to stress a different part of the mutation and diagnosis machinery: Bell state, GHZ state, Deutsch-Jozsa, Grover (2 qubit), QFT, a parameterized single-qubit circuit (Hadamard followed by a bound RZ rotation, so the phase introduced by RZ is actually observable), Shor's algorithm (N = 15), and a 4-qubit variational quantum classifier.

These eight are examples used to validate qtest itself and to generate before/after evidence of what strong versus weak testing looks like, they are not a whitelist or a fixed catalog of circuits qtest supports. qtest works with any ordinary Qiskit `QuantumCircuit`, of any shape or algorithm, as long as it meets the two requirements above: all parameters bound, no measurement instructions left in it. A developer's circuit does not need to resemble any of the eight in structure, size, or purpose to be usable with qtest.

## Design principles

**The oracle runs the real test, not a proxy for it.** Mutation score is meaningless if it doesn't reflect what the test actually checks. This is why the default oracle calls the developer's test function directly against each mutant, and why the noisy and hardware oracles check that same ideal outcome first before ever attributing a survival to noise.

**Unkillable is not the same as untested.** A mutant that survives because it is physically equivalent to the original, or because it differs only by global phase, is not a gap in the test suite. qtest's diagnosis engine exists specifically to keep that distinction from getting lost in a single aggregate score.

**Weak tests are meant to be visible, not hidden.** The QFT and parameterized circuits ship with both a weak and a strong version of their tests intentionally, to show the score moving from close to zero toward the circuit's physical ceiling, depending only on what the assertion checks. That ceiling is rarely 100%: once a strong assertion catches every physically detectable difference, remaining survivors are typically global-phase or structurally-equivalent mutants that no test could ever kill. A strong QFT test, for example, reaches 49%, with every surviving mutant diagnosed as unkillable by physics or by design, not by a gap in the assertion.

## License

MIT.