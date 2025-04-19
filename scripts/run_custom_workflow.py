#!/usr/bin/env python3
"""
Run the Custom Workflow for the Eclaire Trials Edit Check Rule Validation System.

This script demonstrates the full workflow using the custom implementation
that integrates dynamics and derivatives functionality.
"""

import os
import sys
import json
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import the custom workflow
from src.workflow.custom_workflow import CustomWorkflow

def main():
    """Run the custom workflow end-to-end."""
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
    
    # Configure the workflow
    config = {
        "formalize_rules": True,
        "verify_with_z3": False,  # Skip Z3 verification for now
        "generate_tests": True,
        "test_techniques": ["boundary", "equivalence"],
        "test_cases_per_rule": 2,
        "parallel_test_generation": False,
        "max_retries": 2,
        "process_dynamics": True  # Enable dynamics processing
    }
    
    # Create the custom workflow
    logger.info("Creating custom workflow...")
    workflow = CustomWorkflow(config)
    
    # Run the workflow
    logger.info("Running custom workflow...")
    result = workflow.run(rules_file, spec_file)
    
    # Print results
    logger.info(f"Workflow status: {result.get('status', 'unknown')}")
    logger.info(f"Current step: {result.get('current_step', 'unknown')}")
    
    if result.get('errors', []):
        logger.warning(f"Workflow completed with {len(result['errors'])} errors:")
        for error in result['errors']:
            logger.warning(f"  - {error.get('error_type', 'Unknown')}: {error.get('message', 'No message')}")
    
    # Print parsed rules
    rules = result.get('rules', [])
    logger.info(f"Parsed {len(rules)} rules:")
    for i, rule in enumerate(rules[:3], 1):  # Show first 3 rules
        logger.info(f"  Rule {i}: {rule.get('id', 'Unknown')} - {rule.get('description', 'No description')}")
        logger.info(f"    Condition: {rule.get('condition', 'No condition')}")
    
    if len(rules) > 3:
        logger.info(f"  ... and {len(rules) - 3} more rules")
    
    # Print dynamics information
    dynamics = result.get('dynamics', [])
    logger.info(f"Extracted {len(dynamics)} dynamic functions:")
    for i, dynamic in enumerate(dynamics[:5], 1):  # Show first 5 dynamics
        logger.info(f"  Dynamic {i}: {dynamic.get('function', 'Unknown')} - {dynamic.get('original', 'No original')}")
    
    if len(dynamics) > 5:
        logger.info(f"  ... and {len(dynamics) - 5} more dynamic functions")
    
    # Print test cases
    test_cases = result.get('test_cases', [])
    logger.info(f"Generated {len(test_cases)} test cases:")
    
    # Export results to JSON
    output_file = "custom_workflow_results.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2, default=str)
    
    logger.info(f"Results exported to {output_file}")
    
    return result

if __name__ == "__main__":
    main()
