#!/usr/bin/env python
"""
Run the Edit Check Rule Validation workflow end-to-end with JSON data files.

This script demonstrates the full workflow from parsing to test generation
using the provided JSON rule and specification files with updated LLM orchestrator.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the updated LLM orchestrator
from src.llm.llm_orchestrator_updated import LLMOrchestrator
from src.utils.logger import Logger
from src.models.data_models import EditCheckRule, StudySpecification, TestCase
from src.parsers.json_rule_parser import JSONRuleParser
from src.parsers.json_specification_parser import JSONSpecificationParser
from src.test_generation.test_generator import TestGenerator
from src.verification.rule_verifier import RuleVerifier

# Set up logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = Logger(__name__)

class WorkflowResult:
    """Class to store workflow results."""
    
    def __init__(self):
        self.status = "pending"
        self.current_step = "initialization"
        self.rules = []
        self.specification = None
        self.test_cases = []
        self.errors = []

def run_workflow(rules_file, spec_file, config):
    """Run the workflow end-to-end."""
    result = WorkflowResult()
    
    try:
        # Step 1: Parse rules
        result.current_step = "parsing_rules"
        logger.info("Parsing rules...")
        rule_parser = JSONRuleParser()
        rules = rule_parser.parse(rules_file)
        result.rules = rules
        logger.info(f"Parsed {len(rules)} rules")
        
        # Step 2: Parse specification
        result.current_step = "parsing_specification"
        logger.info("Parsing specification...")
        spec_parser = JSONSpecificationParser()
        specification = spec_parser.parse(spec_file)
        result.specification = specification
        logger.info(f"Parsed specification with {len(specification.forms)} forms")
        
        # Step 3: Formalize rules with LLM
        if config.get("formalize_rules", False):
            result.current_step = "formalizing_rules"
            logger.info("Formalizing rules with LLM...")
            llm_orchestrator = LLMOrchestrator()
            
            if llm_orchestrator.is_available:
                for rule in rules:
                    try:
                        formalized_condition = llm_orchestrator.formalize_rule(rule, specification)
                        if formalized_condition:
                            setattr(rule, 'formalized_condition', formalized_condition)
                            logger.info(f"Formalized rule {rule.id}")
                        else:
                            logger.warning(f"Failed to formalize rule {rule.id}")
                    except Exception as e:
                        error = {
                            "error_type": "formalization_error",
                            "rule_id": rule.id,
                            "message": str(e)
                        }
                        result.errors.append(error)
                        logger.error(f"Error formalizing rule {rule.id}: {str(e)}")
            else:
                logger.warning("LLM is not available. Skipping rule formalization.")
        
        # Step 4: Verify rules with Z3
        if config.get("verify_with_z3", False):
            result.current_step = "verifying_rules"
            logger.info("Verifying rules with Z3...")
            verifier = RuleVerifier()
            
            for rule in rules:
                if hasattr(rule, 'formalized_condition') and rule.formalized_condition:
                    try:
                        verification_result = verifier.verify(rule, specification)
                        setattr(rule, 'verification_result', verification_result)
                        logger.info(f"Verified rule {rule.id}: {verification_result.status}")
                        
                        if verification_result.errors:
                            for error in verification_result.errors:
                                logger.warning(f"Verification issue for rule {rule.id}: {error}")
                    except Exception as e:
                        error = {
                            "error_type": "verification_error",
                            "rule_id": rule.id,
                            "message": str(e)
                        }
                        result.errors.append(error)
                        logger.error(f"Error verifying rule {rule.id}: {str(e)}")
        
        # Step 5: Generate test cases
        if config.get("generate_tests", False):
            result.current_step = "generating_tests"
            logger.info("Generating test cases...")
            
            # Configure test generator
            test_techniques = config.get("test_techniques", ["basic"])
            parallel = config.get("parallel_test_generation", False)
            test_generator = TestGenerator()
            
            # Generate test cases
            try:
                test_cases = test_generator.generate_tests(
                    rules, 
                    specification, 
                    parallel=parallel, 
                    techniques=test_techniques
                )
                result.test_cases = test_cases
                logger.info(f"Generated {len(test_cases)} test cases")
                
                # Add LLM-based test cases if available
                if "llm" in test_techniques and llm_orchestrator.is_available:
                    logger.info("Generating additional LLM-based test cases...")
                    llm_test_cases = []
                    
                    for rule in rules:
                        try:
                            rule_test_cases = llm_orchestrator.generate_test_cases(
                                rule, 
                                specification, 
                                num_cases=config.get("test_cases_per_rule", 3)
                            )
                            llm_test_cases.extend(rule_test_cases)
                            logger.info(f"Generated {len(rule_test_cases)} LLM-based test cases for rule {rule.id}")
                        except Exception as e:
                            error = {
                                "error_type": "llm_test_generation_error",
                                "rule_id": rule.id,
                                "message": str(e)
                            }
                            result.errors.append(error)
                            logger.error(f"Error generating LLM-based test cases for rule {rule.id}: {str(e)}")
                    
                    result.test_cases.extend(llm_test_cases)
                    logger.info(f"Added {len(llm_test_cases)} LLM-based test cases")
            
            except Exception as e:
                error = {
                    "error_type": "test_generation_error",
                    "message": str(e)
                }
                result.errors.append(error)
                logger.error(f"Error generating test cases: {str(e)}")
        
        # Workflow completed successfully
        result.status = "completed"
        result.current_step = "completed"
        logger.info("Workflow completed successfully")
    
    except Exception as e:
        # Workflow failed
        result.status = "failed"
        error = {
            "error_type": "workflow_error",
            "step": result.current_step,
            "message": str(e)
        }
        result.errors.append(error)
        logger.error(f"Workflow failed at step {result.current_step}: {str(e)}")
    
    return result

def main():
    """Run the workflow end-to-end."""
    # Define file paths
    rules_file = "data/rules.json"
    spec_file = "data/specification.json"
    
    # Check if files exist
    if not os.path.exists(rules_file):
        logger.error(f"Rules file not found: {rules_file}")
        sys.exit(1)
    
    if not os.path.exists(spec_file):
        logger.error(f"Specification file not found: {spec_file}")
        sys.exit(1)
    
    logger.info(f"Rules file: {rules_file}")
    logger.info(f"Specification file: {spec_file}")
    
    # Configure the workflow
    config = {
        "formalize_rules": True,
        "verify_with_z3": True,
        "generate_tests": True,
        "test_techniques": ["metamorphic", "symbolic", "adversarial", "causal", "llm"],
        "test_cases_per_rule": 3,
        "parallel_test_generation": True,
        "max_retries": 3
    }
    
    # Run the workflow
    logger.info("Running workflow...")
    result = run_workflow(rules_file, spec_file, config)
    
    # Print results
    logger.info(f"Workflow status: {result.status}")
    logger.info(f"Current step: {result.current_step}")
    
    if result.errors:
        logger.warning(f"Workflow completed with {len(result.errors)} errors:")
        for error in result.errors:
            logger.warning(f"  - {error.get('error_type', 'Unknown')}: {error.get('message', 'No message')}")
    
    # Print parsed rules
    logger.info(f"Parsed {len(result.rules)} rules:")
    for i, rule in enumerate(result.rules[:3], 1):  # Show first 3 rules
        logger.info(f"  Rule {i}: {rule.id} - {rule.description}")
        logger.info(f"    Condition: {rule.condition}")
        if hasattr(rule, 'formalized_condition') and rule.formalized_condition:
            logger.info(f"    Formalized: {rule.formalized_condition}")
    
    if len(result.rules) > 3:
        logger.info(f"  ... and {len(result.rules) - 3} more rules")
    
    # Print test cases
    logger.info(f"Generated {len(result.test_cases)} test cases:")
    
    # Group test cases by rule
    test_cases_by_rule = {}
    for test in result.test_cases:
        if test.rule_id not in test_cases_by_rule:
            test_cases_by_rule[test.rule_id] = []
        test_cases_by_rule[test.rule_id].append(test)
    
    # Print summary by rule
    for rule_id, tests in test_cases_by_rule.items():
        logger.info(f"  Rule {rule_id}: {len(tests)} test cases")
        
        # Count tests by technique
        techniques = {}
        for test in tests:
            technique = getattr(test, 'technique', 'unknown')
            if technique not in techniques:
                techniques[technique] = 0
            techniques[technique] += 1
        
        # Print technique breakdown
        for technique, count in techniques.items():
            logger.info(f"    - {technique}: {count} tests")
    
    # Print example test cases (one per technique if available)
    logger.info("Example test cases:")
    shown_techniques = set()
    for test in result.test_cases:
        technique = getattr(test, 'technique', 'unknown')
        if technique not in shown_techniques and len(shown_techniques) < 5:
            shown_techniques.add(technique)
            logger.info(f"  [{technique}] Rule {test.rule_id}: {test.description}")
            logger.info(f"    Test data: {json.dumps(test.test_data, indent=2)}")
            logger.info(f"    Expected result: {test.expected_result}")
    
    # Export results to JSON
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Export validation results
    validation_file = os.path.join(output_dir, "validation_results.json")
    validation_results = []
    for rule in result.rules:
        rule_result = {
            "id": rule.id,
            "condition": rule.condition
        }
        
        if hasattr(rule, 'formalized_condition') and rule.formalized_condition:
            rule_result["formalized_condition"] = rule.formalized_condition
        
        if hasattr(rule, 'verification_result'):
            rule_result["verification"] = {
                "status": rule.verification_result.status,
                "errors": rule.verification_result.errors
            }
        
        validation_results.append(rule_result)
    
    with open(validation_file, "w") as f:
        json.dump(validation_results, f, indent=2)
    
    # Export test cases
    test_cases_file = os.path.join(output_dir, "test_cases.json")
    test_cases_export = []
    for test in result.test_cases:
        test_export = {
            "rule_id": test.rule_id,
            "description": test.description,
            "expected_result": test.expected_result,
            "test_data": test.test_data,
            "technique": getattr(test, 'technique', 'unknown')
        }
        test_cases_export.append(test_export)
    
    with open(test_cases_file, "w") as f:
        json.dump(test_cases_export, f, indent=2)
    
    logger.info(f"Validation results exported to {validation_file}")
    logger.info(f"Test cases exported to {test_cases_file}")
    
    return result

if __name__ == "__main__":
    main()
