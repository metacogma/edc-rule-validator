"""
Specification Parser for the Edit Check Rule Validation System.

This module provides functionality to parse study specifications from Excel files.
"""

import pandas as pd
from typing import Dict, Any, List
from ..models.data_models import StudySpecification, Form, Field, FieldType
from ..utils.logger import Logger

logger = Logger(__name__)

class SpecificationParser:
    """Parse study specifications from Excel files."""
    
    def parse(self, file_path: str) -> StudySpecification:
        """
        Parse a study specification from an Excel file.
        
        Args:
            file_path: Path to the Excel file containing the specification
            
        Returns:
            Parsed study specification
        """
        logger.info(f"Parsing specification from Excel file: {file_path}")
        
        try:
            # Read Excel file - assume it has multiple sheets for forms
            excel_file = pd.ExcelFile(file_path)
            
            # Parse forms
            forms = {}
            for sheet_name in excel_file.sheet_names:
                # Skip any non-form sheets (like metadata, instructions, etc.)
                if sheet_name.startswith('_') or sheet_name.lower() in ['metadata', 'instructions', 'readme']:
                    continue
                
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                form = self._parse_form(sheet_name, df)
                forms[form.name] = form
            
            # Create specification
            specification = StudySpecification(forms=forms)
            
            logger.info(f"Successfully parsed specification with {len(forms)} forms")
            return specification
            
        except Exception as e:
            logger.error(f"Error parsing specification from Excel file: {str(e)}")
            raise
    
    def _parse_form(self, form_name: str, df: pd.DataFrame) -> Form:
        """
        Parse a single form from an Excel sheet.
        
        Args:
            form_name: Name of the form (sheet name)
            df: DataFrame containing form data
            
        Returns:
            Parsed form
        """
        # Parse fields
        fields = []
        for _, row in df.iterrows():
            field = self._parse_field(row)
            if field:
                fields.append(field)
        
        # Create form
        form = Form(
            name=form_name,
            label=form_name,  # Use form name as label if not provided
            fields=fields
        )
        
        return form
    
    def _parse_field(self, row: pd.Series) -> Field:
        """
        Parse a single field from an Excel row.
        
        Args:
            row: DataFrame row containing field data
            
        Returns:
            Parsed field or None if row is invalid
        """
        try:
            # Extract required fields
            field_name = str(row.get('FieldName', ''))
            
            # Skip empty rows
            if not field_name:
                return None
            
            # Extract field type
            field_type_str = str(row.get('Type', 'TEXT')).upper()
            try:
                field_type = FieldType(field_type_str)
            except ValueError:
                logger.warning(f"Unknown field type: {field_type_str}, defaulting to TEXT")
                field_type = FieldType.TEXT
            
            # Create field
            field = Field(
                name=field_name,
                label=str(row.get('Label', field_name)),  # Use field name as label if not provided
                type=field_type
            )
            
            # Add optional attributes if present in the Excel
            if 'Required' in row and pd.notna(row['Required']):
                required = row['Required']
                if isinstance(required, str):
                    required = required.lower() in ['yes', 'true', '1', 'y']
                setattr(field, 'required', bool(required))
            
            if 'ValidValues' in row and pd.notna(row['ValidValues']):
                valid_values = str(row['ValidValues']).split(',')
                valid_values = [value.strip() for value in valid_values]
                setattr(field, 'valid_values', valid_values)
            
            if 'MinValue' in row and pd.notna(row['MinValue']):
                setattr(field, 'min_value', float(row['MinValue']))
            
            if 'MaxValue' in row and pd.notna(row['MaxValue']):
                setattr(field, 'max_value', float(row['MaxValue']))
            
            return field
            
        except Exception as e:
            logger.error(f"Error parsing field row: {str(e)}")
            return None
