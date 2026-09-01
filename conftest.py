import argparse


def valid_noise_rate(value):
    try:
        rate = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid noise rate: {value}. Must be a float between 0 and 0.05 .")
    if not (0 <= rate <= 0.05):
        raise argparse.ArgumentTypeError(f"Invalid noise rate: {value}. Must be between 0 and 0.05 .")
    return rate