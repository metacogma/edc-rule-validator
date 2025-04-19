"""
Dynamics Validator for Eclaire Trials Edit Check Rule Validation System.

This module provides validation for dynamic calculations and derivatives
in clinical trial rules, ensuring they are correctly defined and can be
properly evaluated.
"""

import re
from typing import Dict, List, Any, Optional, Tuple

from ..models.data_models import EditCheckRule, StudySpecification, ValidationResult
from ..utils.dynamics import DynamicsProcessor
from ..utils.logger import Logger

logger = Logger(__name__)

class DynamicsValidator:
    """Validator for dynamics and derivatives in edit check rules."""
    
    def __init__(self):
        """Initialize the dynamics validator."""
        self.dynamics_processor = DynamicsProcessor()
    
    def validate_rule_dynamics(self, rule: EditCheckRule, spec: StudySpecification) -> ValidationResult:
        """
        Validate dynamics and derivatives in a rule.
        
        Args:
            rule: The rule to validate
            spec: The study specification
            
        Returns:
            ValidationResult with validation results
        """
        result = ValidationResult(rule_id=rule.id, is_valid=True)
        
        # Extract dynamics from the rule condition
        dynamics = self.dynamics_processor.extract_dynamics(rule.condition)
        
        # If no dynamics, rule is valid (from dynamics perspective)
        if not dynamics:
            return result
        
        # Validate each dynamic function
        for dynamic in dynamics:
            function_name = dynamic['function']
            parameters = dynamic['parameters']
            original = dynamic['original']
            
            # Check if function exists
            if function_name not in self.dynamics_processor.dynamic_functions:
                result.add_error(
                    error_type="unknown_dynamic_function",
                    message=f"Unknown dynamic function: {function_name}",
                    details={"function": function_name, "original": original}
                )
                continue
            
            # Validate parameters
            param_validation = self._validate_parameters(function_name, parameters, spec)
            if not param_validation['is_valid']:
                for error in param_validation['errors']:
                    result.add_error(
                        error_type="invalid_dynamic_parameters",
                        message=error,
                        details={"function": function_name, "parameters": parameters, "original": original}
                    )
        
        # Update result validity
        result.is_valid = len(result.errors) == 0
        
        return result
    
    def _validate_parameters(self, function_name: str, parameters: List[str], spec: StudySpecification) -> Dict[str, Any]:
        """
        Validate parameters for a dynamic function.
        
        Args:
            function_name: Name of the dynamic function
            parameters: List of parameter strings
            spec: Study specification
            
        Returns:
            Dictionary with validation results
        """
        result = {"is_valid": True, "errors": []}
        
        # Define parameter requirements for each function
        param_requirements = {
            # Time-based functions
            "DAYS_BETWEEN": {"min_params": 2, "max_params": 2, "types": ["date", "date"]},
            "MONTHS_BETWEEN": {"min_params": 2, "max_params": 2, "types": ["date", "date"]},
            "YEARS_BETWEEN": {"min_params": 2, "max_params": 2, "types": ["date", "date"]},
            
            # Change calculations
            "CHANGE_FROM_BASELINE": {"min_params": 2, "max_params": 2, "types": ["number", "number"]},
            "PERCENT_CHANGE_FROM_BASELINE": {"min_params": 2, "max_params": 2, "types": ["number", "number"]},
            "CHANGE_FROM_PREVIOUS": {"min_params": 2, "max_params": 2, "types": ["number", "number"]},
            
            # Rate calculations
            "RATE_OF_CHANGE": {"min_params": 4, "max_params": 4, "types": ["number", "number", "date", "date"]},
            "SLOPE": {"min_params": 2, "max_params": 2, "types": ["number_list", "date_list"]},
            
            # Common derivatives
            "BMI": {"min_params": 2, "max_params": 2, "types": ["number", "number"]},
            "BSA": {"min_params": 2, "max_params": 2, "types": ["number", "number"]},
            "EGFR": {"min_params": 3, "max_params": 5, "types": ["number", "number", "string", "boolean", "number"]},
            
            # Statistical functions
            "MEAN": {"min_params": 1, "max_params": 1, "types": ["number_list"]},
            "MEDIAN": {"min_params": 1, "max_params": 1, "types": ["number_list"]},
            "STD_DEV": {"min_params": 1, "max_params": 1, "types": ["number_list"]},
            "MIN": {"min_params": 1, "max_params": 1, "types": ["number_list"]},
            "MAX": {"min_params": 1, "max_params": 1, "types": ["number_list"]},
            
            # Temporal patterns
            "IS_INCREASING": {"min_params": 1, "max_params": 1, "types": ["number_list"]},
            "IS_DECREASING": {"min_params": 1, "max_params": 1, "types": ["number_list"]},
            "HAS_DOUBLED": {"min_params": 2, "max_params": 2, "types": ["number", "number"]},
            "HAS_HALVED": {"min_params": 2, "max_params": 2, "types": ["number", "number"]}
        }
        
        # Get requirements for this function
        requirements = param_requirements.get(function_name, {"min_params": 0, "max_params": 99, "types": []})
        
        # Check number of parameters
        if len(parameters) < requirements["min_params"]:
            result["is_valid"] = False
            result["errors"].append(
                f"Function {function_name} requires at least {requirements['min_params']} parameters, but got {len(parameters)}"
            )
        
        if len(parameters) > requirements["max_params"]:
            result["is_valid"] = False
            result["errors"].append(
                f"Function {function_name} accepts at most {requirements['max_params']} parameters, but got {len(parameters)}"
            )
        
        # Check parameter types
        for i, param in enumerate(parameters):
            if i >= len(requirements["types"]):
                break
                
            expected_type = requirements["types"][i]
            
            # Check if parameter is a form.field reference
            if "." in param:
                form_name, field_name = param.split(".", 1)
                
                # Check if form exists
                if form_name not in spec.forms:
                    result["is_valid"] = False
                    result["errors"].append(f"Form '{form_name}' not found in specification")
                    continue
                
                # Check if field exists in form
                field = next((f for f in spec.forms[form_name].fields if f.name == field_name), None)
                if field is None:
                    result["is_valid"] = False
                    result["errors"].append(f"Field '{field_name}' not found in form '{form_name}'")
                    continue
                
                # Check if field type is compatible with expected parameter type
                if expected_type == "number" and field.type.value not in ["number"]:
                    result["is_valid"] = False
                    result["errors"].append(
                        f"Parameter {i+1} of {function_name} should be a number, but field '{param}' is of type '{field.type.value}'"
                    )
                
                if expected_type == "date" and field.type.value not in ["date", "datetime"]:
                    result["is_valid"] = False
                    result["errors"].append(
                        f"Parameter {i+1} of {function_name} should be a date, but field '{param}' is of type '{field.type.value}'"
                    )
                
                if expected_type == "string" and field.type.value not in ["text", "categorical"]:
                    result["is_valid"] = False
                    result["errors"].append(
                        f"Parameter {i+1} of {function_name} should be a string, but field '{param}' is of type '{field.type.value}'"
                    )
                
                if expected_type == "boolean" and field.type.value not in ["boolean"]:
                    result["is_valid"] = False
                    result["errors"].append(
                        f"Parameter {i+1} of {function_name} should be a boolean, but field '{param}' is of type '{field.type.value}'"
                    )
                
                if expected_type == "number_list" and field.type.value not in ["number"]:
                    result["is_valid"] = False
                    result["errors"].append(
                        f"Parameter {i+1} of {function_name} should be a list of numbers, but field '{param}' is of type '{field.type.value}'"
                    )
                
                if expected_type == "date_list" and field.type.value not in ["date", "datetime"]:
                    result["is_valid"] = False
                    result["errors"].append(
                        f"Parameter {i+1} of {function_name} should be a list of dates, but field '{param}' is of type '{field.type.value}'"
                    )
            
            # Check if parameter is a literal value
            else:
                # Check numeric literals
                if expected_type == "number":
                    try:
                        float(param)
                    except ValueError:
                        result["is_valid"] = False
                        result["errors"].append(
                            f"Parameter {i+1} of {function_name} should be a number, but got '{param}'"
                        )
                
                # Check date literals
                if expected_type == "date":
                    if not self._is_date_literal(param):
                        result["is_valid"] = False
                        result["errors"].append(
                            f"Parameter {i+1} of {function_name} should be a date, but got '{param}'"
                        )
                
                # Check boolean literals
                if expected_type == "boolean":
                    if param.lower() not in ["true", "false", "yes", "no", "1", "0"]:
                        result["is_valid"] = False
                        result["errors"].append(
                            f"Parameter {i+1} of {function_name} should be a boolean, but got '{param}'"
                        )
                
                # Check list literals
                if expected_type in ["number_list", "date_list"]:
                    if not self._is_list_literal(param):
                        result["is_valid"] = False
                        result["errors"].append(
                            f"Parameter {i+1} of {function_name} should be a list, but got '{param}'"
                        )
        
        return result
    
    def _is_date_literal(self, value: str) -> bool:
        """Check if a string is a date literal."""
        # Common date formats: YYYY-MM-DD, DD-MM-YYYY, MM/DD/YYYY, etc.
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}-\d{2}-\d{4}',  # DD-MM-YYYY
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY or DD/MM/YYYY
            r'\d{4}/\d{2}/\d{2}'   # YYYY/MM/DD
        ]
        
        return any(re.match(pattern, value) for pattern in date_patterns)
    
    def _is_list_literal(self, value: str) -> bool:
        """Check if a string is a list literal."""
        # List literals: comma-separated values, possibly with brackets
        list_patterns = [
            r'\[.*\]',  # [...] format
            r'.*,.*'    # comma-separated format
        ]
        
        return any(re.match(pattern, value) for pattern in list_patterns)
