"""The configuration file for pytest."""
import sys
import os

# Apply path fix
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
