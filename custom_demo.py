#!/usr/bin/env python
"""
Custom demo of the Edit Check Rule Validation System.

This script demonstrates the parsing and validation capabilities
using the custom parser for the specific Excel file format.
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the necessary components
from src.parsers.custom_parser import CustomParser
from src.validators.rule_validator import RuleValidator
from src.models.data_models import EditCheckRule, StudySpecification
from src.test_generation.test_generator import TestGenerator
from src.llm.llm_orchestrator import LLMOrchestrator

def main():
    """Run a custom demo of the system."""
    # Define file paths
    rules_file = "/Users/nareshkumar/Downloads/editcheck_graph/rules_study.xlsx"
    spec_file = "/Users/nareshkumar/Downloads/editcheck_graph/rules_spec.xlsx"
    
    # Check if files exist
    if not os.path.exists(rules_file):
        logger.error(f"Rules file not found: {rules_file}")
        sys.exit(1)
    
    if not os.path.exists(spec_file):
        logger.error(f"Specification file not found: {spec_file}")
        sys.exit(1)
    
    logger.info(f"Rules file: {rules_file}")
    logger.info(f"Specification file: {spec_file}")
    
    # Step 1: Parse the files using the custom parser
    logger.info("Step 1: Parsing files...")
    parser = CustomParser()
    
    # Parse specification
    spec, spec_errors = parser.parse_specification(spec_file)
    if spec_errors:
        logger.warning(f"Found {len(spec_errors)} errors while parsing specification:")
        for error in spec_errors:
            logger.warning(f"  - {error.get('message', 'Unknown error')}")
    
    logger.info(f"Successfully parsed specification with {len(spec.forms)} forms")
    
    # Parse rules
    rules, rule_errors = parser.parse_rules(rules_file)
    if rule_errors:
        logger.warning(f"Found {len(rule_errors)} errors while parsing rules:")
        for error in rule_errors:
            logger.warning(f"  - {error.get('message', 'Unknown error')}")
    
    if not rules:
        logger.error("Failed to parse rules file or no rules found")
        sys.exit(1)
    
    logger.info(f"Successfully parsed {len(rules)} rules")
    
    # Step 2: Validate the rules
    logger.info("Step 2: Validating rules...")
    validator = RuleValidator()
    validation_results = validator.validate_rules(rules, spec)
    
    # Count valid and invalid rules
    valid_rules = sum(1 for result in validation_results if result.is_valid)
    invalid_rules = sum(1 for result in validation_results if not result.is_valid)
    
    logger.info(f"Validation complete: {valid_rules} valid rules, {invalid_rules} invalid rules")
    
    # Step 3: Generate basic test cases (without LLM)
    logger.info("Step 3: Generating basic test cases...")
    
    # Create a simple test case generator that doesn't require LLM
    def generate_simple_test_cases(rules, spec):
        test_cases = []
        for rule in rules:  # Process all rules
            # Create a positive test case
            positive_test = {
                "rule_id": rule.id,
                "description": f"Positive test for rule {rule.id}",
                "expected_result": True,
                "test_data": {},
                "is_positive": True,
                "technique": "basic"
            }
            
            # Create a negative test case
            negative_test = {
                "rule_id": rule.id,
                "description": f"Negative test for rule {rule.id}",
                "expected_result": False,
                "test_data": {},
                "is_positive": False,
                "technique": "basic"
            }
            
            # Add test cases to the list
            test_cases.append(positive_test)
            test_cases.append(negative_test)
        
        return test_cases
    
    # Generate simple test cases
    test_cases = generate_simple_test_cases(rules, spec)
    
    logger.info(f"Generated {len(test_cases)} test cases")
    
    # Print details about the specification
    logger.info("\nSpecification Details:")
    for form_name, form in spec.forms.items():
        logger.info(f"  Form: {form_name} ({form.label})")
        logger.info(f"    Fields: {len(form.fields)}")
        for field in form.fields[:3]:  # Show first 3 fields
            logger.info(f"      - {field.name} ({field.type})")
        if len(form.fields) > 3:
            logger.info(f"      - ... and {len(form.fields) - 3} more fields")
    
    # Print details about the rules
    logger.info("\nRule Details:")
    for i, rule in enumerate(rules[:5], 1):  # Show first 5 rules
        logger.info(f"  Rule {i}: {rule.id}")
        logger.info(f"    Condition: {rule.condition}")
        
        # Find the validation result for this rule
        result = next((r for r in validation_results if r.rule_id == rule.id), None)
        if result:
            status = "Valid" if result.is_valid else "Invalid"
            logger.info(f"    Validation Status: {status}")
            if not result.is_valid and result.errors:
                logger.info(f"    Errors: {len(result.errors)}")
                for error in result.errors[:2]:  # Show first 2 errors
                    logger.info(f"      - {error.get('message', 'Unknown error')}")
        
        # Show test cases for this rule
        rule_tests = [t for t in test_cases if t['rule_id'] == rule.id]
        if rule_tests:
            logger.info(f"    Test Cases: {len(rule_tests)}")
            for j, test in enumerate(rule_tests[:2], 1):  # Show first 2 test cases
                logger.info(f"      Test {j}: {test['description']}")
                logger.info(f"        Expected Result: {test['expected_result']}")
                logger.info(f"        Test Data: {test['test_data']}")
                logger.info(f"        Technique: {test.get('technique', 'basic')}")
    
    if len(rules) > 5:
        logger.info(f"  ... and {len(rules) - 5} more rules")
    
    # Export results to JSON
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Save validation results
    output_file = output_dir / "validation_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "specification": {
                "forms_count": len(spec.forms),
                "fields_count": sum(len(form.fields) for form in spec.forms.values())
            },
            "rules": {
                "total_count": len(rules),
                "valid_count": valid_rules,
                "invalid_count": invalid_rules
            },
            "validation_results": [
                {
                    "rule_id": result.rule_id,
                    "is_valid": result.is_valid,
                    "errors_count": len(result.errors),
                    "warnings_count": len(result.warnings)
                }
                for result in validation_results
            ],
            "test_cases_count": len(test_cases)
        }, f, indent=2)
    
    # Save test cases to a separate file
    test_cases_file = output_dir / "test_cases.json"
    with open(test_cases_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_test_cases": len(test_cases),
            "test_cases": test_cases
        }, f, indent=2)
    
    logger.info(f"Test cases exported to {test_cases_file}")
    
    logger.info(f"\nResults exported to {output_file}")
    
    return rules, spec, validation_results, test_cases

if __name__ == "__main__":
    main()
