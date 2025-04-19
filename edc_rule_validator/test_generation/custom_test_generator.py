"""
Custom Test Generator for Eclaire Trials Edit Check Rule Validation System.

This module provides a production-grade implementation of test case generation
that doesn't rely on LangGraph for compatibility with the integrated workflow.
"""

import os
import json
import random
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta

from ..models.data_models import EditCheckRule, StudySpecification, TestCase, ValidationResult, Field, FieldType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class CustomTestGenerator:
    """Custom test generator for the Edit Check Rule Validation System."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the custom test generator.
        
        Args:
            config: Optional configuration dictionary
        """
        # Default configuration
        self.config = {
            "test_techniques": ["boundary", "equivalence", "random"],
            "test_cases_per_rule": 3,
            "include_dynamics": True
        }
        
        # Update with provided config
        if config:
            self.config.update(config)
    
    def generate_tests(self, rules: List[EditCheckRule], 
                      specification: StudySpecification,
                      validation_results: List[ValidationResult]) -> List[TestCase]:
        """
        Generate test cases for valid rules.
        
        Args:
            rules: List of rules
            specification: Study specification
            validation_results: Validation results
            
        Returns:
            List of test cases
        """
        logger.info(f"Generating test cases for {len(rules)} rules...")
        
        # Get valid rules
        valid_rules = []
        for rule in rules:
            for result in validation_results:
                if result.rule_id == rule.id and result.is_valid:
                    valid_rules.append(rule)
                    break
        
        logger.info(f"Found {len(valid_rules)} valid rules for test generation")
        
        # Generate test cases
        all_test_cases = []
        
        for rule in valid_rules:
            logger.info(f"Generating test cases for rule {rule.id}...")
            
            # Generate test cases using different techniques
            test_cases = []
            
            for technique in self.config["test_techniques"]:
                # Generate test cases for this technique
                technique_test_cases = self._generate_test_cases_for_technique(
                    rule, specification, technique
                )
                test_cases.extend(technique_test_cases)
            
            # Limit the number of test cases per rule
            if len(test_cases) > self.config["test_cases_per_rule"]:
                test_cases = test_cases[:self.config["test_cases_per_rule"]]
            
            all_test_cases.extend(test_cases)
            logger.info(f"Generated {len(test_cases)} test cases for rule {rule.id}")
        
        logger.info(f"Generated {len(all_test_cases)} test cases in total")
        return all_test_cases
    
    def _generate_test_cases_for_technique(self, rule: EditCheckRule, 
                                          specification: StudySpecification,
                                          technique: str) -> List[TestCase]:
        """
        Generate test cases for a rule using a specific technique.
        
        Args:
            rule: Rule to generate test cases for
            specification: Study specification
            technique: Test generation technique
            
        Returns:
            List of test cases
        """
        if technique == "boundary":
            return self._generate_boundary_test_cases(rule, specification)
        elif technique == "equivalence":
            return self._generate_equivalence_test_cases(rule, specification)
        elif technique == "random":
            return self._generate_random_test_cases(rule, specification)
        else:
            logger.warning(f"Unknown test technique: {technique}")
            return []
    
    def _generate_boundary_test_cases(self, rule: EditCheckRule, 
                                     specification: StudySpecification) -> List[TestCase]:
        """
        Generate boundary test cases for a rule.
        
        Args:
            rule: Rule to generate test cases for
            specification: Study specification
            
        Returns:
            List of test cases
        """
        test_cases = []
        
        # Extract fields from the rule
        fields = self._extract_fields_from_rule(rule, specification)
        
        # Generate positive test case (should pass)
        positive_test_case = TestCase(
            rule_id=rule.id,
            description=f"Boundary test case (positive) for {rule.id}",
            expected_result=True,
            is_positive=True,
            test_data=self._generate_valid_test_data(rule, specification, fields),
            technique="boundary"
        )
        test_cases.append(positive_test_case)
        
        # Generate negative test case (should fail)
        negative_test_case = TestCase(
            rule_id=rule.id,
            description=f"Boundary test case (negative) for {rule.id}",
            expected_result=False,
            is_positive=False,
            test_data=self._generate_invalid_test_data(rule, specification, fields),
            technique="boundary"
        )
        test_cases.append(negative_test_case)
        
        return test_cases
    
    def _generate_equivalence_test_cases(self, rule: EditCheckRule, 
                                        specification: StudySpecification) -> List[TestCase]:
        """
        Generate equivalence test cases for a rule.
        
        Args:
            rule: Rule to generate test cases for
            specification: Study specification
            
        Returns:
            List of test cases
        """
        test_cases = []
        
        # Extract fields from the rule
        fields = self._extract_fields_from_rule(rule, specification)
        
        # Generate positive test case (should pass)
        positive_test_case = TestCase(
            rule_id=rule.id,
            description=f"Equivalence test case (positive) for {rule.id}",
            expected_result=True,
            is_positive=True,
            test_data=self._generate_valid_test_data(rule, specification, fields, variant="equivalence"),
            technique="equivalence"
        )
        test_cases.append(positive_test_case)
        
        return test_cases
    
    def _generate_random_test_cases(self, rule: EditCheckRule, 
                                   specification: StudySpecification) -> List[TestCase]:
        """
        Generate random test cases for a rule.
        
        Args:
            rule: Rule to generate test cases for
            specification: Study specification
            
        Returns:
            List of test cases
        """
        test_cases = []
        
        # Extract fields from the rule
        fields = self._extract_fields_from_rule(rule, specification)
        
        # Generate positive test case (should pass)
        positive_test_case = TestCase(
            rule_id=rule.id,
            description=f"Random test case for {rule.id}",
            expected_result=True,
            is_positive=True,
            test_data=self._generate_valid_test_data(rule, specification, fields, variant="random"),
            technique="random"
        )
        test_cases.append(positive_test_case)
        
        return test_cases
    
    def _extract_fields_from_rule(self, rule: EditCheckRule, 
                                 specification: StudySpecification) -> Dict[str, Field]:
        """
        Extract fields from a rule.
        
        Args:
            rule: Rule to extract fields from
            specification: Study specification
            
        Returns:
            Dictionary of fields
        """
        fields = {}
        
        # Extract forms from the rule
        for form_name in rule.forms:
            if form_name in specification.forms:
                form = specification.forms[form_name]
                for field in form.fields:
                    fields[f"{form_name}.{field.name}"] = field
        
        return fields
    
    def _generate_valid_test_data(self, rule: EditCheckRule, 
                                 specification: StudySpecification,
                                 fields: Dict[str, Field],
                                 variant: str = "boundary") -> Dict[str, Any]:
        """
        Generate valid test data for a rule.
        
        Args:
            rule: Rule to generate test data for
            specification: Study specification
            fields: Dictionary of fields
            variant: Variant of test data to generate
            
        Returns:
            Dictionary of test data
        """
        test_data = {}
        
        # Generate test data for each field
        for field_path, field in fields.items():
            form_name, field_name = field_path.split(".")
            
            # Generate value based on field type
            if field.type == FieldType.NUMBER:
                if variant == "boundary":
                    # Use the middle of the valid range
                    min_val = field.min_value if field.min_value is not None else 0
                    max_val = field.max_value if field.max_value is not None else 100
                    value = (min_val + max_val) / 2
                elif variant == "equivalence":
                    # Use a value within the valid range
                    min_val = field.min_value if field.min_value is not None else 0
                    max_val = field.max_value if field.max_value is not None else 100
                    value = min_val + (max_val - min_val) * 0.75
                else:  # random
                    # Use a random value within the valid range
                    min_val = field.min_value if field.min_value is not None else 0
                    max_val = field.max_value if field.max_value is not None else 100
                    value = random.uniform(min_val, max_val)
            elif field.type == FieldType.DATE:
                # Use a date within the valid range
                today = datetime.now().date()
                if variant == "boundary":
                    value = today.isoformat()
                elif variant == "equivalence":
                    value = (today - timedelta(days=7)).isoformat()
                else:  # random
                    days = random.randint(-30, 30)
                    value = (today + timedelta(days=days)).isoformat()
            elif field.type == FieldType.BOOLEAN:
                # Use a boolean value
                if "not" in rule.condition.lower() or "!" in rule.condition:
                    value = False
                else:
                    value = True
            elif field.type == FieldType.CATEGORICAL:
                # Use a valid categorical value
                if field.valid_values:
                    value = random.choice(field.valid_values)
                else:
                    value = "Category A"
            else:
                # Default to a string value
                value = f"Test value for {field_name}"
            
            # Add to test data
            if form_name not in test_data:
                test_data[form_name] = {}
            test_data[form_name][field_name] = value
        
        return test_data
    
    def _generate_invalid_test_data(self, rule: EditCheckRule, 
                                   specification: StudySpecification,
                                   fields: Dict[str, Field]) -> Dict[str, Any]:
        """
        Generate invalid test data for a rule.
        
        Args:
            rule: Rule to generate test data for
            specification: Study specification
            fields: Dictionary of fields
            
        Returns:
            Dictionary of test data
        """
        # Start with valid test data
        test_data = self._generate_valid_test_data(rule, specification, fields)
        
        # Modify one field to make the test data invalid
        if fields:
            # Choose a random field
            field_path = random.choice(list(fields.keys()))
            form_name, field_name = field_path.split(".")
            field = fields[field_path]
            
            # Modify the value based on field type
            if field.type == FieldType.NUMBER:
                # Use a value outside the valid range
                if field.min_value is not None:
                    test_data[form_name][field_name] = field.min_value - 1
                elif field.max_value is not None:
                    test_data[form_name][field_name] = field.max_value + 1
                else:
                    test_data[form_name][field_name] = -999
            elif field.type == FieldType.DATE:
                # Use a date in the far future
                test_data[form_name][field_name] = "2099-12-31"
            elif field.type == FieldType.BOOLEAN:
                # Invert the boolean value
                test_data[form_name][field_name] = not test_data[form_name][field_name]
            elif field.type == FieldType.CATEGORICAL:
                # Use an invalid categorical value
                if field.valid_values:
                    test_data[form_name][field_name] = "Invalid category"
                else:
                    test_data[form_name][field_name] = "Invalid category"
            else:
                # Default to an invalid string value
                test_data[form_name][field_name] = ""
        
        return test_data
