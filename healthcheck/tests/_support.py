"""Shared test helpers."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HEALTHCHECK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG_DIR = os.path.join(HEALTHCHECK_DIR, "am_healthcheck")
FIXTURES_DIR = os.path.join(PKG_DIR, "fixtures")
DEMO_DIR = os.path.join(PKG_DIR, "demo")


def fixture(name):
    return os.path.join(FIXTURES_DIR, name)
