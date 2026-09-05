"""Shared test helpers."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HEALTHCHECK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fixture(name):
    return os.path.join(HEALTHCHECK_DIR, "fixtures", name)
