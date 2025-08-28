"""
Entry point for running network_discovery as a module.

This allows the package to be executed with: python -m network_discovery
"""

from .main import main

if __name__ == "__main__":
    exit(main())