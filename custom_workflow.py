#!/usr/bin/env python3
"""
Custom Workflow for the Eclaire Trials Edit Check Rule Validation System.

This script implements a simplified workflow that performs the same steps as the LangGraph workflow
but without the dependency on LangGraph, making it more compatible with different environments.
"""

import os
import json
import time
import logging
from typing import Dict, List, Any, Optional

from src.models.data_models import EditCheckRule, StudySpecification, ValidationResult, TestCase
from src.parsers.unified_parser import UnifiedParser
from src.validators.rule_validator import RuleValidator
from src.validators.z3_verifier import Z3Verifier
from src.llm.llm_orchestrator import LLMOrchestrator
from src.test_generation.test_generator import TestGenerator
from src.utils.logger import Logger

# Configure logging
logger = Logger(__name__)

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
            "rules": [],
            "validation_results": [],
            "test_cases": [],
            "errors": [],
            "metrics": {
                "total_time": 0,
                "parsing_time": 0,
                "formalization_time": 0,
                "verification_time": 0,
                "test_generation_time": 0
            }
        }
        
        logger.info(f"Starting validation workflow for rules: {rules_file}, spec: {spec_file}")
        
        try:
            # Step 1: Parse files
            parse_start = time.time()
            result = self._parse_files(rules_file, spec_file, result)
            parse_end = time.time()
            result["metrics"]["parsing_time"] = parse_end - parse_start
            
            if result["status"] == "failed":
                logger.error("Parsing failed, aborting workflow")
                return self._finalize_result(result, start_time)
            
            # Step 2: Validate rules
            result = self._validate_rules(result)
            
            if result["status"] == "failed":
                logger.error("Validation failed, aborting workflow")
                return self._finalize_result(result, start_time)
            
            # Step 3: Formalize rules (if configured)
            if self.config["formalize_rules"]:
                formalize_start = time.time()
                result = self._formalize_rules(result)
                formalize_end = time.time()
                result["metrics"]["formalization_time"] = formalize_end - formalize_start
                
                if result["status"] == "failed":
                    logger.error("Formalization failed, aborting workflow")
                    return self._finalize_result(result, start_time)
            
            # Step 4: Verify rules (if configured)
            if self.config["verify_with_z3"]:
                verify_start = time.time()
                result = self._verify_rules(result)
                verify_end = time.time()
                result["metrics"]["verification_time"] = verify_end - verify_start
                
                if result["status"] == "failed":
                    logger.error("Verification failed, aborting workflow")
                    return self._finalize_result(result, start_time)
            
            # Step 5: Generate tests (if configured)
            if self.config["generate_tests"]:
                test_gen_start = time.time()
                result = self._generate_tests(result)
                test_gen_end = time.time()
                result["metrics"]["test_generation_time"] = test_gen_end - test_gen_start
            
            # Mark as successful
            result["status"] = "completed"
            logger.info("Workflow completed successfully")
            
        except Exception as e:
            logger.error(f"Workflow failed: {str(e)}")
            result["status"] = "failed"
            result["errors"].append({
                "error_type": "workflow_failure",
                "message": f"Workflow failed: {str(e)}",
                "exception": str(e)
            })
        
        # Finalize and return result
        return self._finalize_result(result, start_time)
    
    def _parse_files(self, rules_file: str, spec_file: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the rules and specification files."""
        try:
            # Parse rules
            logger.info(f"Parsing rules from {rules_file}")
            rules, rule_errors = self.parser.parse_file(rules_file, "rules")
            
            if rule_errors:
                for error in rule_errors:
                    result["errors"].append(error)
                if not rules:
                    raise Exception(f"Failed to parse rules file: {rule_errors[0]['message']}")
            
            result["rules"] = [rule.to_dict() for rule in rules]
            logger.info(f"Successfully parsed {len(rules)} rules")
            
            # Parse specification
            logger.info(f"Parsing specification from {spec_file}")
            specification, spec_errors = self.parser.parse_file(spec_file, "specification")
            
            if spec_errors:
                for error in spec_errors:
                    result["errors"].append(error)
                if not specification:
                    raise Exception(f"Failed to parse specification file: {spec_errors[0]['message']}")
            
            result["specification"] = specification.to_dict() if specification else None
            logger.info(f"Successfully parsed specification with {len(specification.forms) if specification else 0} forms")
            
            # Store the objects for later use
            result["_rules_objects"] = rules
            result["_specification_object"] = specification
            
            return result
        except Exception as e:
            logger.error(f"Error parsing files: {str(e)}")
            result["status"] = "failed"
            result["errors"].append({
                "error_type": "parsing_failure",
                "message": f"Failed to parse files: {str(e)}",
                "exception": str(e)
            })
            return result
    
    def _validate_rules(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the rules against the specification."""
        try:
            rules = result["_rules_objects"]
            specification = result["_specification_object"]
            
            logger.info(f"Validating {len(rules)} rules against specification")
            validation_results = self.validator.validate_rules(rules, specification)
            result["validation_results"] = [vr.to_dict() for vr in validation_results]
            
            # Check if all rules are valid
            all_valid = all(vr.is_valid for vr in validation_results)
            if not all_valid:
                logger.warning(f"Some rules failed validation")
                invalid_count = sum(1 for vr in validation_results if not vr.is_valid)
                logger.warning(f"{invalid_count} out of {len(rules)} rules are invalid")
            
            return result
        except Exception as e:
            logger.error(f"Error validating rules: {str(e)}")
            result["status"] = "failed"
            result["errors"].append({
                "error_type": "validation_failure",
                "message": f"Failed to validate rules: {str(e)}",
                "exception": str(e)
            })
            return result
    
    def _formalize_rules(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Formalize the rules using LLM."""
        try:
            rules = result["_rules_objects"]
            
            if not self.llm_orchestrator.is_available:
                logger.warning("LLM is not available. Skipping rule formalization.")
                return result
            
            logger.info(f"Formalizing {len(rules)} rules using LLM")
            
            # Formalize each rule
            for i, rule in enumerate(rules):
                logger.info(f"Formalizing rule {rule.id} ({i+1}/{len(rules)})")
                formalized_rule = self.llm_orchestrator.formalize_rule(rule)
                
                # Update the rule in the list
                rules[i] = formalized_rule
            
            # Update the result with formalized rules
            result["_rules_objects"] = rules
            result["rules"] = [rule.to_dict() for rule in rules]
            
            return result
        except Exception as e:
            logger.error(f"Error formalizing rules: {str(e)}")
            result["errors"].append({
                "error_type": "formalization_failure",
                "message": f"Failed to formalize rules: {str(e)}",
                "exception": str(e)
            })
            # Don't fail the workflow, continue with unformalized rules
            return result
    
    def _verify_rules(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Verify the rules using Z3."""
        try:
            rules = result["_rules_objects"]
            specification = result["_specification_object"]
            
            logger.info(f"Verifying {len(rules)} rules using Z3")
            
            # Verify each rule
            verified_rules = []
            for i, rule in enumerate(rules):
                logger.info(f"Verifying rule {rule.id} ({i+1}/{len(rules)})")
                
                # Skip rules without formalized condition
                if not rule.formalized_condition:
                    logger.warning(f"Rule {rule.id} has no formalized condition. Skipping verification.")
                    verified_rules.append(rule)
                    continue
                
                # Verify the rule
                verified_rule = self.verifier.verify_rule(rule, specification)
                verified_rules.append(verified_rule)
            
            # Update the result with verified rules
            result["_rules_objects"] = verified_rules
            result["rules"] = [rule.to_dict() for rule in verified_rules]
            
            return result
        except Exception as e:
            logger.error(f"Error verifying rules: {str(e)}")
            result["errors"].append({
                "error_type": "verification_failure",
                "message": f"Failed to verify rules: {str(e)}",
                "exception": str(e)
            })
            # Don't fail the workflow, continue with unverified rules
            return result
    
    def _generate_tests(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test cases for the rules."""
        try:
            rules = result["_rules_objects"]
            specification = result["_specification_object"]
            
            # Filter rules that are valid for test generation
            valid_rules = [rule for rule in rules if rule.formalized_condition]
            
            if not valid_rules:
                logger.warning("No valid rules for test generation")
                return result
            
            logger.info(f"Generating test cases for {len(valid_rules)} rules")
            
            # Generate test cases using advanced techniques
            all_test_cases = []
            for i, rule in enumerate(valid_rules):
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
            
            # If no test cases were generated, try LLM-based generation
            if not all_test_cases and self.llm_orchestrator.is_available:
                logger.warning("Advanced test generation produced no tests. Falling back to LLM-based generation.")
                for i, rule in enumerate(valid_rules):
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
            
            # Update the result with test cases
            result["test_cases"] = [tc.to_dict() for tc in all_test_cases]
            result["_test_case_objects"] = all_test_cases
            
            return result
        except Exception as e:
            logger.error(f"Error generating test cases: {str(e)}")
            result["errors"].append({
                "error_type": "test_generation_failure",
                "message": f"Failed to generate test cases: {str(e)}",
                "exception": str(e)
            })
            # Don't fail the workflow, continue without test cases
            return result
    
    def _finalize_result(self, result: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Finalize the result and export to JSON."""
        # Calculate total time
        end_time = time.time()
        result["metrics"]["total_time"] = end_time - start_time
        
        # Remove internal objects before export
        clean_result = {k: v for k, v in result.items() if not k.startswith("_")}
        
        # Export to JSON
        output_file = self.config["output_file"]
        with open(output_file, "w") as f:
            json.dump(clean_result, f, indent=2)
        
        logger.info(f"Results exported to {output_file}")
        
        return result


def main():
    """Main entry point for the custom workflow."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run the Edit Check Rule Validation workflow")
    parser.add_argument("--rules", required=True, help="Path to the rules Excel file")
    parser.add_argument("--spec", required=True, help="Path to the specification Excel file")
    parser.add_argument("--output", default="workflow_results.json", help="Path to the output JSON file")
    parser.add_argument("--no-formalize", action="store_true", help="Skip rule formalization")
    parser.add_argument("--no-verify", action="store_true", help="Skip rule verification")
    parser.add_argument("--no-tests", action="store_true", help="Skip test generation")
    args = parser.parse_args()
    
    # Configure the workflow
    config = {
        "formalize_rules": not args.no_formalize,
        "verify_with_z3": not args.no_verify,
        "generate_tests": not args.no_tests,
        "output_file": args.output
    }
    
    # Create and run the workflow
    workflow = CustomWorkflow(config)
    result = workflow.run(args.rules, args.spec)
    
    # Print summary
    print("\n=== WORKFLOW SUMMARY ===")
    print(f"Status: {result['status']}")
    print(f"Rules: {len(result['rules'])}")
    print(f"Validation Results: {len(result['validation_results'])}")
    print(f"Test Cases: {len(result['test_cases'])}")
    print(f"Errors: {len(result['errors'])}")
    print(f"Total Time: {result['metrics']['total_time']:.2f} seconds")
    print(f"Results exported to: {args.output}")
    
    # Return success if workflow completed
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    exit(main())
