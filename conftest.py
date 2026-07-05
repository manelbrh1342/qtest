import argparse


def valid_noise_rate(value):
    try:
        rate = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid noise rate: {value}. Must be a float between 0 and 0.05 .")
    if not (0 <= rate <= 0.05):
        raise argparse.ArgumentTypeError(f"Invalid noise rate: {value}. Must be between 0 and 0.05 .")
    return rate
def pytest_addoption(parser):
    parser.addoption(
        "--noise", action="store_true", default=False, help="Enable noise in tests"
    )
    parser.addoption(
        "--noise-rate", action="store", type=valid_noise_rate, default=0.01, help="Set noise rate for tests"
    )
    parser.addoption(
        "--shots", action="store", type=int, default=1024, help="Set number of shots for noisy tests"
    )
    parser.addoption(
        "--threshold", action="store", type=float, default=0.95, help="Set fidelity threshold for noisy tests"
    )
    parser.addoption("--backend", action="store", default=None,
                  help="IBM backend name for hardware execution (e.g. ibm_marrakesh)")
