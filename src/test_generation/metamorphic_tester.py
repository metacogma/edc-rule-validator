"""
Metamorphic Testing module for Edit Check Rule Validation System.

This module implements metamorphic testing principles to generate test cases
that exploit invariant properties of clinical trial rules.
"""

import re
import copy
import random
from typing import List, Dict, Any, Tuple, Set, Optional
import numpy as np
from datetime import datetime, timedelta

from ..models.data_models import EditCheckRule, StudySpecification, TestCase, FieldType
from ..utils.logger import Logger

logger = Logger(__name__)

class MetamorphicTester:
    """Generate test cases using metamorphic testing principles."""
    
    def __init__(self):
        """Initialize the metamorphic tester."""
        # Patterns for extracting numerical comparisons
        self.num_comparison_pattern = re.compile(r'([A-Za-z0-9_.]+)\s*([<>=!]+)\s*(\d+(?:\.\d+)?)')
        self.date_comparison_pattern = re.compile(r'([A-Za-z0-9_.]+)\s*([<>=!]+)\s*([A-Za-z0-9_.]+)')
        
        # Define metamorphic relations
        self.metamorphic_relations = {
            # For numerical fields
            '>': [
                ('increase', True),   # If x > a is true, then x + δ > a is true for any δ > 0
                ('decrease_within', False),  # If x > a is true, then x - δ > a may be false if δ > x - a
                ('decrease_beyond', False)   # If x > a is true, then x - δ > a is false for δ > x - a
            ],
            '>=': [
                ('increase', True),   # If x >= a is true, then x + δ >= a is true for any δ > 0
                ('decrease_within', True),   # If x >= a is true, then x - δ >= a is true for δ < x - a
                ('decrease_beyond', False)   # If x >= a is true, then x - δ >= a is false for δ > x - a
            ],
            '<': [
                ('decrease', True),   # If x < a is true, then x - δ < a is true for any δ > 0
                ('increase_within', False),  # If x < a is true, then x + δ < a may be false if δ > a - x
                ('increase_beyond', False)   # If x < a is true, then x + δ < a is false for δ > a - x
            ],
            '<=': [
                ('decrease', True),   # If x <= a is true, then x - δ <= a is true for any δ > 0
                ('increase_within', True),   # If x <= a is true, then x + δ <= a is true for δ < a - x
                ('increase_beyond', False)   # If x <= a is true, then x + δ <= a is false for δ > a - x
            ],
            '=': [
                ('exact_match', True),       # If x = a is true, then x = a is true (identity)
                ('slight_change', False)     # If x = a is true, then x ± δ = a is false for any δ ≠ 0
            ],
            '!=': [
                ('any_change', True),        # If x != a is true, then x ± δ != a is true for any δ ≠ a - x
                ('exact_match', False)       # If x != a is true, then x + (a - x) != a is false
            ]
        }
    
    def generate_metamorphic_tests(self, rule: EditCheckRule, specification: StudySpecification) -> List[TestCase]:
        """
        Generate test cases based on metamorphic relations.
        
        Args:
            rule: The rule to generate test cases for
            specification: The study specification
            
        Returns:
            List of test cases
        """
        test_cases = []
        
        # Use formalized condition if available, otherwise use original condition
        condition = rule.formalized_condition or rule.condition
        
        # Extract numerical comparisons from the rule
        numerical_comparisons = self._extract_numerical_comparisons(condition)
        
        # Generate base test cases
        base_tests = self._generate_base_tests(rule, specification, numerical_comparisons)
        
        # For each base test, generate follow-up tests using metamorphic relations
        for base_test in base_tests:
            follow_up_tests = self._generate_follow_up_tests(
                rule, specification, base_test, numerical_comparisons
            )
            test_cases.append(base_test)
            test_cases.extend(follow_up_tests)
        
        logger.info(f"Generated {len(test_cases)} metamorphic test cases for rule {rule.id}")
        return test_cases
    
    def _extract_numerical_comparisons(self, condition: str) -> List[Tuple[str, str, float]]:
        """
        Extract numerical comparisons from a rule condition.
        
        Args:
            condition: Rule condition
            
        Returns:
            List of (field, operator, value) tuples
        """
        comparisons = []
        
        # Find all numerical comparisons
        matches = self.num_comparison_pattern.findall(condition)
        for field, operator, value in matches:
            try:
                numeric_value = float(value)
                comparisons.append((field, operator, numeric_value))
            except ValueError:
                # Not a numeric value
                pass
        
        return comparisons
    
    def _generate_base_tests(
        self, 
        rule: EditCheckRule, 
        specification: StudySpecification,
        comparisons: List[Tuple[str, str, float]]
    ) -> List[TestCase]:
        """
        Generate base test cases for metamorphic testing.
        
        Args:
            rule: The rule to generate test cases for
            specification: The study specification
            comparisons: List of numerical comparisons
            
        Returns:
            List of base test cases
        """
        base_tests = []
        
        # Generate a positive base test
        positive_test_data = self._create_positive_test_data(rule, specification, comparisons)
        if positive_test_data:
            positive_test = TestCase(
                rule_id=rule.id,
                description=f"Base positive test for rule {rule.id}",
                expected_result=True,
                test_data=positive_test_data,
                is_positive=True
            )
            base_tests.append(positive_test)
        
        # Generate a negative base test
        negative_test_data = self._create_negative_test_data(rule, specification, comparisons)
        if negative_test_data:
            negative_test = TestCase(
                rule_id=rule.id,
                description=f"Base negative test for rule {rule.id}",
                expected_result=False,
                test_data=negative_test_data,
                is_positive=False
            )
            base_tests.append(negative_test)
        
        return base_tests
    
    def _create_positive_test_data(
        self, 
        rule: EditCheckRule, 
        specification: StudySpecification,
        comparisons: List[Tuple[str, str, float]]
    ) -> Dict[str, Any]:
        """
        Create test data that should satisfy the rule.
        
        Args:
            rule: The rule to create test data for
            specification: The study specification
            comparisons: List of numerical comparisons
            
        Returns:
            Dictionary of test data
        """
        test_data = {}
        
        # Process each comparison
        for field_path, operator, value in comparisons:
            # Split field path into form and field
            if '.' in field_path:
                form_name, field_name = field_path.split('.', 1)
                
                # Get field type from specification
                field_type = self._get_field_type(specification, form_name, field_name)
                
                # Initialize form in test data if not exists
                if form_name not in test_data:
                    test_data[form_name] = {}
                
                # Set field value based on operator and field type
                if field_type == FieldType.NUMBER:
                    test_data[form_name][field_name] = self._get_satisfying_numeric_value(operator, value)
                elif field_type == FieldType.DATE:
                    test_data[form_name][field_name] = self._get_satisfying_date_value(operator, value)
                elif field_type == FieldType.CATEGORICAL:
                    valid_values = self._get_valid_values(specification, form_name, field_name)
                    if valid_values:
                        test_data[form_name][field_name] = random.choice(valid_values)
                else:
                    # For other types, use a default value
                    test_data[form_name][field_name] = "Test Value"
        
        return test_data
    
    def _create_negative_test_data(
        self, 
        rule: EditCheckRule, 
        specification: StudySpecification,
        comparisons: List[Tuple[str, str, float]]
    ) -> Dict[str, Any]:
        """
        Create test data that should violate the rule.
        
        Args:
            rule: The rule to create test data for
            specification: The study specification
            comparisons: List of numerical comparisons
            
        Returns:
            Dictionary of test data
        """
        test_data = {}
        
        # If no comparisons, create empty test data
        if not comparisons:
            return test_data
        
        # Choose one comparison to violate
        field_path, operator, value = random.choice(comparisons)
        
        # Split field path into form and field
        if '.' in field_path:
            form_name, field_name = field_path.split('.', 1)
            
            # Get field type from specification
            field_type = self._get_field_type(specification, form_name, field_name)
            
            # Initialize form in test data if not exists
            if form_name not in test_data:
                test_data[form_name] = {}
            
            # Set field value that violates the operator
            if field_type == FieldType.NUMBER:
                test_data[form_name][field_name] = self._get_violating_numeric_value(operator, value)
            elif field_type == FieldType.DATE:
                test_data[form_name][field_name] = self._get_violating_date_value(operator, value)
            elif field_type == FieldType.CATEGORICAL:
                valid_values = self._get_valid_values(specification, form_name, field_name)
                if valid_values and len(valid_values) > 1:
                    # Choose a value that doesn't match the expected value
                    expected_value = str(value).strip('"\'')
                    other_values = [v for v in valid_values if v != expected_value]
                    if other_values:
                        test_data[form_name][field_name] = random.choice(other_values)
            else:
                # For other types, use a default value
                test_data[form_name][field_name] = "Invalid Value"
        
        # For other comparisons, use satisfying values
        for other_field_path, other_operator, other_value in comparisons:
            if other_field_path != field_path:
                if '.' in other_field_path:
                    other_form_name, other_field_name = other_field_path.split('.', 1)
                    
                    # Get field type from specification
                    other_field_type = self._get_field_type(specification, other_form_name, other_field_name)
                    
                    # Initialize form in test data if not exists
                    if other_form_name not in test_data:
                        test_data[other_form_name] = {}
                    
                    # Set field value based on operator and field type
                    if other_field_type == FieldType.NUMBER:
                        test_data[other_form_name][other_field_name] = self._get_satisfying_numeric_value(other_operator, other_value)
                    elif other_field_type == FieldType.DATE:
                        test_data[other_form_name][other_field_name] = self._get_satisfying_date_value(other_operator, other_value)
                    elif other_field_type == FieldType.CATEGORICAL:
                        valid_values = self._get_valid_values(specification, other_form_name, other_field_name)
                        if valid_values:
                            test_data[other_form_name][other_field_name] = random.choice(valid_values)
                    else:
                        # For other types, use a default value
                        test_data[other_form_name][other_field_name] = "Test Value"
        
        return test_data
    
    def _generate_follow_up_tests(
        self, 
        rule: EditCheckRule, 
        specification: StudySpecification,
        base_test: TestCase,
        comparisons: List[Tuple[str, str, float]]
    ) -> List[TestCase]:
        """
        Generate follow-up test cases using metamorphic relations.
        
        Args:
            rule: The rule to generate test cases for
            specification: The study specification
            base_test: The base test case
            comparisons: List of numerical comparisons
            
        Returns:
            List of follow-up test cases
        """
        follow_up_tests = []
        
        # For each comparison, apply metamorphic relations
        for field_path, operator, value in comparisons:
            # Split field path into form and field
            if '.' in field_path:
                form_name, field_name = field_path.split('.', 1)
                
                # Check if the form and field exist in the base test
                if form_name in base_test.test_data and field_name in base_test.test_data[form_name]:
                    base_value = base_test.test_data[form_name][field_name]
                    
                    # Get field type from specification
                    field_type = self._get_field_type(specification, form_name, field_name)
                    
                    # Apply metamorphic relations based on field type
                    if field_type == FieldType.NUMBER and isinstance(base_value, (int, float)):
                        follow_up_tests.extend(
                            self._apply_numeric_metamorphic_relations(
                                rule, base_test, form_name, field_name, operator, base_value, value
                            )
                        )
                    elif field_type == FieldType.DATE and isinstance(base_value, str):
                        follow_up_tests.extend(
                            self._apply_date_metamorphic_relations(
                                rule, base_test, form_name, field_name, operator, base_value, value
                            )
                        )
        
        return follow_up_tests
    
    def _apply_numeric_metamorphic_relations(
        self, 
        rule: EditCheckRule,
        base_test: TestCase,
        form_name: str,
        field_name: str,
        operator: str,
        base_value: float,
        threshold: float
    ) -> List[TestCase]:
        """
        Apply numeric metamorphic relations to generate follow-up tests.
        
        Args:
            rule: The rule to generate test cases for
            base_test: The base test case
            form_name: Form name
            field_name: Field name
            operator: Comparison operator
            base_value: Base value
            threshold: Threshold value
            
        Returns:
            List of follow-up test cases
        """
        follow_up_tests = []
        
        # Get metamorphic relations for the operator
        relations = self.metamorphic_relations.get(operator, [])
        
        for relation_type, expected_result in relations:
            # Create a copy of the base test data
            test_data = copy.deepcopy(base_test.test_data)
            
            # Apply the relation
            if relation_type == 'increase':
                delta = abs(threshold - base_value) * 0.5 + 1  # Ensure it's significant
                test_data[form_name][field_name] = base_value + delta
            elif relation_type == 'decrease':
                delta = abs(threshold - base_value) * 0.5 + 1  # Ensure it's significant
                test_data[form_name][field_name] = base_value - delta
            elif relation_type == 'increase_within':
                delta = abs(threshold - base_value) * 0.5  # Stay within the boundary
                test_data[form_name][field_name] = base_value + delta
            elif relation_type == 'increase_beyond':
                delta = abs(threshold - base_value) * 1.5 + 1  # Go beyond the boundary
                test_data[form_name][field_name] = base_value + delta
            elif relation_type == 'decrease_within':
                delta = abs(threshold - base_value) * 0.5  # Stay within the boundary
                test_data[form_name][field_name] = base_value - delta
            elif relation_type == 'decrease_beyond':
                delta = abs(threshold - base_value) * 1.5 + 1  # Go beyond the boundary
                test_data[form_name][field_name] = base_value - delta
            elif relation_type == 'exact_match':
                test_data[form_name][field_name] = threshold
            elif relation_type == 'slight_change':
                test_data[form_name][field_name] = threshold + 0.1
            
            # Create the follow-up test case
            follow_up_test = TestCase(
                rule_id=rule.id,
                description=f"Follow-up test for rule {rule.id} with {relation_type} on {form_name}.{field_name}",
                expected_result=expected_result,
                test_data=test_data,
                is_positive=expected_result
            )
            
            follow_up_tests.append(follow_up_test)
        
        return follow_up_tests
    
    def _apply_date_metamorphic_relations(
        self, 
        rule: EditCheckRule,
        base_test: TestCase,
        form_name: str,
        field_name: str,
        operator: str,
        base_value: str,
        threshold: Any
    ) -> List[TestCase]:
        """
        Apply date metamorphic relations to generate follow-up tests.
        
        Args:
            rule: The rule to generate test cases for
            base_test: The base test case
            form_name: Form name
            field_name: Field name
            operator: Comparison operator
            base_value: Base value (date string)
            threshold: Threshold value
            
        Returns:
            List of follow-up test cases
        """
        follow_up_tests = []
        
        try:
            # Parse base date
            base_date = datetime.strptime(base_value, "%Y-%m-%d")
            
            # Get metamorphic relations for the operator
            relations = self.metamorphic_relations.get(operator, [])
            
            for relation_type, expected_result in relations:
                # Create a copy of the base test data
                test_data = copy.deepcopy(base_test.test_data)
                
                # Apply the relation
                if relation_type == 'increase':
                    test_data[form_name][field_name] = (base_date + timedelta(days=10)).strftime("%Y-%m-%d")
                elif relation_type == 'decrease':
                    test_data[form_name][field_name] = (base_date - timedelta(days=10)).strftime("%Y-%m-%d")
                elif relation_type == 'increase_within':
                    test_data[form_name][field_name] = (base_date + timedelta(days=3)).strftime("%Y-%m-%d")
                elif relation_type == 'increase_beyond':
                    test_data[form_name][field_name] = (base_date + timedelta(days=30)).strftime("%Y-%m-%d")
                elif relation_type == 'decrease_within':
                    test_data[form_name][field_name] = (base_date - timedelta(days=3)).strftime("%Y-%m-%d")
                elif relation_type == 'decrease_beyond':
                    test_data[form_name][field_name] = (base_date - timedelta(days=30)).strftime("%Y-%m-%d")
                elif relation_type == 'exact_match':
                    # Keep the same date
                    pass
                elif relation_type == 'slight_change':
                    test_data[form_name][field_name] = (base_date + timedelta(days=1)).strftime("%Y-%m-%d")
                
                # Create the follow-up test case
                follow_up_test = TestCase(
                    rule_id=rule.id,
                    description=f"Follow-up test for rule {rule.id} with {relation_type} on {form_name}.{field_name}",
                    expected_result=expected_result,
                    test_data=test_data,
                    is_positive=expected_result
                )
                
                follow_up_tests.append(follow_up_test)
        
        except (ValueError, TypeError):
            # Could not parse date, skip
            pass
        
        return follow_up_tests
    
    def _get_field_type(self, specification: StudySpecification, form_name: str, field_name: str) -> FieldType:
        """
        Get the type of a field from the specification.
        
        Args:
            specification: Study specification
            form_name: Form name
            field_name: Field name
            
        Returns:
            Field type
        """
        field = specification.get_field(form_name, field_name)
        if field:
            return field.type
        return FieldType.TEXT
    
    def _get_valid_values(self, specification: StudySpecification, form_name: str, field_name: str) -> List[str]:
        """
        Get valid values for a categorical field.
        
        Args:
            specification: Study specification
            form_name: Form name
            field_name: Field name
            
        Returns:
            List of valid values
        """
        field = specification.get_field(form_name, field_name)
        if field and field.valid_values:
            return [v.strip() for v in field.valid_values.split(',')]
        return []
    
    def _get_satisfying_numeric_value(self, operator: str, threshold: float) -> float:
        """
        Get a numeric value that satisfies the comparison.
        
        Args:
            operator: Comparison operator
            threshold: Threshold value
            
        Returns:
            Satisfying value
        """
        if operator == '>':
            return threshold + random.uniform(1, 10)
        elif operator == '>=':
            return threshold + random.uniform(0, 10)
        elif operator == '<':
            return threshold - random.uniform(1, 10)
        elif operator == '<=':
            return threshold - random.uniform(0, 10)
        elif operator == '=':
            return threshold
        elif operator == '!=':
            return threshold + random.choice([-10, 10])
        return threshold
    
    def _get_violating_numeric_value(self, operator: str, threshold: float) -> float:
        """
        Get a numeric value that violates the comparison.
        
        Args:
            operator: Comparison operator
            threshold: Threshold value
            
        Returns:
            Violating value
        """
        if operator == '>':
            return threshold - random.uniform(0, 5)
        elif operator == '>=':
            return threshold - random.uniform(0.1, 5)
        elif operator == '<':
            return threshold + random.uniform(0, 5)
        elif operator == '<=':
            return threshold + random.uniform(0.1, 5)
        elif operator == '=':
            return threshold + random.choice([-5, 5])
        elif operator == '!=':
            return threshold
        return threshold
    
    def _get_satisfying_date_value(self, operator: str, threshold: Any) -> str:
        """
        Get a date value that satisfies the comparison.
        
        Args:
            operator: Comparison operator
            threshold: Threshold value
            
        Returns:
            Satisfying date value
        """
        base_date = datetime.now()
        
        if operator == '>':
            return (base_date + timedelta(days=10)).strftime("%Y-%m-%d")
        elif operator == '>=':
            return base_date.strftime("%Y-%m-%d")
        elif operator == '<':
            return (base_date - timedelta(days=10)).strftime("%Y-%m-%d")
        elif operator == '<=':
            return base_date.strftime("%Y-%m-%d")
        elif operator == '=':
            return base_date.strftime("%Y-%m-%d")
        elif operator == '!=':
            return (base_date + timedelta(days=10)).strftime("%Y-%m-%d")
        
        return base_date.strftime("%Y-%m-%d")
    
    def _get_violating_date_value(self, operator: str, threshold: Any) -> str:
        """
        Get a date value that violates the comparison.
        
        Args:
            operator: Comparison operator
            threshold: Threshold value
            
        Returns:
            Violating date value
        """
        base_date = datetime.now()
        
        if operator == '>':
            return (base_date - timedelta(days=10)).strftime("%Y-%m-%d")
        elif operator == '>=':
            return (base_date - timedelta(days=1)).strftime("%Y-%m-%d")
        elif operator == '<':
            return (base_date + timedelta(days=10)).strftime("%Y-%m-%d")
        elif operator == '<=':
            return (base_date + timedelta(days=1)).strftime("%Y-%m-%d")
        elif operator == '=':
            return (base_date + timedelta(days=1)).strftime("%Y-%m-%d")
        elif operator == '!=':
            return base_date.strftime("%Y-%m-%d")
        
        return base_date.strftime("%Y-%m-%d")
