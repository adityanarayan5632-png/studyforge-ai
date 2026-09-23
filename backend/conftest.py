"""Pytest configuration to set BASE URL before test modules are imported."""
import os

# Set BASE URL before test modules are imported
os.environ["BASE"] = "http://127.0.0.1:8080"
os.environ["API_BASE"] = "http://127.0.0.1:8080"