"""Demo script for DT-CAN LLM tool interface.

This script demonstrates how to use the DTCANTool for inference.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm_tools import DTCANTool
from src.llm_tools.csv_loader import load_patient_from_csv, get_patient_ids


"""
> target prompt:

Please check the whether the patient with patient_ids 4 in cohort `Dataset/private_fundus` has diabetes, and what would the probability be?
"""

def example():
    cohort_dir = "Dataset/private_fundus"
    checkpoint_path = "checkpoints/deepdr_ehr_text/best.pt"
    config_path = "src/configs/deepdr_ehr_text.yaml"

    # Get sample patient IDs
    try:
        patient_ids = get_patient_ids(cohort_dir, limit=3)
        print(f"\nLoaded {len(patient_ids)} sample patients: {patient_ids[:3]}")
    except Exception as e:
        print(f"\nError loading patient IDs: {e}")
        return

    tool = DTCANTool()

    # Process each patient
    for patient_id in patient_ids[:2]:  # Process first 2 patients
        print(f"\n--- Patient {patient_id} ---")

        # Load patient data from CSV
        patient_data = load_patient_from_csv(cohort_dir, patient_id)
        print(f"Loaded modalities: {list(patient_data.keys())}")

        # Run inference with raw data encoding
        result = tool.predict(
            checkpoint_path=checkpoint_path,
            data=patient_data,
            config={
                "config_path": config_path,
                "encode_raw": True,
                "output_format": "probabilities",
            },
        )

        print("Predictions:")
        for disease, prob in result["predictions"]["system"].items():
            print(f"  {disease}: {prob:.3f}")



if __name__ == "__main__":
    print("DT-CAN LLM Tool Demo")
    print("=" * 60)
    
    example()