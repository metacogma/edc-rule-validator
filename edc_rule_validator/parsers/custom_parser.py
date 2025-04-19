"""
Custom parser for the specific Excel file format provided.

This module parses the 'Edit checks' sheet from the Excel files
to extract rules and specifications, including dynamics and derivatives.
"""

import pandas as pd
from typing import Tuple, List, Dict, Any, Optional
import re
from datetime import datetime

from ..models.data_models import EditCheckRule, StudySpecification, Form, Field, FieldType, RuleSeverity
from ..utils.logger import Logger
from ..utils.dynamics import DynamicsProcessor

logger = Logger(__name__)

class CustomParser:
    """Parser for the specific Excel file format provided."""
    
    def __init__(self):
        """Initialize the parser."""
        self.errors = []
        self.dynamics_processor = DynamicsProcessor()
    
    def parse_rules(self, file_path: str) -> Tuple[List[EditCheckRule], List[Dict[str, Any]]]:
        """
        Parse rules from the Excel file.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Tuple of (rules, errors)
        """
        self.errors = []
        rules = []
        
        # Track dynamics and derivatives for later processing
        self.dynamics = []
        
        try:
            # Read the 'Edit checks' sheet with no header
            df = pd.read_excel(file_path, sheet_name='Edit checks', header=None)
            logger.info(f"Successfully read 'Edit checks' sheet with {len(df)} rows")
            
            # Find the header row (usually row 2 or 3)
            header_row = None
            for i in range(5):  # Check first 5 rows
                if isinstance(df.iloc[i, 1], str) and 'Check' in str(df.iloc[i, 1]):
                    header_row = i
                    break
            
            if header_row is None:
                logger.warning("Could not find header row, using row 2 as default")
                header_row = 2
                
            # Extract column names from the header row
            column_names = df.iloc[header_row].tolist()
            
            # Map column indices to meaningful names
            col_map = {}
            for i, name in enumerate(column_names):
                if name is not None and isinstance(name, str):
                    if 'Check Name' in name or 'Check ID' in name:
                        col_map['id'] = i
                    elif 'Description' in name or 'Edit Check Description' in name:
                        col_map['description'] = i
                    elif 'Discrepancy Text' in name or 'Message' in name:
                        col_map['message'] = i
                    elif 'Form Discrepancy' in name:
                        col_map['form'] = i
                    elif 'Field Discrepancy' in name:
                        col_map['field'] = i
                    elif 'Dependent Forms' in name:
                        col_map['dependent_forms'] = i
                    elif 'Dependent Fields' in name:
                        col_map['dependent_fields'] = i
            
            # Process each row after the header as a rule
            for idx in range(header_row + 1, len(df)):
                try:
                    row = df.iloc[idx]
                    
                    # Skip rows marked as REMOVE or empty
                    if pd.isna(row[1]) or (isinstance(row[0], str) and 'REMOVE' in row[0]):
                        continue
                    
                    # Extract rule information
                    rule_id = str(row[col_map.get('id', 1)]) if pd.notna(row[col_map.get('id', 1)]) else f"RULE_{idx}"
                    
                    # Extract description (column 5 typically has the rule description)
                    description = str(row[col_map.get('description', 5)]) if pd.notna(row[col_map.get('description', 5)]) else ""
                    
                    # The condition is typically in the description field
                    condition = description
                    
                    # Extract message
                    message = str(row[col_map.get('message', 6)]) if pd.notna(row[col_map.get('message', 6)]) else ""
                    
                    # Skip empty rules
                    if not condition or condition.lower() == 'nan' or pd.isna(condition):
                        continue
                    
                    # Create rule object
                    rule = EditCheckRule(
                        id=rule_id,
                        condition=condition,  # Use the condition field
                        message=message,
                        severity=RuleSeverity.ERROR  # Default severity
                    )
                    
                    # Store description in a custom attribute if needed
                    setattr(rule, 'description', description)
                    
                    # Extract dynamics and derivatives from the condition
                    rule_dynamics = self.dynamics_processor.extract_dynamics(condition)
                    if rule_dynamics:
                        self.dynamics.extend(rule_dynamics)
                        # Store dynamics in a custom attribute
                        setattr(rule, 'dynamics', rule_dynamics)
                    
                    # Extract form and field references
                    form_name = str(row[col_map.get('form', 2)]) if pd.notna(row[col_map.get('form', 2)]) else ""
                    field_name = str(row[col_map.get('field', 3)]) if pd.notna(row[col_map.get('field', 3)]) else ""
                    dependent_forms = str(row[col_map.get('dependent_forms', 7)]) if pd.notna(row[col_map.get('dependent_forms', 7)]) else ""
                    dependent_fields = str(row[col_map.get('dependent_fields', 8)]) if pd.notna(row[col_map.get('dependent_fields', 8)]) else ""
                    
                    # Add forms and fields to the rule
                    forms = [form for form in [form_name, dependent_forms] if form and form.lower() != 'nan']
                    fields = [field for field in [field_name, dependent_fields] if field and field.lower() != 'nan']
                    
                    if not forms:
                        # Try to extract forms from the condition
                        extracted_forms_fields = self._extract_forms_fields(condition)
                        extracted_forms = list(set([f for f, _ in extracted_forms_fields]))
                        extracted_fields = list(set([f for _, f in extracted_forms_fields]))
                        
                        forms.extend(extracted_forms)
                        fields.extend(extracted_fields)
                    
                    rule.forms = list(set(forms))
                    rule.fields = list(set(fields))
                    
                    # Only add rules with valid IDs
                    if rule_id and rule_id.lower() != 'nan' and not rule_id.startswith('RULE_'):
                        rules.append(rule)
                    
                except Exception as e:
                    self.errors.append({
                        'row': idx,
                        'message': f"Error parsing rule at row {idx}: {str(e)}",
                        'error_type': 'rule_parsing_error'
                    })
            
            logger.info(f"Parsed {len(rules)} rules with {len(self.errors)} errors")
            logger.info(f"Extracted {len(self.dynamics)} dynamic functions from rules")
            
        except Exception as e:
            self.errors.append({
                'message': f"Error reading Excel file: {str(e)}",
                'error_type': 'file_reading_error'
            })
            logger.error(f"Error reading Excel file: {str(e)}")
        
        return rules, self.errors
    
    def parse_specification(self, file_path: str) -> Tuple[StudySpecification, List[Dict[str, Any]]]:
        """
        Parse study specification from the Excel file.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Tuple of (specification, errors)
        """
        self.errors = []
        spec = StudySpecification()
        
        try:
            # Read all sheets to extract form and field information
            xl = pd.ExcelFile(file_path)
            
            # Create a default form for each sheet
            for sheet_name in xl.sheet_names:
                form = Form(
                    name=sheet_name,
                    label=sheet_name
                )
                
                # Read the sheet
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Extract column headers as fields
                for col in df.columns:
                    field = Field(
                        name=col,
                        type=self._infer_field_type(df[col]),
                        label=col,
                        required=False
                    )
                    form.fields.append(field)
                
                spec.add_form(form)
            
            logger.info(f"Created specification with {len(spec.forms)} forms")
            
            # Create additional forms for common EDC structures
            self._add_common_edc_forms(spec)
            
            # Add dynamics and derivatives form if we have extracted dynamics
            if hasattr(self, 'dynamics') and self.dynamics:
                self._add_dynamics_form(spec)
            
        except Exception as e:
            self.errors.append({
                'message': f"Error reading Excel file: {str(e)}",
                'error_type': 'file_reading_error'
            })
            logger.error(f"Error reading Excel file: {str(e)}")
        
        return spec, self.errors
    
    def _extract_forms_fields(self, condition: str) -> List[Tuple[str, str]]:
        """
        Extract form and field references from a condition string.
        
        Args:
            condition: The rule condition string
            
        Returns:
            List of (form, field) tuples
        """
        # Pattern to match form.field references
        pattern = r'([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)'
        matches = re.findall(pattern, condition)
        
        # If no explicit form.field references, look for field names
        if not matches:
            # Assume fields without form references are in a default form
            field_pattern = r'\b([A-Za-z][A-Za-z0-9_]*)\b'
            field_matches = re.findall(field_pattern, condition)
            
            # Filter out common operators and keywords
            keywords = {'AND', 'OR', 'NOT', 'NULL', 'IN', 'BETWEEN', 'IS', 'TRUE', 'FALSE'}
            fields = [f for f in field_matches if f not in keywords]
            
            # Assign to default form
            matches = [('DefaultForm', field) for field in fields]
        
        return matches
    
    def _infer_field_type(self, series: pd.Series) -> FieldType:
        """
        Infer the field type from a pandas Series.
        
        Args:
            series: The pandas Series to analyze
            
        Returns:
            Inferred FieldType
        """
        # Drop NaN values for type inference
        non_null = series.dropna()
        
        if len(non_null) == 0:
            return FieldType.TEXT
        
        # Check if all values are boolean
        if non_null.dtype == bool or set(non_null.astype(str).str.lower()).issubset({'true', 'false', 'yes', 'no', 'y', 'n', '1', '0'}):
            return FieldType.BOOLEAN
        
        # Check if all values are numeric
        if pd.api.types.is_numeric_dtype(non_null):
            return FieldType.NUMBER
        
        # Check if all values are dates
        try:
            pd.to_datetime(non_null)
            # Check if time components are present
            if any(pd.to_datetime(non_null).dt.time != pd.Timestamp('00:00:00').time()):
                return FieldType.DATETIME
            return FieldType.DATE
        except:
            pass
        
        # Check if values are categorical (limited unique values)
        if len(non_null.unique()) < min(10, len(non_null) / 2):
            return FieldType.CATEGORICAL
        
        # Default to text
        return FieldType.TEXT
    
    def _add_common_edc_forms(self, spec: StudySpecification) -> None:
        """
        Add common EDC forms and fields to the specification.
        
        Args:
            spec: The specification to augment
        """
        # Add Demographics form
        demographics = Form(
            name="Demographics",
            label="Demographics"
        )
        demographics.fields.extend([
            Field(name="SubjectID", type=FieldType.TEXT, label="Subject ID", required=True),
            Field(name="DateOfBirth", type=FieldType.DATE, label="Date of Birth"),
            Field(name="Gender", type=FieldType.CATEGORICAL, label="Gender", valid_values=["Male", "Female", "Other"]),
            Field(name="Race", type=FieldType.CATEGORICAL, label="Race"),
            Field(name="Ethnicity", type=FieldType.CATEGORICAL, label="Ethnicity")
        ])
        spec.add_form(demographics)
        
        # Add Vitals form
        vitals = Form(
            name="Vitals",
            label="Vital Signs"
        )
        vitals.fields.extend([
            Field(name="Height", type=FieldType.NUMBER, label="Height (cm)"),
            Field(name="Weight", type=FieldType.NUMBER, label="Weight (kg)"),
            Field(name="BMI", type=FieldType.NUMBER, label="BMI"),
            Field(name="Temperature", type=FieldType.NUMBER, label="Temperature (°C)"),
            Field(name="SystolicBP", type=FieldType.NUMBER, label="Systolic Blood Pressure"),
            Field(name="DiastolicBP", type=FieldType.NUMBER, label="Diastolic Blood Pressure"),
            Field(name="HeartRate", type=FieldType.NUMBER, label="Heart Rate (bpm)"),
            Field(name="RespiratoryRate", type=FieldType.NUMBER, label="Respiratory Rate")
        ])
        spec.add_form(vitals)
        
        # Add Labs form
        labs = Form(
            name="Labs",
            label="Laboratory Tests"
        )
        labs.fields.extend([
            Field(name="WBC", type=FieldType.NUMBER, label="White Blood Cell Count"),
            Field(name="RBC", type=FieldType.NUMBER, label="Red Blood Cell Count"),
            Field(name="Hemoglobin", type=FieldType.NUMBER, label="Hemoglobin"),
            Field(name="Hematocrit", type=FieldType.NUMBER, label="Hematocrit"),
            Field(name="Platelets", type=FieldType.NUMBER, label="Platelets"),
            Field(name="Glucose", type=FieldType.NUMBER, label="Glucose"),
            Field(name="Creatinine", type=FieldType.NUMBER, label="Creatinine"),
            Field(name="ALT", type=FieldType.NUMBER, label="ALT"),
            Field(name="AST", type=FieldType.NUMBER, label="AST")
        ])
        spec.add_form(labs)
        
        # Add Visit form
        visit = Form(
            name="Visit",
            label="Visit Information"
        )
        visit.fields.extend([
            Field(name="VisitDate", type=FieldType.DATE, label="Visit Date", required=True),
            Field(name="VisitNumber", type=FieldType.NUMBER, label="Visit Number", required=True),
            Field(name="VisitType", type=FieldType.CATEGORICAL, label="Visit Type"),
            Field(name="VisitStatus", type=FieldType.CATEGORICAL, label="Visit Status", 
                  valid_values=["Scheduled", "Completed", "Missed", "Early Termination"])
        ])
        spec.add_form(visit)
        
    def _add_dynamics_form(self, spec: StudySpecification) -> None:
        """
        Add dynamics and derivatives form to the specification.
        
        Args:
            spec: The specification to augment
        """
        # Create Derivatives form
        derivatives = Form(
            name="Derivatives",
            label="Derived Variables and Dynamics"
        )
        
        # Add standard derived fields
        derivatives.fields.extend([
            Field(name="BMI", type=FieldType.NUMBER, label="Body Mass Index"),
            Field(name="BSA", type=FieldType.NUMBER, label="Body Surface Area"),
            Field(name="eGFR", type=FieldType.NUMBER, label="Estimated Glomerular Filtration Rate")
        ])
        
        # Add fields for each dynamic function found in rules
        for dynamic in self.dynamics:
            field_name = dynamic['original'].replace('(', '_').replace(')', '').replace(',', '_').replace(' ', '')
            
            # Check if field already exists
            if not any(field.name == field_name for field in derivatives.fields):
                field_type = self.dynamics_processor._infer_dynamic_type(dynamic['function'])
                
                field = Field(
                    name=field_name,
                    type=field_type,
                    label=dynamic['original'],
                    required=False
                )
                
                derivatives.fields.append(field)
        
        spec.add_form(derivatives)
