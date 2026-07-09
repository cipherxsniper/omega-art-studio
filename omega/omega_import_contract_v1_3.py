"""
OMEGA IMPORT CONTRACT v1
Forces consistent environment initialization.
"""

from omega_env_bootstrap_v1 import bootstrap_env

ENV = bootstrap_env()

def get_env():
    return ENV
