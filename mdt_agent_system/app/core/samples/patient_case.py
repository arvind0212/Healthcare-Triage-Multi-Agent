import json
import os
from pathlib import Path

def get_sample_case():
    """
    Loads the sample patient case from the JSON file.
    Returns the patient case as a dictionary.
    """
    # Get the directory where this file is located
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    
    # Path to the sample patient case JSON file
    sample_case_path = current_dir / "patient_case.json"
    
    # Check if the file exists
    if not os.path.exists(sample_case_path):
        raise FileNotFoundError(f"Sample patient case file not found at {sample_case_path}")
    
    # Load the JSON file
    with open(sample_case_path, "r") as f:
        patient_case = json.load(f)
    
    return patient_case 