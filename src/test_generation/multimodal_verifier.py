"""
Multi-Modal Verification module for Edit Check Rule Validation System.

This module implements multi-modal verification techniques to validate test cases
using multiple complementary approaches.
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple, Set
import numpy as np
from datetime import datetime, timedelta

from ..models.data_models import EditCheckRule, StudySpecification, TestCase, ValidationResult
from ..validators.z3_verifier import Z3Verifier
from ..utils.logger import Logger

logger = Logger(__name__)

class MultiModalVerifier:
    """Verify test cases using multiple complementary approaches."""
    
    def __init__(self, z3_verifier: Optional[Z3Verifier] = None):
        """
        Initialize the multi-modal verifier.
        
        Args:
            z3_verifier: Z3 verifier for formal verification
        """
        self.z3_verifier = z3_verifier or Z3Verifier()
        
        # Verification modes
        self.verification_modes = [
            self._verify_with_z3,
            self._verify_with_direct_evaluation,
            self._verify_with_cross_validation
        ]
    
    def verify_test_cases(
        self,
        rule: EditCheckRule,
        specification: StudySpecification,
        test_cases: List[TestCase]
    ) -> List[Tuple[TestCase, ValidationResult]]:
        """
        Verify test cases using multiple verification modes.
        
        Args:
            rule: The rule to verify
            specification: The study specification
            test_cases: List of test cases to verify
            
        Returns:
            List of (test case, validation result) tuples
        """
        verification_results = []
        
        for test_case in test_cases:
            # Apply each verification mode
            mode_results = []
            for verification_mode in self.verification_modes:
                result = verification_mode(rule, specification, test_case)
                if result:
                    mode_results.append(result)
            
            # Combine results from all modes
            combined_result = self._combine_verification_results(mode_results)
            verification_results.append((test_case, combined_result))
        
        return verification_results
    
    def _verify_with_z3(
        self,
        rule: EditCheckRule,
        specification: StudySpecification,
        test_case: TestCase
    ) -> Optional[ValidationResult]:
        """
        Verify a test case using Z3 formal verification.
        
        Args:
            rule: The rule to verify
            specification: The study specification
            test_case: The test case to verify
            
        Returns:
            Validation result or None if verification fails
        """
        try:
            # Use Z3 verifier to check the test case
            result = self.z3_verifier.verify_test_case(rule, specification, test_case)
            
            if result:
                return ValidationResult(
                    rule_id=rule.id,
                    is_valid=result.is_valid,
                    message=f"Z3 verification: {result.message}",
                    details={
                        "verification_method": "z3",
                        "original_result": result.details
                    }
                )
            
            return None
        
        except Exception as e:
            logger.error(f"Error in Z3 verification: {str(e)}")
            return None
    
    def _verify_with_direct_evaluation(
        self,
        rule: EditCheckRule,
        specification: StudySpecification,
        test_case: TestCase
    ) -> Optional[ValidationResult]:
        """
        Verify a test case using direct evaluation of the rule condition.
        
        Args:
            rule: The rule to verify
            specification: The study specification
            test_case: The test case to verify
            
        Returns:
            Validation result or None if verification fails
        """
        try:
            # Use formalized condition if available, otherwise use original condition
            condition = rule.formalized_condition or rule.condition
            
            # Evaluate the condition with the test data
            evaluation_result = self._evaluate_condition(condition, test_case.test_data)
            
            if evaluation_result is not None:
                is_valid = evaluation_result == test_case.expected_result
                
                return ValidationResult(
                    rule_id=rule.id,
                    is_valid=is_valid,
                    message=f"Direct evaluation: {'passed' if is_valid else 'failed'}",
                    details={
                        "verification_method": "direct_evaluation",
                        "condition_result": evaluation_result,
                        "expected_result": test_case.expected_result
                    }
                )
            
            return None
        
        except Exception as e:
            logger.error(f"Error in direct evaluation: {str(e)}")
            return None
    
    def _verify_with_cross_validation(
        self,
        rule: EditCheckRule,
        specification: StudySpecification,
        test_case: TestCase
    ) -> Optional[ValidationResult]:
        """
        Verify a test case using cross-validation with related rules.
        
        Args:
            rule: The rule to verify
            specification: The study specification
            test_case: The test case to verify
            
        Returns:
            Validation result or None if verification fails
        """
        # This is a placeholder for cross-validation logic
        # In a real implementation, you would:
        # 1. Identify related rules (e.g., rules that reference the same fields)
        # 2. Check if the test case is consistent with those rules
        # 3. Return a validation result based on the consistency check
        
        # For now, we'll return None to indicate that this verification mode is not implemented
        return None
    
    def _evaluate_condition(self, condition: str, test_data: Dict[str, Dict[str, Any]]) -> Optional[bool]:
        """
        Evaluate a rule condition with test data.
        
        Args:
            condition: Rule condition
            test_data: Test data
            
        Returns:
            Evaluation result or None if evaluation fails
        """
        try:
            # Replace field references with values from test data
            eval_condition = condition
            
            # Find all field references in the condition
            field_pattern = re.compile(r'([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)')
            for match in field_pattern.finditer(condition):
                form_name = match.group(1)
                field_name = match.group(2)
                
                # Check if the field exists in the test data
                if form_name in test_data and field_name in test_data[form_name]:
                    field_value = test_data[form_name][field_name]
                    
                    # Format the value based on its type
                    if isinstance(field_value, str):
                        formatted_value = f'"{field_value}"'
                    elif isinstance(field_value, (int, float)):
                        formatted_value = str(field_value)
                    elif field_value is None:
                        formatted_value = 'None'
                    else:
                        formatted_value = str(field_value)
                    
                    # Replace the field reference with the value
                    eval_condition = eval_condition.replace(
                        f'{form_name}.{field_name}',
                        formatted_value
                    )
                else:
                    # Field is missing, replace with None
                    eval_condition = eval_condition.replace(
                        f'{form_name}.{field_name}',
                        'None'
                    )
            
            # Replace logical operators
            eval_condition = eval_condition.replace('AND', 'and')
            eval_condition = eval_condition.replace('OR', 'or')
            eval_condition = eval_condition.replace('NOT', 'not')
            
            # Evaluate the condition
            # Note: This is a simplified approach and has security implications in a real system
            # In a production system, you would use a safer evaluation method
            result = eval(eval_condition)
            
            return bool(result)
        
        except Exception as e:
            logger.error(f"Error evaluating condition: {str(e)}")
            return None
    
    def _combine_verification_results(self, results: List[ValidationResult]) -> ValidationResult:
        """
        Combine results from multiple verification modes.
        
        Args:
            results: List of validation results
            
        Returns:
            Combined validation result
        """
        if not results:
            return ValidationResult(
                rule_id="unknown",
                is_valid=False,
                message="No verification results available",
                details={}
            )
        
        # Count valid and invalid results
        valid_count = sum(1 for r in results if r.is_valid)
        invalid_count = len(results) - valid_count
        
        # Determine overall validity (majority vote)
        is_valid = valid_count > invalid_count
        
        # Combine messages
        messages = [r.message for r in results]
        combined_message = f"Combined verification ({valid_count}/{len(results)} passed): {'; '.join(messages)}"
        
        # Combine details
        combined_details = {
            "verification_methods": [r.details.get("verification_method", "unknown") for r in results],
            "individual_results": [
                {
                    "is_valid": r.is_valid,
                    "message": r.message,
                    "details": r.details
                }
                for r in results
            ]
        }
        
        return ValidationResult(
            rule_id=results[0].rule_id,
            is_valid=is_valid,
            message=combined_message,
            details=combined_details
        )
