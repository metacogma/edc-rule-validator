"""
JSON Specification Parser for the Edit Check Rule Validation System.

This module provides functionality to parse study specifications from JSON files.
"""

import json
from typing import Dict, Any, List
from ..models.data_models import StudySpecification, Form, Field, FieldType
from ..utils.logger import Logger

logger = Logger(__name__)

class JSONSpecificationParser:
    """Parse study specifications from JSON files."""
    
    def parse(self, file_path: str) -> StudySpecification:
        """
        Parse a study specification from a JSON file.
        
        Args:
            file_path: Path to the JSON file containing the specification
            
        Returns:
            Parsed study specification
        """
        logger.info(f"Parsing specification from JSON file: {file_path}")
        
        try:
            # Read JSON file
            with open(file_path, 'r') as f:
                spec_data = json.load(f)
            
            # Parse forms
            forms = {}
            for form_name, form_data in spec_data.get('forms', {}).items():
                form = self._parse_form(form_data)
                forms[form_name] = form
            
            # Create specification
            specification = StudySpecification(forms=forms)
            
            logger.info(f"Successfully parsed specification with {len(forms)} forms")
            return specification
            
        except Exception as e:
            logger.error(f"Error parsing specification from JSON file: {str(e)}")
            raise
    
    def _parse_form(self, form_data: Dict[str, Any]) -> Form:
        """
        Parse a single form from JSON data.
        
        Args:
            form_data: Dictionary containing form data
            
        Returns:
            Parsed form
        """
        # Parse fields
        fields = []
        for field_data in form_data.get('fields', []):
            field = self._parse_field(field_data)
            fields.append(field)
        
        # Create form
        form = Form(
            name=form_data.get('name', ''),
            label=form_data.get('label', ''),
            fields=fields
        )
        
        return form
    
    def _parse_field(self, field_data: Dict[str, Any]) -> Field:
        """
        Parse a single field from JSON data.
        
        Args:
            field_data: Dictionary containing field data
            
        Returns:
            Parsed field
        """
        # Parse field type
        field_type_str = field_data.get('type', 'TEXT')
        try:
            field_type = FieldType(field_type_str)
        except ValueError:
            logger.warning(f"Unknown field type: {field_type_str}, defaulting to TEXT")
            field_type = FieldType.TEXT
        
        # Create field
        field = Field(
            name=field_data.get('name', ''),
            label=field_data.get('label', ''),
            type=field_type
        )
        
        # Add optional attributes
        if 'required' in field_data:
            setattr(field, 'required', field_data['required'])
        
        if 'valid_values' in field_data:
            setattr(field, 'valid_values', field_data['valid_values'])
        
        if 'min_value' in field_data:
            setattr(field, 'min_value', field_data['min_value'])
        
        if 'max_value' in field_data:
            setattr(field, 'max_value', field_data['max_value'])
        
        return field
