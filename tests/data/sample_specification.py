"""
Sample study specification data for testing.

This module provides functions to generate sample study specification data
that can be used for testing the parser and validator components.
"""

import pandas as pd
import os
from typing import Tuple


def create_sample_specification_excel(output_path: str) -> str:
    """
    Create a sample study specification Excel file for testing.
    
    Args:
        output_path: Directory to save the Excel file
        
    Returns:
        Path to the created Excel file
    """
    # Create forms data
    forms_data = {
        'form_name': ['Demographics', 'MedicalHistory', 'VitalSigns', 'LabResults'],
        'form_label': ['Patient Demographics', 'Medical History', 'Vital Signs', 'Laboratory Results']
    }
    forms_df = pd.DataFrame(forms_data)
    
    # Create fields data
    fields_data = {
        'form_name': [
            'Demographics', 'Demographics', 'Demographics', 'Demographics',
            'MedicalHistory', 'MedicalHistory', 'MedicalHistory',
            'VitalSigns', 'VitalSigns', 'VitalSigns', 'VitalSigns',
            'LabResults', 'LabResults', 'LabResults'
        ],
        'field_name': [
            'subject_id', 'age', 'gender', 'ethnicity',
            'condition', 'diagnosis_date', 'ongoing',
            'height', 'weight', 'blood_pressure', 'temperature',
            'hemoglobin', 'white_blood_cells', 'platelets'
        ],
        'field_type': [
            'text', 'number', 'categorical', 'categorical',
            'text', 'date', 'boolean',
            'number', 'number', 'text', 'number',
            'number', 'number', 'number'
        ],
        'field_label': [
            'Subject ID', 'Age (years)', 'Gender', 'Ethnicity',
            'Medical Condition', 'Date of Diagnosis', 'Ongoing?',
            'Height (cm)', 'Weight (kg)', 'Blood Pressure (mmHg)', 'Temperature (°C)',
            'Hemoglobin (g/dL)', 'White Blood Cells (10^9/L)', 'Platelets (10^9/L)'
        ],
        'required': [
            True, True, True, False,
            True, True, True,
            True, True, True, True,
            True, True, True
        ],
        'valid_values': [
            None, '18-100', 'Male,Female,Other', 'Hispanic,Non-Hispanic',
            None, None, 'Yes,No',
            '100-250', '30-200', None, '35-42',
            '8-18', '4-11', '150-450'
        ]
    }
    fields_df = pd.DataFrame(fields_data)
    
    # Create Excel file
    os.makedirs(output_path, exist_ok=True)
    file_path = os.path.join(output_path, 'sample_specification.xlsx')
    
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        forms_df.to_excel(writer, sheet_name='Forms', index=False)
        fields_df.to_excel(writer, sheet_name='Fields', index=False)
    
    return file_path


def create_sample_rules_excel(output_path: str) -> str:
    """
    Create a sample rules Excel file for testing.
    
    Args:
        output_path: Directory to save the Excel file
        
    Returns:
        Path to the created Excel file
    """
    # Create rules data
    rules_data = {
        'check_id': [
            'R001', 'R002', 'R003', 'R004', 'R005',
            'R006', 'R007', 'R008', 'R009', 'R010'
        ],
        'condition': [
            'Demographics.age >= 18 AND Demographics.age <= 65',
            'IF Demographics.gender = "Female" THEN MedicalHistory.pregnancy_test MUST BE COMPLETED',
            'VitalSigns.systolic_bp < 140 AND VitalSigns.diastolic_bp < 90',
            'IF MedicalHistory.diabetes = "Yes" THEN LabResults.glucose MUST BE COMPLETED',
            'LabResults.hemoglobin >= 10',
            'VitalSigns.weight / ((VitalSigns.height/100)^2) <= 35',
            'IF MedicalHistory.ongoing = "Yes" THEN MedicalHistory.end_date MUST BE BLANK',
            'Demographics.ethnicity IN ("Hispanic", "Non-Hispanic", "Unknown")',
            'LabResults.collection_date <= CURRENT_DATE',
            'IF VitalSigns.temperature > 38 THEN VitalSigns.fever MUST BE "Yes"'
        ],
        'message': [
            'Subject must be between 18 and 65 years of age',
            'Pregnancy test is required for female subjects',
            'Blood pressure must be within normal range',
            'Glucose test is required for diabetic subjects',
            'Hemoglobin must be at least 10 g/dL',
            'BMI must not exceed 35',
            'End date must be blank for ongoing conditions',
            'Ethnicity must be one of the allowed values',
            'Lab collection date cannot be in the future',
            'Fever should be marked as Yes if temperature exceeds 38°C'
        ],
        'severity': [
            'error', 'error', 'warning', 'error', 'warning',
            'warning', 'error', 'error', 'error', 'warning'
        ],
        'forms': [
            'Demographics', 'Demographics,MedicalHistory', 'VitalSigns', 'MedicalHistory,LabResults', 'LabResults',
            'VitalSigns', 'MedicalHistory', 'Demographics', 'LabResults', 'VitalSigns'
        ],
        'fields': [
            'age', 'gender,pregnancy_test', 'systolic_bp,diastolic_bp', 'diabetes,glucose', 'hemoglobin',
            'weight,height', 'ongoing,end_date', 'ethnicity', 'collection_date', 'temperature,fever'
        ]
    }
    rules_df = pd.DataFrame(rules_data)
    
    # Create Excel file
    os.makedirs(output_path, exist_ok=True)
    file_path = os.path.join(output_path, 'sample_rules.xlsx')
    
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        rules_df.to_excel(writer, sheet_name='Rules', index=False)
    
    return file_path


def generate_sample_files() -> Tuple[str, str]:
    """
    Generate both sample specification and rules files.
    
    Returns:
        Tuple containing paths to the specification and rules files
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    
    spec_path = create_sample_specification_excel(data_dir)
    rules_path = create_sample_rules_excel(data_dir)
    
    return spec_path, rules_path


if __name__ == "__main__":
    spec_path, rules_path = generate_sample_files()
    print(f"Generated sample specification file: {spec_path}")
    print(f"Generated sample rules file: {rules_path}")
