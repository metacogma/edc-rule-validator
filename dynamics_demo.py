#!/usr/bin/env python3
"""
Dynamics and Derivatives Demo for Eclaire Trials Edit Check Rule Validation System.

This script demonstrates the parsing and validation of rules with dynamics and derivatives
from the provided Excel files.
"""

import os
import sys
import logging
import json
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import the necessary components
from src.parsers.custom_parser import CustomParser
from src.validators.rule_validator import RuleValidator
from src.models.data_models import EditCheckRule, StudySpecification
from src.utils.dynamics import DynamicsProcessor

def main():
    """Run a dynamics and derivatives demo of the system."""
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
    
    # Step 1: Parse the files using the custom parser
    logger.info("Step 1: Parsing files...")
    parser = CustomParser()
    
    # Parse specification
    spec, spec_errors = parser.parse_specification(spec_file)
    if spec_errors:
        logger.warning(f"Found {len(spec_errors)} errors while parsing specification:")
        for error in spec_errors:
            logger.warning(f"  - {error['message']}")
    
    logger.info(f"Parsed specification with {len(spec.forms)} forms")
    
    # Parse rules
    rules, rule_errors = parser.parse_rules(rules_file)
    if rule_errors:
        logger.warning(f"Found {len(rule_errors)} errors while parsing rules:")
        for error in rule_errors:
            logger.warning(f"  - {error['message']}")
    
    logger.info(f"Parsed {len(rules)} rules")
    
    # Step 2: Validate the rules
    logger.info("Step 2: Validating rules...")
    validator = RuleValidator()
    validation_results = validator.validate_rules(rules, spec)
    
    valid_count = sum(1 for result in validation_results if result.is_valid)
    logger.info(f"Validation complete: {valid_count}/{len(validation_results)} rules are valid")
    
    # Step 3: Extract and process dynamics
    logger.info("Step 3: Processing dynamics and derivatives...")
    dynamics_processor = DynamicsProcessor()
    
    # Count dynamics in rules
    all_dynamics = []
    for rule in rules:
        dynamics = dynamics_processor.extract_dynamics(rule.condition)
        if dynamics:
            all_dynamics.extend(dynamics)
            logger.info(f"Rule {rule.id} contains {len(dynamics)} dynamic functions:")
            for dynamic in dynamics:
                logger.info(f"  - {dynamic['original']}")
    
    logger.info(f"Found {len(all_dynamics)} total dynamic functions across all rules")
    
    # Step 4: Expand specification with derivatives
    logger.info("Step 4: Expanding specification with derivatives...")
    expanded_spec = dynamics_processor.expand_derivatives(spec, rules)
    
    if "Derivatives" in expanded_spec.forms:
        derivatives_form = expanded_spec.forms["Derivatives"]
        logger.info(f"Added Derivatives form with {len(derivatives_form.fields)} fields:")
        for field in derivatives_form.fields:
            logger.info(f"  - {field.name}: {field.type.value}")
    
    # Step 5: Output validation results
    logger.info("Step 5: Outputting validation results...")
    
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)
    
    # Output validation results
    with open("output/validation_results.json", "w") as f:
        results_json = []
        for result in validation_results:
            results_json.append({
                "rule_id": result.rule_id,
                "is_valid": result.is_valid,
                "errors": result.errors,
                "warnings": result.warnings
            })
        json.dump(results_json, f, indent=2)
    
    logger.info(f"Validation results saved to output/validation_results.json")
    
    # Output dynamics summary
    with open("output/dynamics_summary.json", "w") as f:
        dynamics_json = {
            "total_dynamics": len(all_dynamics),
            "dynamics_by_function": {},
            "dynamics_by_rule": {}
        }
        
        # Count dynamics by function type
        for dynamic in all_dynamics:
            func_name = dynamic["function"]
            if func_name not in dynamics_json["dynamics_by_function"]:
                dynamics_json["dynamics_by_function"][func_name] = 0
            dynamics_json["dynamics_by_function"][func_name] += 1
        
        # Count dynamics by rule
        for rule in rules:
            rule_dynamics = dynamics_processor.extract_dynamics(rule.condition)
            if rule_dynamics:
                dynamics_json["dynamics_by_rule"][rule.id] = len(rule_dynamics)
        
        json.dump(dynamics_json, f, indent=2)
    
    logger.info(f"Dynamics summary saved to output/dynamics_summary.json")
    
    # Print summary
    print("\n=== DYNAMICS DEMO SUMMARY ===")
    print(f"Rules: {len(rules)}")
    print(f"Valid Rules: {valid_count}/{len(validation_results)}")
    print(f"Dynamic Functions: {len(all_dynamics)}")
    print(f"Derivative Fields: {len(expanded_spec.forms.get('Derivatives', {}).fields) if 'Derivatives' in expanded_spec.forms else 0}")
    print(f"Results saved to output/ directory")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
