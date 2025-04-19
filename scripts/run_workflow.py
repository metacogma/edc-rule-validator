#!/usr/bin/env python
"""
Run the Edit Check Rule Validation workflow end-to-end.

This script demonstrates the full workflow from parsing to test generation
using the provided rule and specification files.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the workflow orchestrator
from src.workflow.workflow_orchestrator import WorkflowOrchestrator
from src.utils.logger import Logger

# Set up logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = Logger(__name__)

def main():
    """Run the workflow end-to-end."""
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
    
    # Configure the workflow
    config = {
        "formalize_rules": True,
        "verify_with_z3": True,
        "generate_tests": True,
        "test_techniques": ["metamorphic", "symbolic", "adversarial", "causal"],
        "test_cases_per_rule": 3,
        "parallel_test_generation": True,
        "max_retries": 3
    }
    
    # Create the workflow orchestrator
    logger.info("Creating workflow orchestrator...")
    orchestrator = WorkflowOrchestrator(config)
    
    # Run the workflow
    logger.info("Running workflow...")
    result = orchestrator.run(rules_file, spec_file)
    
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
        if technique not in shown_techniques and len(shown_techniques) < 4:
            shown_techniques.add(technique)
            logger.info(f"  [{technique}] Rule {test.rule_id}: {test.description}")
            logger.info(f"    Test data: {json.dumps(test.test_data, indent=2)}")
            logger.info(f"    Expected result: {test.expected_result}")
    
    # Export results to JSON
    output_file = "workflow_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "status": result.status,
            "rules_count": len(result.rules),
            "test_cases_count": len(result.test_cases),
            "errors_count": len(result.errors)
        }, f, indent=2)
    
    logger.info(f"Results exported to {output_file}")
    
    return result

if __name__ == "__main__":
    main()
