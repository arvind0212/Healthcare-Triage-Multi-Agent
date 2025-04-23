import json
import os
from pathlib import Path

def load_sample_patient_case() -> dict:
    """Load the sample patient case data."""
    file_path = Path(__file__).parent / "patient_case.json"
    with open(file_path, "r") as f:
        return json.load(f)

def load_sample_mdt_report() -> dict:
    """Load the sample MDT report template."""
    file_path = Path(__file__).parent / "mdt_report_template.json"
    with open(file_path, "r") as f:
        return json.load(f)

__all__ = ["load_sample_patient_case", "load_sample_mdt_report"] 