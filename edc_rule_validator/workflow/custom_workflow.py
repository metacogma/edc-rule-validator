#!/usr/bin/env python3
"""
Custom Workflow for the Eclaire Trials Edit Check Rule Validation System.

This module provides a production-grade implementation of the validation workflow
that can be used both as a standalone script and as a library for API integration.
"""

import os
import sys
import time
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import asdict, is_dataclass

# Add parent directory to path to import from src
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from src.parsers.unified_parser import UnifiedParser
from src.validators.rule_validator import RuleValidator
from src.verifiers.z3_verifier import Z3Verifier
from src.llm.llm_orchestrator import LLMOrchestrator
from src.test_generation.test_generator import TestGenerator
from src.models.data_models import EditCheckRule, StudySpecification, ValidationResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class CustomWorkflow:
    """Custom workflow for the Edit Check Rule Validation System."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the custom workflow.
        
        Args:
            config: Optional configuration dictionary
        """
        self.parser = UnifiedParser()
        self.validator = RuleValidator()
        self.verifier = Z3Verifier()
        self.llm_orchestrator = LLMOrchestrator()
        self.test_generator = TestGenerator(self.llm_orchestrator)
        
        # Default configuration
        self.config = {
            "formalize_rules": True,
            "verify_with_z3": True,
            "generate_tests": True,
            "test_techniques": ["metamorphic", "symbolic", "adversarial", "causal"],
            "test_cases_per_rule": 5,
            "parallel_test_generation": True,
            "max_retries": 3,
            "output_file": "workflow_results.json"
        }
        
        # Update with provided config
        if config:
            self.config.update(config)
    
    def run(self, rules_file: str, spec_file: str) -> Dict[str, Any]:
        """
        Run the validation workflow.
        
        Args:
            rules_file: Path to the rules file
            spec_file: Path to the specification file
            
        Returns:
            Dictionary with workflow results
        """
        start_time = time.time()
        
        # Initialize result dictionary
        result = {
            "status": "running",
            "rules_file": rules_file,
            "spec_file": spec_file,
            "config": self.config,
            "start_time": start_time,
        }
        
        try:
            # Step 1: Parse files
            self._parse_files(rules_file, spec_file, result)
            
            # Step 2: Validate rules
            self._validate_rules(result)
            
            # Step 3: Formalize rules (if enabled)
            if self.config["formalize_rules"]:
                self._formalize_rules(result)
            
            # Step 4: Verify rules with Z3 (if enabled)
            if self.config["verify_with_z3"]:
                self._verify_rules(result)
            
            # Step 5: Generate test cases (if enabled)
            if self.config["generate_tests"]:
                self._generate_tests(result)
            
            # Step 6: Finalize result
            return self._finalize_result(result, start_time)
            
        except Exception as e:
            logger.error(f"Error in workflow: {str(e)}")
            result["status"] = "error"
            result["error"] = str(e)
            return self._finalize_result(result, start_time)
    
    def _parse_files(self, rules_file: str, spec_file: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the rules and specification files."""
        try:
            # Parse rules
            logger.info(f"Parsing rules from {rules_file}")
            rules, rule_errors = self.parser.parse_file(rules_file, "rules")
            
            if not rules:
                raise ValueError(f"Failed to parse rules from {rules_file}")
            
            logger.info(f"Successfully parsed {len(rules)} rules")
            
            # Parse specification
            logger.info(f"Parsing specification from {spec_file}")
            specification, spec_errors = self.parser.parse_file(spec_file, "specification")
            
            if not specification:
                raise ValueError(f"Failed to parse specification from {spec_file}")
            
            logger.info(f"Successfully parsed specification with {len(specification.forms)} forms")
            
            # Update result
            result["rules"] = self._serialize_objects(rules)
            result["_rules_objects"] = rules
            result["specification"] = self._serialize_object(specification)
            result["_specification_object"] = specification
            result["parsing_errors"] = rule_errors + spec_errors
            
            return result
        except Exception as e:
            logger.error(f"Error parsing files: {str(e)}")
            raise
    
    def _validate_rules(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the rules against the specification."""
        try:
            rules = result["_rules_objects"]
            specification = result["_specification_object"]
            
            logger.info(f"Validating {len(rules)} rules against specification")
            
            # Validate each rule
            validation_results = []
            invalid_count = 0
            
            for rule in rules:
                validation_result = self.validator.validate_rule(rule, specification)
                validation_results.append(validation_result)
                
                if not validation_result.is_valid:
                    invalid_count += 1
                    logger.warning(f"Rule {rule.id} failed validation with {len(validation_result.errors)} errors")
                else:
                    logger.info(f"Rule {rule.id} passed validation")
            
            if invalid_count > 0:
                logger.warning(f"Some rules failed validation")
                logger.warning(f"{invalid_count} out of {len(rules)} rules are invalid")
            
            # Update result
            result["validation_results"] = self._serialize_objects(validation_results)
            result["_validation_results_objects"] = validation_results
            
            return result
        except Exception as e:
            logger.error(f"Error validating rules: {str(e)}")
            raise
    
    def _formalize_rules(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Formalize the rules using LLM."""
        try:
            rules = result["_rules_objects"]
            specification = result["_specification_object"]
            
            logger.info(f"Formalizing {len(rules)} rules using LLM")
            
            # Formalize each rule
            for i, rule in enumerate(rules):
                try:
                    logger.info(f"Formalizing rule {rule.id} ({i+1}/{len(rules)})")
                    
                    # Skip rules that failed validation
                    validation_results = result["_validation_results_objects"]
                    validation_result = next((vr for vr in validation_results if vr.rule_id == rule.id), None)
                    
                    if validation_result and not validation_result.is_valid:
                        logger.warning(f"Skipping formalization for invalid rule {rule.id}")
                        continue
                    
                    # Formalize rule
                    formalized_condition = self.llm_orchestrator.formalize_rule(rule, specification)
                    
                    if formalized_condition:
                        rule.formalized_condition = formalized_condition
                        logger.info(f"Successfully formalized rule {rule.id}")
                    else:
                        logger.warning(f"Failed to formalize rule {rule.id}")
                except Exception as e:
                    logger.error(f"Error formalizing rule {rule.id}: {str(e)}")
            
            # Update result
            result["rules"] = self._serialize_objects(rules)
            
            return result
        except Exception as e:
            logger.error(f"Error formalizing rules: {str(e)}")
            result["formalization_error"] = str(e)
            return result
    
    def _verify_rules(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Verify the rules using Z3."""
        try:
            rules = result["_rules_objects"]
            specification = result["_specification_object"]
            
            logger.info(f"Verifying {len(rules)} rules using Z3")
            
            # Filter rules that have formalized conditions
            formalized_rules = [rule for rule in rules if hasattr(rule, 'formalized_condition') and rule.formalized_condition]
            
            if not formalized_rules:
                logger.warning("No formalized rules to verify")
                return result
            
            # Verify each rule
            verification_results = []
            
            for i, rule in enumerate(formalized_rules):
                try:
                    logger.info(f"Verifying rule {rule.id} ({i+1}/{len(formalized_rules)})")
                    
                    # Verify rule
                    verification_result = self.verifier.verify_rule(rule, specification)
                    verification_results.append(verification_result)
                    
                    if verification_result["is_valid"]:
                        logger.info(f"Rule {rule.id} passed verification")
                    else:
                        logger.warning(f"Rule {rule.id} failed verification: {verification_result['reason']}")
                except Exception as e:
                    logger.error(f"Error verifying rule {rule.id}: {str(e)}")
                    verification_results.append({
                        "rule_id": rule.id,
                        "is_valid": False,
                        "reason": f"Error during verification: {str(e)}"
                    })
            
            # Update result
            result["verification_results"] = verification_results
            
            return result
        except Exception as e:
            logger.error(f"Error verifying rules: {str(e)}")
            result["verification_error"] = str(e)
            return result
    
    def _generate_tests(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test cases for the rules."""
        try:
            rules = result["_rules_objects"]
            specification = result["_specification_object"]
            
            # Filter rules that are valid for test generation
            valid_rules = [rule for rule in rules if hasattr(rule, 'formalized_condition') and rule.formalized_condition]
            
            if not valid_rules:
                logger.warning("No valid rules for test generation")
                return result
            
            logger.info(f"Generating test cases for {len(valid_rules)} rules")
            
            # Generate test cases using advanced techniques
            all_test_cases = []
            for i, rule in enumerate(valid_rules):
                try:
                    logger.info(f"Generating test cases for rule {rule.id} ({i+1}/{len(valid_rules)})")
                    
                    # Generate test cases
                    test_cases = self.test_generator.generate_tests(
                        rule, 
                        specification,
                        self.config["test_techniques"],
                        self.config["test_cases_per_rule"]
                    )
                    
                    all_test_cases.extend(test_cases)
                    logger.info(f"Generated {len(test_cases)} test cases for rule {rule.id}")
                except Exception as e:
                    logger.error(f"Error generating test cases for rule {rule.id}: {str(e)}")
            
            # If no test cases were generated, try LLM-based generation
            if not all_test_cases and self.llm_orchestrator.is_available:
                try:
                    logger.warning("Advanced test generation produced no tests. Falling back to LLM-based generation.")
                    for i, rule in enumerate(valid_rules):
                        try:
                            logger.info(f"Generating LLM test cases for rule {rule.id} ({i+1}/{len(valid_rules)})")
                            
                            # Generate test cases
                            test_cases = self.llm_orchestrator.generate_test_cases(
                                rule, 
                                specification,
                                self.config["test_cases_per_rule"]
                            )
                            
                            # Add a marker to indicate these are LLM-generated tests
                            for test in test_cases:
                                test.description = f"[LLM] {test.description}"
                            
                            all_test_cases.extend(test_cases)
                            logger.info(f"Generated {len(test_cases)} LLM test cases for rule {rule.id}")
                        except Exception as e:
                            logger.error(f"Error generating LLM test cases for rule {rule.id}: {str(e)}")
                except Exception as e:
                    logger.error(f"Error in LLM fallback test generation: {str(e)}")
            
            # Update the result with test cases
            if all_test_cases:
                # Convert test cases to dictionaries manually
                test_cases_dicts = []
                for tc in all_test_cases:
                    tc_dict = {
                        "rule_id": tc.rule_id,
                        "description": tc.description,
                        "expected_result": tc.expected_result,
                        "test_data": tc.test_data,
                        "is_positive": tc.is_positive
                    }
                    test_cases_dicts.append(tc_dict)
                    
                result["test_cases"] = test_cases_dicts
                result["_test_case_objects"] = all_test_cases
            
            return result
        except Exception as e:
            logger.error(f"Error generating tests: {str(e)}")
            result["test_generation_error"] = str(e)
            return result
    
    def _finalize_result(self, result: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Finalize the result and export to JSON."""
        try:
            # Calculate total time
            end_time = time.time()
            total_time = end_time - start_time
            
            # Add summary information
            result["end_time"] = end_time
            result["total_time"] = total_time
            
            if "status" not in result:
                result["status"] = "completed"
            
            # Remove internal objects
            result_export = {k: v for k, v in result.items() if not k.startswith("_")}
            
            # Export to JSON
            if self.config["output_file"]:
                with open(self.config["output_file"], "w") as f:
                    json.dump(result_export, f, indent=2)
                logger.info(f"Results exported to {self.config['output_file']}")
            
            # Print summary
            print("\n=== WORKFLOW SUMMARY ===")
            print(f"Status: {result['status']}")
            print(f"Rules: {len(result.get('rules', []))}")
            print(f"Validation Results: {len(result.get('validation_results', []))}")
            print(f"Test Cases: {len(result.get('test_cases', []))}")
            print(f"Errors: {len([e for e in result.keys() if e.endswith('_error')])}")
            print(f"Total Time: {total_time:.2f} seconds")
            
            if self.config["output_file"]:
                print(f"Results exported to: {self.config['output_file']}")
            
            return result_export
        except Exception as e:
            logger.error(f"Error finalizing result: {str(e)}")
            return {
                "status": "error",
                "error": f"Error finalizing result: {str(e)}",
                "total_time": time.time() - start_time
            }
    
    def _serialize_objects(self, objects: List[Any]) -> List[Dict[str, Any]]:
        """Serialize a list of objects to dictionaries."""
        return [self._serialize_object(obj) for obj in objects]
    
    def _serialize_object(self, obj: Any) -> Dict[str, Any]:
        """Serialize an object to a dictionary."""
        if obj is None:
            return None
        
        # Handle dataclasses
        if is_dataclass(obj):
            return asdict(obj)
        
        # Handle objects with to_dict method
        if hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
            return obj.to_dict()
        
        # Handle EditCheckRule
        if isinstance(obj, EditCheckRule):
            return {
                "id": obj.id,
                "condition": obj.condition,
                "message": obj.message,
                "severity": str(obj.severity),
                "forms": obj.forms,
                "fields": obj.fields,
                "formalized_condition": obj.formalized_condition
            }
        
        # Handle StudySpecification
        if isinstance(obj, StudySpecification):
            return {
                "forms": [self._serialize_object(form) for form in obj.forms],
                "fields": [self._serialize_object(field) for field in obj.fields]
            }
        
        # Handle ValidationResult
        if isinstance(obj, ValidationResult):
            return {
                "rule_id": obj.rule_id,
                "is_valid": obj.is_valid,
                "errors": obj.errors,
                "warnings": obj.warnings
            }
        
        # Handle dictionaries
        if isinstance(obj, dict):
            return obj
        
        # Handle other objects
        return str(obj)
