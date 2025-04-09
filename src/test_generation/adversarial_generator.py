"""
Adversarial Test Generator with Counterfactual Reasoning.

This module implements adversarial test generation using counterfactual reasoning
to challenge rule assumptions and find edge cases.
"""

import re
import json
import random
from typing import List, Dict, Any, Optional, Tuple, Set
import numpy as np
from datetime import datetime, timedelta

from ..models.data_models import EditCheckRule, StudySpecification, TestCase, FieldType
from ..llm.llm_orchestrator import LLMOrchestrator
from ..utils.logger import Logger

logger = Logger(__name__)

class AdversarialTestGenerator:
    """Generate adversarial test cases using counterfactual reasoning."""
    
    def __init__(self, llm_orchestrator: Optional[LLMOrchestrator] = None):
        """
        Initialize the adversarial test generator.
        
        Args:
            llm_orchestrator: LLM orchestrator for generating counterfactual scenarios
        """
        self.llm_orchestrator = llm_orchestrator
        
        # Patterns for extracting comparisons
        self.comparison_pattern = re.compile(r'([A-Za-z0-9_.]+)\s*([<>=!]+)\s*([A-Za-z0-9_."\']+)')
        self.logical_op_pattern = re.compile(r'\b(AND|OR|NOT)\b', re.IGNORECASE)
        
        # Adversarial strategies
        self.strategies = [
            self._boundary_value_strategy,
            self._missing_value_strategy,
            self._type_confusion_strategy,
            self._logical_inversion_strategy,
            self._special_value_strategy
        ]
    
    def generate_adversarial_tests(self, rule: EditCheckRule, specification: StudySpecification) -> List[TestCase]:
        """
        Generate adversarial test cases using counterfactual reasoning.
        
        Args:
            rule: Rule to generate test cases for
            specification: Study specification
            
        Returns:
            List of adversarial test cases
        """
        test_cases = []
        
        # Use formalized condition if available, otherwise use original condition
        condition = rule.formalized_condition or rule.condition
        
        # Extract field references and comparisons from the condition
        field_refs, comparisons = self._extract_fields_and_comparisons(condition)
        
        # Apply each adversarial strategy
        for strategy in self.strategies:
            strategy_tests = strategy(rule, specification, field_refs, comparisons)
            test_cases.extend(strategy_tests)
        
        # If LLM is available, generate counterfactual test cases
        if self.llm_orchestrator and self.llm_orchestrator.is_available:
            counterfactual_tests = self._generate_counterfactual_tests(rule, specification)
            test_cases.extend(counterfactual_tests)
        
        logger.info(f"Generated {len(test_cases)} adversarial test cases for rule {rule.id}")
        return test_cases
    
    def _extract_fields_and_comparisons(self, condition: str) -> Tuple[Set[str], List[Tuple[str, str, str]]]:
        """
        Extract field references and comparisons from a rule condition.
        
        Args:
            condition: Rule condition
            
        Returns:
            Tuple of (set of field references, list of comparisons)
        """
        field_refs = set()
        comparisons = []
        
        # Extract comparisons
        for match in self.comparison_pattern.finditer(condition):
            left = match.group(1)
            op = match.group(2)
            right = match.group(3)
            
            # Add to field references if it's a field
            if not left.replace('.', '').isdigit() and not left.startswith('"'):
                field_refs.add(left)
            
            # Add to field references if right side is a field
            if not right.replace('.', '').isdigit() and not right.startswith('"') and not right.startswith("'"):
                field_refs.add(right)
            
            comparisons.append((left, op, right))
        
        return field_refs, comparisons
    
    def _boundary_value_strategy(
        self, 
        rule: EditCheckRule,
        specification: StudySpecification,
        field_refs: Set[str],
        comparisons: List[Tuple[str, str, str]]
    ) -> List[TestCase]:
        """
        Generate test cases using boundary value analysis.
        
        Args:
            rule: Rule to generate test cases for
            specification: Study specification
            field_refs: Set of field references
            comparisons: List of comparisons
            
        Returns:
            List of test cases
        """
        test_cases = []
        
        for left, op, right in comparisons:
            # Only consider comparisons where left is a field and right is a literal
            if left in field_refs and (right.replace('.', '').isdigit() or 
                                      right.startswith('"') or 
                                      right.startswith("'")):
                if '.' in left:
                    form_name, field_name = left.split('.', 1)
                    
                    # Get field type
                    field_type = self._get_field_type(specification, form_name, field_name)
                    
                    # For numeric fields, create boundary tests
                    if field_type in [FieldType.NUMBER, FieldType.INTEGER]:
                        try:
                            # Parse the literal
                            if right.startswith('"') or right.startswith("'"):
                                # Skip string literals
                                continue
                            
                            value = float(right)
                            
                            # Create test data with boundary values
                            boundary_values = []
                            
                            if op in ['>', '>=']:
                                # For > or >=, test exactly at the boundary and just below
                                boundary_values.append((value, op == '>='))
                                boundary_values.append((value - 0.001, False))
                            elif op in ['<', '<=']:
                                # For < or <=, test exactly at the boundary and just above
                                boundary_values.append((value, op == '<='))
                                boundary_values.append((value + 0.001, False))
                            elif op == '=':
                                # For =, test just above and just below
                                boundary_values.append((value - 0.001, False))
                                boundary_values.append((value + 0.001, False))
                            elif op == '!=':
                                # For !=, test exactly at the boundary
                                boundary_values.append((value, False))
                            
                            # Create test cases for each boundary value
                            for boundary_value, expected_result in boundary_values:
                                test_data = {form_name: {field_name: boundary_value}}
                                
                                test_case = TestCase(
                                    rule_id=rule.id,
                                    description=f"Boundary test for rule {rule.id} with {form_name}.{field_name}={boundary_value}",
                                    expected_result=expected_result,
                                    test_data=test_data,
                                    is_positive=expected_result
                                )
                                
                                test_cases.append(test_case)
                        
                        except ValueError:
                            # Not a numeric literal
                            pass
                    
                    # For date fields, create boundary tests
                    elif field_type == FieldType.DATE:
                        # Date boundary testing would go here
                        # For simplicity, we'll skip it in this implementation
                        pass
        
        return test_cases
    
    def _missing_value_strategy(
        self, 
        rule: EditCheckRule,
        specification: StudySpecification,
        field_refs: Set[str],
        comparisons: List[Tuple[str, str, str]]
    ) -> List[TestCase]:
        """
        Generate test cases with missing values.
        
        Args:
            rule: Rule to generate test cases for
            specification: Study specification
            field_refs: Set of field references
            comparisons: List of comparisons
            
        Returns:
            List of test cases
        """
        test_cases = []
        
        # For each field reference, create a test with the field missing
        for field_ref in field_refs:
            if '.' in field_ref:
                form_name, field_name = field_ref.split('.', 1)
                
                # Create test data with the field missing
                test_data = {form_name: {}}
                
                test_case = TestCase(
                    rule_id=rule.id,
                    description=f"Missing value test for rule {rule.id} with {field_ref} missing",
                    expected_result=False,  # Typically, missing values should cause the rule to fail
                    test_data=test_data,
                    is_positive=False
                )
                
                test_cases.append(test_case)
        
        return test_cases
    
    def _type_confusion_strategy(
        self, 
        rule: EditCheckRule,
        specification: StudySpecification,
        field_refs: Set[str],
        comparisons: List[Tuple[str, str, str]]
    ) -> List[TestCase]:
        """
        Generate test cases with type confusion.
        
        Args:
            rule: Rule to generate test cases for
            specification: Study specification
            field_refs: Set of field references
            comparisons: List of comparisons
            
        Returns:
            List of test cases
        """
        test_cases = []
        
        # For each field reference, create a test with an unexpected type
        for field_ref in field_refs:
            if '.' in field_ref:
                form_name, field_name = field_ref.split('.', 1)
                
                # Get field type
                field_type = self._get_field_type(specification, form_name, field_name)
                
                # Create test data with unexpected type
                unexpected_value = None
                
                if field_type == FieldType.NUMBER:
                    unexpected_value = "not_a_number"
                elif field_type == FieldType.INTEGER:
                    unexpected_value = "not_an_integer"
                elif field_type == FieldType.DATE:
                    unexpected_value = "not_a_date"
                elif field_type == FieldType.CATEGORICAL:
                    # For categorical, use a value not in the valid values
                    valid_values = self._get_valid_values(specification, form_name, field_name)
                    if valid_values:
                        unexpected_value = "invalid_category"
                else:
                    # For text, use a numeric value
                    unexpected_value = 12345
                
                if unexpected_value is not None:
                    test_data = {form_name: {field_name: unexpected_value}}
                    
                    test_case = TestCase(
                        rule_id=rule.id,
                        description=f"Type confusion test for rule {rule.id} with {field_ref}={unexpected_value}",
                        expected_result=False,  # Typically, type confusion should cause the rule to fail
                        test_data=test_data,
                        is_positive=False
                    )
                    
                    test_cases.append(test_case)
        
        return test_cases
    
    def _logical_inversion_strategy(
        self, 
        rule: EditCheckRule,
        specification: StudySpecification,
        field_refs: Set[str],
        comparisons: List[Tuple[str, str, str]]
    ) -> List[TestCase]:
        """
        Generate test cases by inverting logical conditions.
        
        Args:
            rule: Rule to generate test cases for
            specification: Study specification
            field_refs: Set of field references
            comparisons: List of comparisons
            
        Returns:
            List of test cases
        """
        test_cases = []
        
        # For each comparison, create a test that inverts the comparison
        for left, op, right in comparisons:
            if left in field_refs and (right.replace('.', '').isdigit() or 
                                      right.startswith('"') or 
                                      right.startswith("'")):
                if '.' in left:
                    form_name, field_name = left.split('.', 1)
                    
                    # Get field type
                    field_type = self._get_field_type(specification, form_name, field_name)
                    
                    # For numeric fields, invert the comparison
                    if field_type in [FieldType.NUMBER, FieldType.INTEGER]:
                        try:
                            # Parse the literal
                            if right.startswith('"') or right.startswith("'"):
                                # Skip string literals
                                continue
                            
                            value = float(right)
                            
                            # Invert the comparison
                            inverted_value = None
                            if op == '>':
                                inverted_value = value - 1  # Less than
                            elif op == '>=':
                                inverted_value = value - 1  # Less than
                            elif op == '<':
                                inverted_value = value + 1  # Greater than
                            elif op == '<=':
                                inverted_value = value + 1  # Greater than
                            elif op == '=':
                                inverted_value = value + 1  # Not equal
                            elif op == '!=':
                                inverted_value = value  # Equal
                            
                            if inverted_value is not None:
                                test_data = {form_name: {field_name: inverted_value}}
                                
                                test_case = TestCase(
                                    rule_id=rule.id,
                                    description=f"Logical inversion test for rule {rule.id} with {form_name}.{field_name}={inverted_value}",
                                    expected_result=op == '!=',  # Only != would be true when inverted
                                    test_data=test_data,
                                    is_positive=op == '!='
                                )
                                
                                test_cases.append(test_case)
                        
                        except ValueError:
                            # Not a numeric literal
                            pass
                    
                    # For categorical fields, invert the comparison
                    elif field_type == FieldType.CATEGORICAL:
                        if (right.startswith('"') and right.endswith('"')) or \
                           (right.startswith("'") and right.endswith("'")):
                            # Remove quotes
                            value = right[1:-1]
                            
                            # Get valid values
                            valid_values = self._get_valid_values(specification, form_name, field_name)
                            
                            # Choose a different value if possible
                            if valid_values and len(valid_values) > 1:
                                other_values = [v for v in valid_values if v != value]
                                if other_values:
                                    inverted_value = random.choice(other_values)
                                    
                                    test_data = {form_name: {field_name: inverted_value}}
                                    
                                    test_case = TestCase(
                                        rule_id=rule.id,
                                        description=f"Logical inversion test for rule {rule.id} with {form_name}.{field_name}={inverted_value}",
                                        expected_result=op == '!=',  # Only != would be true when inverted
                                        test_data=test_data,
                                        is_positive=op == '!='
                                    )
                                    
                                    test_cases.append(test_case)
        
        return test_cases
    
    def _special_value_strategy(
        self, 
        rule: EditCheckRule,
        specification: StudySpecification,
        field_refs: Set[str],
        comparisons: List[Tuple[str, str, str]]
    ) -> List[TestCase]:
        """
        Generate test cases with special values.
        
        Args:
            rule: Rule to generate test cases for
            specification: Study specification
            field_refs: Set of field references
            comparisons: List of comparisons
            
        Returns:
            List of test cases
        """
        test_cases = []
        
        # Special values for different field types
        special_values = {
            FieldType.NUMBER: [0, -1, float('inf'), float('-inf'), float('nan')],
            FieldType.INTEGER: [0, -1, 2**31-1, -2**31],
            FieldType.DATE: ["1900-01-01", "2100-12-31", datetime.now().strftime("%Y-%m-%d")],
            FieldType.TEXT: ["", " ", "NULL", "null", "None", "undefined"],
            FieldType.CATEGORICAL: ["", " ", "OTHER", "Unknown"]
        }
        
        # For each field reference, create tests with special values
        for field_ref in field_refs:
            if '.' in field_ref:
                form_name, field_name = field_ref.split('.', 1)
                
                # Get field type
                field_type = self._get_field_type(specification, form_name, field_name)
                
                # Get special values for this field type
                values = special_values.get(field_type, [])
                
                # Create test cases for each special value
                for value in values:
                    test_data = {form_name: {field_name: value}}
                    
                    test_case = TestCase(
                        rule_id=rule.id,
                        description=f"Special value test for rule {rule.id} with {field_ref}={value}",
                        expected_result=False,  # Typically, special values should cause the rule to fail
                        test_data=test_data,
                        is_positive=False
                    )
                    
                    test_cases.append(test_case)
        
        return test_cases
    
    def _generate_counterfactual_tests(
        self,
        rule: EditCheckRule,
        specification: StudySpecification
    ) -> List[TestCase]:
        """
        Generate counterfactual test cases using LLM.
        
        Args:
            rule: Rule to generate test cases for
            specification: Study specification
            
        Returns:
            List of counterfactual test cases
        """
        test_cases = []
        
        if not self.llm_orchestrator or not self.llm_orchestrator.is_available:
            return test_cases
        
        try:
            # Prepare context for the LLM
            context = {
                "rule_id": rule.id,
                "rule_condition": rule.formalized_condition or rule.condition,
                "rule_message": rule.message,
                "specification": self._format_specification_for_llm(specification)
            }
            
            # Prompt the LLM to generate counterfactual scenarios
            prompt = f"""
            You are an expert in clinical trial data validation. I need you to generate counterfactual test cases for the following edit check rule:
            
            Rule ID: {rule.id}
            Rule Condition: {rule.formalized_condition or rule.condition}
            Rule Message: {rule.message}
            
            Study Specification:
            {json.dumps(context['specification'], indent=2)}
            
            Please generate 3 test cases:
            1. A positive test case where the rule should pass
            2. A negative test case where the rule should fail
            3. An edge case that tests an unusual or boundary condition
            
            For each test case, provide:
            - A description of the test case
            - The expected result (true/false)
            - The test data in JSON format
            
            Format your response as valid JSON like this:
            {{
                "test_cases": [
                    {{
                        "description": "...",
                        "expected_result": true/false,
                        "test_data": {{...}}
                    }},
                    ...
                ]
            }}
            """
            
            # Call the LLM
            response = self.llm_orchestrator.generate_counterfactual_tests(prompt, context)
            
            # Parse the response
            if response and isinstance(response, str):
                try:
                    # Extract JSON from the response
                    json_start = response.find('{')
                    json_end = response.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = response[json_start:json_end]
                        data = json.loads(json_str)
                        
                        if 'test_cases' in data and isinstance(data['test_cases'], list):
                            for tc in data['test_cases']:
                                if all(k in tc for k in ['description', 'expected_result', 'test_data']):
                                    test_case = TestCase(
                                        rule_id=rule.id,
                                        description=tc['description'],
                                        expected_result=tc['expected_result'],
                                        test_data=tc['test_data'],
                                        is_positive=tc['expected_result']
                                    )
                                    
                                    test_cases.append(test_case)
                
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Error parsing LLM response: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error generating counterfactual tests: {str(e)}")
        
        return test_cases
    
    def _format_specification_for_llm(self, specification: StudySpecification) -> Dict[str, Any]:
        """
        Format the study specification for the LLM.
        
        Args:
            specification: Study specification
            
        Returns:
            Formatted specification
        """
        formatted_spec = {
            "forms": {}
        }
        
        # Format each form and its fields
        for form_name, fields in specification.forms.items():
            formatted_spec["forms"][form_name] = {
                "fields": {}
            }
            
            for field_name, field in fields.items():
                formatted_spec["forms"][form_name]["fields"][field_name] = {
                    "type": str(field.type),
                    "label": field.label,
                    "valid_values": field.valid_values.split(',') if field.valid_values else []
                }
        
        return formatted_spec
    
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
