"""
Enhanced Rule Validator for the Edit Check Rule Validation System.

This module provides advanced functionality to validate edit check rules against
study specifications, ensuring logical consistency, completeness, and clinical validity.
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple

from ..models.data_models import EditCheckRule, StudySpecification, ValidationResult, FieldType
from ..utils.logger import Logger

logger = Logger(__name__)

class EnhancedRuleValidator:
    """Enhanced rule validator with clinical domain knowledge and semantic analysis."""
    
    def __init__(self):
        """Initialize with domain-specific validation capabilities."""
        # Advanced pattern matchers
        self.form_field_pattern = re.compile(r'([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)')
        self.conditional_pattern = re.compile(r'IF\s+(.+?)\s+THEN\s+(.+)(?:\s+ELSE\s+(.+))?', re.IGNORECASE)
        self.comparison_pattern = re.compile(r'([A-Za-z0-9_]+)\s*(<=|>=|!=|=|<|>|IN|NOT IN|BETWEEN)\s*([A-Za-z0-9_.\'\"]+(?:\s*,\s*[A-Za-z0-9_.\'\"]+)*)')
        
        # Clinical domain knowledge
        self.clinical_ranges = {
            'SystolicBP': {'min': 60, 'max': 250, 'unit': 'mmHg'},
            'DiastolicBP': {'min': 30, 'max': 150, 'unit': 'mmHg'},
            'HeartRate': {'min': 40, 'max': 200, 'unit': 'bpm'},
            'Temperature': {'min': 35, 'max': 42, 'unit': '°C'},
            'RespiratoryRate': {'min': 8, 'max': 30, 'unit': 'breaths/min'},
            'Height': {'min': 30, 'max': 250, 'unit': 'cm'},
            'Weight': {'min': 2, 'max': 300, 'unit': 'kg'}
        }
    
    def validate_rule(self, rule: EditCheckRule, specification: StudySpecification) -> ValidationResult:
        """Validate a rule with enhanced clinical domain checks."""
        result = ValidationResult(rule_id=rule.id, is_valid=True)
        
        # Basic validation
        if not rule.condition:
            result.add_error(
                'missing_condition',
                f"Rule {rule.id} is missing a condition"
            )
            return result
        
        # Extract and validate forms and fields
        forms_fields = self._extract_forms_fields(rule.condition)
        self._validate_forms_fields(forms_fields, specification, result)
        
        # Check for contradictory conditions
        contradictions = self._check_contradictory_conditions(rule.condition)
        for error_type, message, details in contradictions:
            result.add_error(error_type, message, details)
        
        # Check for unrealistic clinical values
        unrealistic_values = self._check_unrealistic_values(rule.condition)
        for error_type, message, details in unrealistic_values:
            result.add_error(error_type, message, details)
        
        # Check for type mismatches
        type_mismatches = self._check_type_mismatches(rule.condition, specification)
        for error_type, message, details in type_mismatches:
            result.add_error(error_type, message, details)
        
        # Check for non-existent fields
        nonexistent_fields = self._check_nonexistent_fields(forms_fields, specification)
        for error_type, message, details in nonexistent_fields:
            result.add_error(error_type, message, details)
        
        # Check for clinical inconsistencies
        clinical_inconsistencies = self._check_clinical_inconsistencies(rule.condition)
        for error_type, message, details in clinical_inconsistencies:
            result.add_error(error_type, message, details)
        
        return result
    
    def _extract_forms_fields(self, condition: str) -> List[Dict[str, Any]]:
        """Extract forms and fields from a rule condition."""
        result = []
        
        # Extract explicit form.field references
        form_field_matches = self.form_field_pattern.findall(condition)
        for form_name, field_name in form_field_matches:
            result.append({
                'form': form_name,
                'field': field_name,
                'reference_type': 'explicit'
            })
        
        # Extract field names without form references
        words = re.findall(r'\b([A-Za-z][A-Za-z0-9_]*)\b', condition)
        keywords = {'AND', 'OR', 'NOT', 'IF', 'THEN', 'ELSE', 'NULL', 'IN', 'BETWEEN', 'IS', 'TRUE', 'FALSE'}
        
        for word in words:
            if word not in keywords and not any(item['field'] == word for item in result):
                # This could be an implicit field reference
                result.append({
                    'form': None,
                    'field': word,
                    'reference_type': 'implicit'
                })
        
        return result
    
    def _validate_forms_fields(self, forms_fields: List[Dict[str, Any]], specification: StudySpecification, result: ValidationResult) -> None:
        """Validate forms and fields against specification."""
        for item in forms_fields:
            form_name = item['form']
            field_name = item['field']
            
            # Skip implicit references without form names
            if form_name is None:
                continue
            
            # Check if form exists
            if form_name not in specification.forms:
                result.add_error(
                    'invalid_form',
                    f"Form '{form_name}' referenced in rule does not exist in the specification",
                    {'form': form_name}
                )
                continue
            
            # Check if field exists in form
            form = specification.forms[form_name]
            field_exists = False
            
            for field in form.fields:
                if field.name == field_name:
                    field_exists = True
                    break
            
            if not field_exists:
                result.add_error(
                    'invalid_field',
                    f"Field '{field_name}' in form '{form_name}' does not exist in the specification",
                    {'form': form_name, 'field': field_name}
                )
    
    def _check_contradictory_conditions(self, condition: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        """Check for contradictory conditions in a rule."""
        errors = []
        
        # Check for contradictions in AND expressions
        if ' AND ' in condition:
            # Extract all field comparisons
            comparisons = {}
            for match in self.comparison_pattern.finditer(condition):
                field, op, value = match.groups()
                if field not in comparisons:
                    comparisons[field] = []
                comparisons[field].append((op, value))
            
            # Check for contradictions in each field's comparisons
            for field, field_comparisons in comparisons.items():
                if len(field_comparisons) > 1:
                    # Check for direct contradictions
                    for i, (op1, val1) in enumerate(field_comparisons):
                        for op2, val2 in field_comparisons[i+1:]:
                            try:
                                # Try to convert values to float for numeric comparison
                                float_val1 = float(val1)
                                float_val2 = float(val2)
                                
                                # Check for contradictions
                                if op1 == '>' and op2 == '<':
                                    if float_val1 >= float_val2:
                                        errors.append((
                                            'contradictory_conditions',
                                            f"Contradictory conditions: {field} {op1} {val1} AND {field} {op2} {val2}",
                                            {'field': field, 'condition1': f"{field} {op1} {val1}", 'condition2': f"{field} {op2} {val2}"}
                                        ))
                                elif op1 == '<' and op2 == '>':
                                    if float_val1 <= float_val2:
                                        errors.append((
                                            'contradictory_conditions',
                                            f"Contradictory conditions: {field} {op1} {val1} AND {field} {op2} {val2}",
                                            {'field': field, 'condition1': f"{field} {op1} {val1}", 'condition2': f"{field} {op2} {val2}"}
                                        ))
                                elif op1 == '>=' and op2 == '<=':
                                    if float_val1 > float_val2:
                                        errors.append((
                                            'contradictory_conditions',
                                            f"Contradictory conditions: {field} {op1} {val1} AND {field} {op2} {val2}",
                                            {'field': field, 'condition1': f"{field} {op1} {val1}", 'condition2': f"{field} {op2} {val2}"}
                                        ))
                                elif op1 == '<=' and op2 == '>=':
                                    if float_val1 < float_val2:
                                        errors.append((
                                            'contradictory_conditions',
                                            f"Contradictory conditions: {field} {op1} {val1} AND {field} {op2} {val2}",
                                            {'field': field, 'condition1': f"{field} {op1} {val1}", 'condition2': f"{field} {op2} {val2}"}
                                        ))
                                elif op1 == '=' and op2 == '=':
                                    if float_val1 != float_val2:
                                        errors.append((
                                            'contradictory_conditions',
                                            f"Contradictory conditions: {field} {op1} {val1} AND {field} {op2} {val2}",
                                            {'field': field, 'condition1': f"{field} {op1} {val1}", 'condition2': f"{field} {op2} {val2}"}
                                        ))
                            except ValueError:
                                # Not numeric values, can't determine contradiction
                                pass
        
        return errors
    
    def _check_unrealistic_values(self, condition: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        """Check for unrealistic clinical values in a rule."""
        errors = []
        
        # Check for unrealistic values in clinical fields
        for field_name, range_info in self.clinical_ranges.items():
            # Look for patterns like "FieldName > X" or "FieldName < Y"
            pattern = re.compile(rf'\b{field_name}\s*(>|>=|=|==)\s*(\d+)')
            matches = pattern.findall(condition)
            
            for op, value_str in matches:
                value = float(value_str)
                
                if value > range_info['max']:
                    errors.append((
                        'unrealistic_value',
                        f"Unrealistic value for {field_name}: {value} (normal range is {range_info['min']}-{range_info['max']} {range_info['unit']})",
                        {'field': field_name, 'value': value, 'normal_range': f"{range_info['min']}-{range_info['max']} {range_info['unit']}"}
                    ))
                elif value < range_info['min']:
                    errors.append((
                        'unrealistic_value',
                        f"Unrealistic value for {field_name}: {value} (normal range is {range_info['min']}-{range_info['max']} {range_info['unit']})",
                        {'field': field_name, 'value': value, 'normal_range': f"{range_info['min']}-{range_info['max']} {range_info['unit']}"}
                    ))
        
        return errors
    
    def _check_type_mismatches(self, condition: str, specification: StudySpecification) -> List[Tuple[str, str, Dict[str, Any]]]:
        """Check for type mismatches in a rule."""
        errors = []
        
        # Check for date fields compared with numeric values
        date_fields = []
        for form_name, form in specification.forms.items():
            for field in form.fields:
                if field.type == FieldType.DATE:
                    date_fields.append((form_name, field.name))
        
        for form_name, field_name in date_fields:
            # Look for patterns like "FormName.FieldName > X" or "FieldName < Y" where X or Y is a number
            pattern1 = re.compile(rf'\b{form_name}\.{field_name}\s*(>|>=|<|<=|=|==)\s*(\d+)')
            pattern2 = re.compile(rf'\b{field_name}\s*(>|>=|<|<=|=|==)\s*(\d+)')
            
            matches1 = pattern1.findall(condition)
            matches2 = pattern2.findall(condition)
            
            for op, value_str in matches1 + matches2:
                errors.append((
                    'type_mismatch',
                    f"Type mismatch: comparing date field '{field_name}' with numeric value '{value_str}'",
                    {'field': field_name, 'type': 'DATE', 'value': value_str}
                ))
        
        return errors
    
    def _check_nonexistent_fields(self, forms_fields: List[Dict[str, Any]], specification: StudySpecification) -> List[Tuple[str, str, Dict[str, Any]]]:
        """Check for references to non-existent fields."""
        errors = []
        
        # Check for fields that don't exist in any form
        all_fields = set()
        for form_name, form in specification.forms.items():
            for field in form.fields:
                all_fields.add(field.name)
        
        for item in forms_fields:
            field_name = item['field']
            
            # Skip fields that are likely not actual field references
            if field_name.lower() in {'and', 'or', 'not', 'if', 'then', 'else', 'null', 'true', 'false', 'value'}:
                continue
            
            if field_name not in all_fields:
                errors.append((
                    'nonexistent_field',
                    f"Field '{field_name}' does not exist in any form in the specification",
                    {'field': field_name}
                ))
        
        return errors
    
    def _check_clinical_inconsistencies(self, condition: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        """Check for clinical inconsistencies in a rule."""
        errors = []
        
        # Check for rules that might allow systolic < diastolic
        if 'SystolicBP' in condition and 'DiastolicBP' in condition:
            if 'SystolicBP < DiastolicBP' in condition:
                errors.append((
                    'clinical_inconsistency',
                    "Clinical inconsistency: Systolic blood pressure should always be greater than diastolic blood pressure",
                    {'condition': condition}
                ))
        
        return errors
