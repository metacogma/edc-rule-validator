"""
Data models for the Edit Check Rule Validation System.

This module defines the core data structures used throughout the system,
including StudySpecification and EditCheckRule.
"""

import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum


class RuleSeverity(str, Enum):
    """Severity levels for edit check rules."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class FieldType(str, Enum):
    """Field types for study specification fields."""
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    DATETIME = "datetime"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    TIME = "time"
    FILE = "file"
    
    @classmethod
    def from_string(cls, value: str) -> 'FieldType':
        """Convert string to FieldType enum."""
        value_lower = value.lower()
        mapping = {
            "string": cls.TEXT,
            "text": cls.TEXT,
            "character": cls.TEXT,
            "varchar": cls.TEXT,
            
            "number": cls.NUMBER,
            "numeric": cls.NUMBER,
            "integer": cls.NUMBER,
            "float": cls.NUMBER,
            "double": cls.NUMBER,
            "decimal": cls.NUMBER,
            
            "date": cls.DATE,
            
            "datetime": cls.DATETIME,
            "timestamp": cls.DATETIME,
            
            "categorical": cls.CATEGORICAL,
            "category": cls.CATEGORICAL,
            "enum": cls.CATEGORICAL,
            "enumeration": cls.CATEGORICAL,
            "codelist": cls.CATEGORICAL,
            
            "boolean": cls.BOOLEAN,
            "bool": cls.BOOLEAN,
            "logical": cls.BOOLEAN,
            "yes/no": cls.BOOLEAN,
            
            "time": cls.TIME,
            
            "file": cls.FILE,
            "attachment": cls.FILE,
            "binary": cls.FILE
        }
        
        return mapping.get(value_lower, cls.TEXT)


@dataclass
class Field:
    """Field in a study form."""
    name: str
    type: FieldType
    label: Optional[str] = None
    required: bool = False
    valid_values: Optional[List[str]] = None
    min_value: Optional[Union[float, datetime]] = None
    max_value: Optional[Union[float, datetime]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Field':
        """Create a Field from a dictionary."""
        field_type = FieldType.from_string(data.get('type', 'text'))
        
        return cls(
            name=data.get('name'),
            type=field_type,
            label=data.get('label'),
            required=data.get('required', False),
            valid_values=data.get('valid_values'),
            min_value=data.get('min_value'),
            max_value=data.get('max_value')
        )


@dataclass
class Form:
    """Form in a study specification."""
    name: str
    label: Optional[str] = None
    fields: List[Field] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Form':
        """Create a Form from a dictionary."""
        form = cls(
            name=data.get('name'),
            label=data.get('label')
        )
        
        fields_data = data.get('fields', [])
        for field_data in fields_data:
            form.fields.append(Field.from_dict(field_data))
            
        return form


@dataclass
class StudySpecification:
    """Study specification data model."""
    forms: Dict[str, Form] = field(default_factory=dict)
    
    def add_form(self, form: Form) -> None:
        """Add a form to the specification."""
        self.forms[form.name] = form
    
    def get_field(self, form_name: str, field_name: str) -> Optional[Field]:
        """Get a field by form name and field name."""
        form = self.forms.get(form_name)
        if not form:
            return None
            
        for field in form.fields:
            if field.name == field_name:
                return field
                
        return None
    
    @classmethod
    def from_dataframes(cls, forms_df, fields_df) -> 'StudySpecification':
        """Create a StudySpecification from forms and fields dataframes."""
        spec = cls()
        
        # Process forms
        if not forms_df.empty:
            for _, row in forms_df.iterrows():
                form_name = row.get('form_name')
                form_label = row.get('form_label')
                
                if form_name:
                    form = Form(name=form_name, label=form_label)
                    spec.add_form(form)
        
        # Create forms that are in fields but not in forms
        if not fields_df.empty:
            unique_forms = fields_df['form_name'].unique()
            for form_name in unique_forms:
                if form_name and form_name not in spec.forms:
                    form = Form(name=form_name)
                    spec.add_form(form)
        
        # Process fields
        if not fields_df.empty:
            for _, row in fields_df.iterrows():
                form_name = row.get('form_name')
                field_name = row.get('field_name')
                field_type = row.get('field_type')
                
                if form_name and field_name and field_type:
                    if form_name in spec.forms:
                        field_data = {
                            'name': field_name,
                            'type': field_type
                        }
                        
                        # Add optional fields if present
                        for col, attr in [
                            ('field_label', 'label'),
                            ('required', 'required'),
                            ('valid_values', 'valid_values'),
                            ('min_value', 'min_value'),
                            ('max_value', 'max_value')
                        ]:
                            if col in fields_df.columns and not pd.isna(row.get(col)):
                                field_data[attr] = row.get(col)
                        
                        field = Field.from_dict(field_data)
                        spec.forms[form_name].fields.append(field)
        
        return spec


@dataclass
class EditCheckRule:
    """Edit check rule data model."""
    id: str
    condition: str
    message: Optional[str] = None
    severity: RuleSeverity = RuleSeverity.ERROR
    forms: List[str] = field(default_factory=list)
    fields: List[str] = field(default_factory=list)
    formalized_condition: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EditCheckRule':
        """Create an EditCheckRule from a dictionary."""
        # Handle severity conversion
        severity_value = data.get('severity', RuleSeverity.ERROR)
        if isinstance(severity_value, str):
            try:
                severity = RuleSeverity(severity_value.lower())
            except ValueError:
                severity = RuleSeverity.ERROR
        else:
            severity = RuleSeverity.ERROR
            
        return cls(
            id=data.get('id'),
            condition=data.get('condition'),
            message=data.get('message'),
            severity=severity,
            forms=data.get('forms', []),
            fields=data.get('fields', []),
            formalized_condition=data.get('formalized_condition')
        )


@dataclass
class ValidationResult:
    """Result of a rule validation."""
    rule_id: str
    is_valid: bool
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_error(self, error_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Add an error to the validation result."""
        error = {
            'error_type': error_type,
            'message': message
        }
        
        if details:
            error.update(details)
            
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Add a warning to the validation result."""
        warning = {
            'warning_type': warning_type,
            'message': message
        }
        
        if details:
            warning.update(details)
            
        self.warnings.append(warning)


@dataclass
class TestCase:
    """Test case for a rule."""
    rule_id: str
    description: str
    expected_result: bool
    test_data: Dict[str, Any]
    is_positive: bool = True
    technique: str = "unknown"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestCase':
        """Create a TestCase from a dictionary."""
        return cls(
            rule_id=data.get('rule_id'),
            description=data.get('description', ''),
            expected_result=data.get('expected_result', True),
            test_data=data.get('test_data', {}),
            is_positive=data.get('is_positive', True),
            technique=data.get('technique', 'unknown')
        )
