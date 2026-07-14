
from qiskit import QuantumCircuit


def c_amod15(a, power):
    """
    Controlled multiplication by a^power mod 15.
    Valid a values: 2, 4, 7, 8, 11, 13 (the units mod 15).
    Acts on a 4-qubit work register.
    """
    if a not in [2, 4, 7, 8, 11, 13]:
        raise ValueError("'a' must be one of 2,4,7,8,11,13 for mod 15")

    U = QuantumCircuit(4)
    for _iteration in range(power):
        if a in [2, 13]:
            U.swap(2, 3)
            U.swap(1, 2)
            U.swap(0, 1)
        if a in [7, 8]:
            U.swap(0, 1)
            U.swap(1, 2)
            U.swap(2, 3)
        if a in [4, 11]:
            U.swap(1, 3)
            U.swap(0, 2)
        if a in [7, 11, 13]:
            for q in range(4):
                U.x(q)
    U = U.to_gate()
    U.name = f"{a}^{power} mod 15"
    c_U = U.control()
    return c_U
