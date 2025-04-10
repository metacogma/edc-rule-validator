#!/usr/bin/env python
"""
Integrated End-to-End Demo for the Edit Check Rule Validation System.

This script demonstrates the full workflow from parsing to test generation
using the actual rule and specification files with all advanced techniques.
"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import components
from src.parsers.rule_parser import RuleParser
from src.parsers.specification_parser import SpecificationParser
from src.llm.llm_orchestrator_updated import LLMOrchestrator
from src.test_generation.test_generator import TestGenerator
from src.verification.rule_verifier import RuleVerifier

def run_integrated_demo():
    """Run the integrated end-to-end demo."""
    logger.info("Starting integrated end-to-end demo...")
    
    # Define file paths to real Excel files
    rules_file = "tests/data/sample_rules.xlsx"
    spec_file = "tests/data/sample_specification.xlsx"
    
    # Check if files exist
    if not os.path.exists(rules_file):
        logger.error(f"Rules file not found: {rules_file}")
        sys.exit(1)
    
    if not os.path.exists(spec_file):
        logger.error(f"Specification file not found: {spec_file}")
        sys.exit(1)
    
    logger.info(f"Using rules file: {rules_file}")
    logger.info(f"Using specification file: {spec_file}")
    
    # Step 1: Parse rules
    logger.info("\n=== STEP 1: PARSING RULES ===")
    start_time = time.time()
    rule_parser = RuleParser()
    rules = rule_parser.parse(rules_file)
    logger.info(f"Parsed {len(rules)} rules in {time.time() - start_time:.2f} seconds")
    
    # Print sample rules
    for i, rule in enumerate(rules[:3], 1):
        logger.info(f"Rule {i}: {rule.id}")
        logger.info(f"  Condition: {rule.condition}")
    
    if len(rules) > 3:
        logger.info(f"  ... and {len(rules) - 3} more rules")
    
    # Step 2: Parse specification
    logger.info("\n=== STEP 2: PARSING SPECIFICATION ===")
    start_time = time.time()
    spec_parser = SpecificationParser()
    specification = spec_parser.parse(spec_file)
    logger.info(f"Parsed specification with {len(specification.forms)} forms in {time.time() - start_time:.2f} seconds")
    
    # Print sample forms and fields
    form_count = 0
    for form_name, form in specification.forms.items():
        if form_count < 3:
            logger.info(f"Form: {form_name}")
            logger.info(f"  Fields: {', '.join([field.name for field in form.fields[:5]])}")
            if len(form.fields) > 5:
                logger.info(f"  ... and {len(form.fields) - 5} more fields")
            form_count += 1
    
    if len(specification.forms) > 3:
        logger.info(f"  ... and {len(specification.forms) - 3} more forms")
    
    # Step 3: Formalize rules with LLM
    logger.info("\n=== STEP 3: FORMALIZING RULES WITH LLM ===")
    start_time = time.time()
    llm_orchestrator = LLMOrchestrator()
    
    if llm_orchestrator.is_available:
        logger.info("Azure OpenAI is available. Proceeding with rule formalization...")
        formalized_count = 0
        
        for rule in rules[:5]:  # Limit to 5 rules for demo purposes
            try:
                formalized_condition = llm_orchestrator.formalize_rule(rule, specification)
                if formalized_condition:
                    setattr(rule, 'formalized_condition', formalized_condition)
                    logger.info(f"Formalized rule {rule.id}")
                    logger.info(f"  Original: {rule.condition}")
                    logger.info(f"  Formalized: {formalized_condition}")
                    formalized_count += 1
                else:
                    logger.warning(f"Failed to formalize rule {rule.id}")
            except Exception as e:
                logger.error(f"Error formalizing rule {rule.id}: {str(e)}")
        
        logger.info(f"Formalized {formalized_count} rules in {time.time() - start_time:.2f} seconds")
    else:
        logger.warning("Azure OpenAI is not available. Skipping rule formalization.")
    
    # Step 4: Verify rules with Z3
    logger.info("\n=== STEP 4: VERIFYING RULES WITH Z3 ===")
    start_time = time.time()
    verifier = RuleVerifier()
    verified_count = 0
    
    for rule in rules:
        if hasattr(rule, 'formalized_condition') and rule.formalized_condition:
            try:
                verification_result = verifier.verify(rule, specification)
                setattr(rule, 'verification_result', verification_result)
                logger.info(f"Verified rule {rule.id}: {verification_result.status}")
                
                if verification_result.errors:
                    for error in verification_result.errors:
                        logger.warning(f"Verification issue for rule {rule.id}: {error}")
                
                verified_count += 1
            except Exception as e:
                logger.error(f"Error verifying rule {rule.id}: {str(e)}")
    
    logger.info(f"Verified {verified_count} rules in {time.time() - start_time:.2f} seconds")
    
    # Step 5: Generate test cases using all techniques
    logger.info("\n=== STEP 5: GENERATING TEST CASES ===")
    start_time = time.time()
    
    # Configure test generator with all techniques
    test_techniques = ["metamorphic", "symbolic", "adversarial", "causal", "llm"]
    test_generator = TestGenerator()
    
    # Generate test cases
    try:
        # Only use rules that have been formalized for test generation
        formalized_rules = [rule for rule in rules if hasattr(rule, 'formalized_condition') and rule.formalized_condition]
        
        if formalized_rules:
            logger.info(f"Generating tests for {len(formalized_rules)} formalized rules using techniques: {', '.join(test_techniques)}")
            test_cases = test_generator.generate_tests(
                formalized_rules, 
                specification, 
                parallel=True, 
                techniques=test_techniques
            )
            
            logger.info(f"Generated {len(test_cases)} test cases in {time.time() - start_time:.2f} seconds")
            
            # Group test cases by technique
            techniques = {}
            for test in test_cases:
                technique = getattr(test, 'technique', 'unknown')
                if technique not in techniques:
                    techniques[technique] = 0
                techniques[technique] += 1
            
            # Print technique breakdown
            logger.info("Test cases by technique:")
            for technique, count in techniques.items():
                logger.info(f"  - {technique}: {count} tests")
            
            # Group test cases by rule
            test_cases_by_rule = {}
            for test in test_cases:
                if test.rule_id not in test_cases_by_rule:
                    test_cases_by_rule[test.rule_id] = []
                test_cases_by_rule[test.rule_id].append(test)
            
            # Print example test cases for each rule
            logger.info("\n=== EXAMPLE TEST CASES ===")
            for rule_id, tests in test_cases_by_rule.items():
                logger.info(f"Rule {rule_id}: {len(tests)} test cases")
                
                # Show one example of each technique for this rule
                shown_techniques = set()
                for test in tests:
                    technique = getattr(test, 'technique', 'unknown')
                    if technique not in shown_techniques and len(shown_techniques) < 5:
                        shown_techniques.add(technique)
                        logger.info(f"  [{technique}] {test.description}")
                        logger.info(f"    Expected Result: {test.expected_result}")
                        logger.info(f"    Test Data: {json.dumps(test.test_data, indent=2)}")
            
            # Export results to JSON
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            
            # Export validation results
            validation_file = os.path.join(output_dir, "validation_results.json")
            validation_results = []
            for rule in rules:
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
            for test in test_cases:
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
            
            return test_cases
        else:
            logger.warning("No formalized rules available for test generation.")
            return []
            
    except Exception as e:
        logger.error(f"Error generating test cases: {str(e)}")
        return []

if __name__ == "__main__":
    run_integrated_demo()
