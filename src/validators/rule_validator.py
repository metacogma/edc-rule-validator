"""
Rule validator for the Edit Check Rule Validation System.

This module provides functionality to validate edit check rules against
study specifications, ensuring logical consistency and completeness.
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple

from ..models.data_models import EditCheckRule, StudySpecification, ValidationResult
from ..utils.logger import Logger

logger = Logger(__name__)

class RuleValidator:
    """Validate edit check rules against study specifications."""
    
    def __init__(self):
        """Initialize the rule validator."""
        # Common patterns for rule parsing
        self.form_field_pattern = re.compile(r'([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)')
        self.comparison_operators = ['=', '!=', '<', '<=', '>', '>=', 'IN', 'NOT IN', 'BETWEEN']
        self.logical_operators = ['AND', 'OR', 'NOT']
        self.conditional_patterns = [
            re.compile(r'IF\s+(.+?)\s+THEN\s+(.+?)\s+(MUST\s+BE|SHOULD\s+BE|MUST\s+NOT\s+BE|SHOULD\s+NOT\s+BE)\s+(.+)', re.IGNORECASE),
            re.compile(r'WHEN\s+(.+?)\s+THEN\s+(.+?)\s+(MUST\s+BE|SHOULD\s+BE|MUST\s+NOT\s+BE|SHOULD\s+NOT\s+BE)\s+(.+)', re.IGNORECASE)
        ]
    
    def validate_rules(self, rules: List[EditCheckRule], specification: StudySpecification) -> List[ValidationResult]:
        """
        Validate a list of rules against a study specification.
        
        Args:
            rules: List of rules to validate
            specification: Study specification to validate against
            
        Returns:
            List of validation results
        """
        results = []
        
        for rule in rules:
            result = self.validate_rule(rule, specification)
            results.append(result)
            
            if not result.is_valid:
                logger.warning(f"Rule {rule.id} failed validation with {len(result.errors)} errors")
            else:
                logger.info(f"Rule {rule.id} passed validation")
        
        return results
    
    def validate_rule(self, rule: EditCheckRule, specification: StudySpecification) -> ValidationResult:
        """
        Validate a single rule against a study specification.
        
        Args:
            rule: Rule to validate
            specification: Study specification to validate against
            
        Returns:
            Validation result
        """
        result = ValidationResult(rule_id=rule.id, is_valid=True)
        
        # Check if rule has a condition
        if not rule.condition:
            result.add_error(
                'missing_condition',
                f"Rule {rule.id} is missing a condition"
            )
            return result
        
        # Extract forms and fields from the rule condition
        forms_fields = self._extract_forms_fields(rule.condition)
        
        # Validate forms and fields against specification
        for form_name, field_name in forms_fields:
            # Check if form exists
            if form_name not in specification.forms:
                result.add_error(
                    'invalid_form',
                    f"Form '{form_name}' referenced in rule {rule.id} does not exist in the specification",
                    {'form': form_name}
                )
                continue
            
            # Check if field exists in form
            form = specification.forms.get(form_name)
            field_exists = False
            
            for field in form.fields:
                if field.name == field_name:
                    field_exists = True
                    break
            
            if not field_exists:
                result.add_error(
                    'invalid_field',
                    f"Field '{field_name}' in form '{form_name}' referenced in rule {rule.id} does not exist in the specification",
                    {'form': form_name, 'field': field_name}
                )
        
        # Validate rule syntax
        syntax_errors = self._validate_rule_syntax(rule.condition)
        for error_type, message, details in syntax_errors:
            result.add_error(error_type, message, details)
        
        # Validate rule semantics
        semantic_errors = self._validate_rule_semantics(rule.condition, specification)
        for error_type, message, details in semantic_errors:
            result.add_error(error_type, message, details)
        
        return result
    
    def _extract_forms_fields(self, condition: str) -> List[Tuple[str, str]]:
        """
        Extract form and field references from a rule condition.
        
        Args:
            condition: Rule condition to extract from
            
        Returns:
            List of (form_name, field_name) tuples
        """
        matches = self.form_field_pattern.findall(condition)
        return matches
    
    def _validate_rule_syntax(self, condition: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        Validate the syntax of a rule condition.
        
        Args:
            condition: Rule condition to validate
            
        Returns:
            List of (error_type, message, details) tuples
        """
        errors = []
        
        # Check for balanced parentheses
        if condition.count('(') != condition.count(')'):
            errors.append((
                'unbalanced_parentheses',
                f"Unbalanced parentheses in condition: {condition}",
                {'condition': condition}
            ))
        
        # Check for invalid comparison operators
        words = re.findall(r'\b\w+\b', condition)
        for word in words:
            if word.upper() in ['EQUAL', 'EQUALS', 'EQUAL TO']:
                errors.append((
                    'invalid_operator',
                    f"Invalid operator '{word}' in condition. Use '=' instead.",
                    {'condition': condition, 'operator': word}
                ))
        
        # Check for missing logical operators between conditions
        # This is a simplified check and might need enhancement
        if ' AND' not in condition.upper() and ' OR' not in condition.upper() and ',' in condition:
            errors.append((
                'missing_logical_operator',
                f"Possible missing logical operator (AND/OR) in condition: {condition}",
                {'condition': condition}
            ))
        
        return errors
    
    def _validate_rule_semantics(self, condition: str, specification: StudySpecification) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        Validate the semantics of a rule condition against a study specification.
        
        Args:
            condition: Rule condition to validate
            specification: Study specification to validate against
            
        Returns:
            List of (error_type, message, details) tuples
        """
        errors = []
        
        # Extract form.field references
        form_field_refs = self.form_field_pattern.findall(condition)
        
        for form_name, field_name in form_field_refs:
            # Skip if form doesn't exist (already checked in validate_rule)
            if form_name not in specification.forms:
                continue
            
            # Get the field
            field = specification.get_field(form_name, field_name)
            if not field:
                continue
            
            # Check for type compatibility in comparisons
            if field.type.value in ['number', 'date', 'datetime', 'time']:
                # Check for string comparisons with numeric fields
                if f"{form_name}.{field_name}" in condition and '"' in condition and '=' in condition:
                    # This is a simplified check - in a real system, we'd parse the condition more thoroughly
                    errors.append((
                        'type_mismatch',
                        f"Possible type mismatch: comparing {field.type.value} field '{form_name}.{field_name}' with a string value",
                        {'form': form_name, 'field': field_name, 'field_type': field.type.value}
                    ))
            
            # Check for valid categorical values
            if field.type.value == 'categorical' and field.valid_values:
                valid_values_set = {v.strip() for v in field.valid_values.split(',')}
                
                # Extract string literals that might be compared with this field
                # This is a simplified approach - in a real system, we'd parse the condition more thoroughly
                string_literals = re.findall(r'"([^"]*)"', condition)
                for value in string_literals:
                    if f"{form_name}.{field_name}" in condition and value not in valid_values_set:
                        errors.append((
                            'invalid_categorical_value',
                            f"Value '{value}' is not in the valid values for categorical field '{form_name}.{field_name}'",
                            {'form': form_name, 'field': field_name, 'value': value, 'valid_values': field.valid_values}
                        ))
        
        return errors
