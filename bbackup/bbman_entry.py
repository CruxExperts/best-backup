"""
Entry point wrapper for bbman CLI.
This allows bbman to be registered as a console script in setup.py.
"""

# Import and re-export the cli function
from .bbman import cli

if __name__ == "__main__":
    cli()
