#!/usr/bin/env python3
"""
Integrated Workflow for Eclaire Trials Edit Check Rule Validation System.

This script combines dynamics processing with test case generation for a complete
end-to-end workflow from Excel parsing to test case generation and reporting.
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import the necessary components
from src.parsers.custom_parser import CustomParser
from src.validators.rule_validator import RuleValidator
from src.validators.dynamics_validator import DynamicsValidator
from src.utils.dynamics import DynamicsProcessor
from src.models.data_models import EditCheckRule, StudySpecification, ValidationResult
from src.workflow.workflow_orchestrator import WorkflowOrchestrator
from src.utils.html_generator import generate_html_report

# Create output directory if it doesn't exist
os.makedirs("output", exist_ok=True)

def main():
    """Run the integrated workflow with dynamics and test case generation."""
    # Define file paths
    rules_file = "data/excel/rules_study.xlsx"
    spec_file = "data/excel/rules_spec.xlsx"
    
    # Check if files exist
    if not os.path.exists(rules_file):
        logger.error(f"Rules file not found: {rules_file}")
        sys.exit(1)
    
    if not os.path.exists(spec_file):
        logger.error(f"Specification file not found: {spec_file}")
        sys.exit(1)
    
    logger.info(f"Rules file: {rules_file}")
    logger.info(f"Specification file: {spec_file}")
    
    # Step 1: Parse the files using the custom parser with dynamics support
    logger.info("Step 1: Parsing files with dynamics support...")
    parser = CustomParser()
    
    # Parse specification
    logger.info("Parsing specification...")
    spec, spec_errors = parser.parse_specification(spec_file)
    
    if spec_errors:
        logger.warning(f"Found {len(spec_errors)} errors while parsing specification:")
        for error in spec_errors:
            logger.warning(f"  - {error}")
    
    logger.info(f"Parsed specification with {len(spec.forms)} forms")
    
    # Parse rules
    logger.info("Parsing rules...")
    rules, rule_errors = parser.parse_rules(rules_file)
    
    if rule_errors:
        logger.warning(f"Found {len(rule_errors)} errors while parsing rules:")
        for error in rule_errors:
            logger.warning(f"  - {error}")
    
    logger.info(f"Parsed {len(rules)} rules")
    
    # Step 2: Process dynamics and update specification with derivatives
    logger.info("Step 2: Processing dynamics and updating specification...")
    dynamics_processor = DynamicsProcessor()
    
    # Extract dynamics from rules
    logger.info("Extracting dynamics from rules...")
    dynamics = parser.dynamics if hasattr(parser, 'dynamics') else []
    
    if dynamics:
        logger.info(f"Found {len(dynamics)} dynamic functions across all rules")
        for dynamic in dynamics:
            logger.info(f"  - {dynamic['function']}: {dynamic['expression']}")
        
        # Add derivatives to specification
        logger.info("Adding derivatives to specification...")
        spec = dynamics_processor.add_derivatives_to_spec(spec, dynamics)
        logger.info(f"Updated specification now has {len(spec.forms)} forms")
    else:
        logger.info("No dynamic functions found in rules")
    
    # Step 3: Validate rules with dynamics support
    logger.info("Step 3: Validating rules with dynamics support...")
    validator = RuleValidator()
    dynamics_validator = DynamicsValidator()
    
    # Validate each rule
    valid_rules = []
    invalid_rules = []
    validation_results = []
    
    for rule in rules:
        # Validate the rule
        result = validator.validate_rule(rule, spec)
        
        # If the rule has dynamics, validate those too
        if dynamics:
            dynamics_result = dynamics_validator.validate_rule_dynamics(rule, spec)
            # Merge the validation results
            result.errors.extend(dynamics_result.errors)
            result.warnings.extend(dynamics_result.warnings)
        
        validation_results.append(result)
        
        if result.is_valid:
            valid_rules.append(rule)
            logger.info(f"Rule {rule.id} passed validation")
        else:
            invalid_rules.append(rule)
            logger.warning(f"Rule {rule.id} failed validation with {len(result.errors)} errors")
            for error in result.errors:
                logger.warning(f"  - {error}")
    
    logger.info(f"Validation complete: {len(valid_rules)}/{len(rules)} rules are valid")
    
    # Step 4: Configure test case generation
    logger.info("Step 4: Configuring test case generation...")
    config = {
        "formalize_rules": True,
        "verify_with_z3": True,
        "generate_tests": True,
        "test_techniques": ["metamorphic", "symbolic", "adversarial", "causal"],
        "test_cases_per_rule": 3,
        "parallel_test_generation": True,
        "max_retries": 3,
        "include_dynamics": True  # Enable dynamics support in test generation
    }
    
    # Step 5: Generate test cases using the workflow orchestrator
    logger.info("Step 5: Generating test cases...")
    orchestrator = WorkflowOrchestrator(config)
    
    # We'll use the already parsed rules and specification instead of re-parsing
    orchestrator.rules = rules
    orchestrator.specification = spec
    
    # Run the test generation steps only
    try:
        logger.info("Running test generation...")
        # Use the run method with our already parsed rules and specification
        result = orchestrator.run(rules_file, spec_file)
        
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
    except Exception as e:
        logger.error(f"Error during test generation: {str(e)}")
        result = type('obj', (object,), {
            'status': 'error',
            'errors': [{'error_type': 'TestGenerationError', 'message': str(e)}],
            'test_cases': []
        })
    
    # Step 6: Generate reports
    logger.info("Step 6: Generating reports...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Export validation results to JSON
    validation_output = f"output/integrated_validation_results_{timestamp}.json"
    with open(validation_output, "w") as f:
        json.dump({
            "valid_rules": len(valid_rules),
            "invalid_rules": len(invalid_rules),
            "total_rules": len(rules),
            "dynamics_count": len(dynamics) if dynamics else 0,
            "results": [
                {
                    "rule_id": r.rule_id,
                    "is_valid": r.is_valid,
                    "errors": r.errors,
                    "warnings": r.warnings
                } for r in validation_results
            ]
        }, f, indent=2)
    
    logger.info(f"Validation results exported to {validation_output}")
    
    # Export test cases to JSON
    test_output = f"output/integrated_test_cases_{timestamp}.json"
    with open(test_output, "w") as f:
        json.dump({
            "status": result.status if hasattr(result, 'status') else "unknown",
            "test_cases_count": len(result.test_cases) if hasattr(result, 'test_cases') else 0,
            "errors_count": len(result.errors) if hasattr(result, 'errors') else 0,
            "test_cases": [
                {
                    "rule_id": test.rule_id,
                    "technique": getattr(test, 'technique', 'unknown'),
                    "description": test.description,
                    "test_data": test.test_data,
                    "expected_result": test.expected_result
                } for test in (result.test_cases if hasattr(result, 'test_cases') else [])
            ]
        }, f, indent=2)
    
    logger.info(f"Test cases exported to {test_output}")
    
    # Generate HTML report
    html_output = f"output/integrated_report_{timestamp}.html"
    
    # Prepare data for HTML report
    report_data = {
        "title": "Eclaire Trials Edit Check Rule Validation Report",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total_rules": len(rules),
            "valid_rules": len(valid_rules),
            "invalid_rules": len(invalid_rules),
            "dynamics_count": len(dynamics) if dynamics else 0,
            "test_cases_count": len(result.test_cases) if hasattr(result, 'test_cases') else 0
        },
        "rules": [
            {
                "id": rule.id,
                "description": rule.description,
                "condition": rule.condition,
                "is_valid": any(r.rule_id == rule.id and r.is_valid for r in validation_results),
                "errors": [e for r in validation_results if r.rule_id == rule.id for e in r.errors],
                "warnings": [w for r in validation_results if r.rule_id == rule.id for w in r.warnings],
                "test_cases": [
                    {
                        "technique": getattr(test, 'technique', 'unknown'),
                        "description": test.description,
                        "test_data": test.test_data,
                        "expected_result": test.expected_result
                    } for test in (result.test_cases if hasattr(result, 'test_cases') else []) 
                    if test.rule_id == rule.id
                ]
            } for rule in rules
        ],
        "dynamics": dynamics if dynamics else [],
        "branding": {
            "primary_color": "#0074D9",    # Blue
            "secondary_color": "#FF9500",  # Orange
            "accent_color": "#7F4FBF"      # Purple
        }
    }
    
    # Generate HTML report
    try:
        generate_html_report(report_data, html_output)
        logger.info(f"HTML report generated at {html_output}")
    except Exception as e:
        logger.error(f"Error generating HTML report: {str(e)}")
    
    logger.info("Integrated workflow completed successfully!")
    logger.info(f"Summary: {len(valid_rules)}/{len(rules)} valid rules, {len(dynamics) if dynamics else 0} dynamics, {len(result.test_cases) if hasattr(result, 'test_cases') else 0} test cases")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
