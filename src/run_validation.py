"""
Main entry point for the Edit Check Rule Validation System.

This module provides a command-line interface for running the validation workflow.
"""

import os
import sys
import argparse
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from .workflow.workflow_orchestrator import WorkflowOrchestrator
from .utils.logger import Logger

# Load environment variables
load_dotenv()

logger = Logger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Edit Check Rule Validation System for Clinical Trials"
    )
    
    parser.add_argument(
        "--rules", 
        required=True,
        help="Path to the rules Excel file"
    )
    
    parser.add_argument(
        "--spec", 
        required=True,
        help="Path to the study specification Excel file"
    )
    
    parser.add_argument(
        "--config", 
        help="Path to configuration JSON file"
    )
    
    parser.add_argument(
        "--output", 
        help="Path to output directory for validation results"
    )
    
    parser.add_argument(
        "--no-formalize", 
        action="store_true",
        help="Skip rule formalization with LLM"
    )
    
    parser.add_argument(
        "--no-verify", 
        action="store_true",
        help="Skip rule verification with Z3"
    )
    
    parser.add_argument(
        "--no-tests", 
        action="store_true",
        help="Skip test case generation"
    )
    
    parser.add_argument(
        "--test-cases", 
        type=int,
        default=3,
        help="Number of test cases to generate per rule"
    )
    
    return parser.parse_args()

def load_config(config_path: Optional[str]) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Configuration dictionary
    """
    config = {}
    
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
    
    return config

def save_results(state, output_dir: str) -> None:
    """
    Save validation results to files.
    
    Args:
        state: Workflow state with results
        output_dir: Output directory
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Save validation results
    validation_results = []
    for result in state.validation_results:
        validation_results.append({
            "rule_id": result.rule_id,
            "is_valid": result.is_valid,
            "errors": result.errors,
            "warnings": result.warnings
        })
    
    with open(os.path.join(output_dir, "validation_results.json"), 'w') as f:
        json.dump(validation_results, f, indent=2)
    
    # Save test cases
    test_cases = []
    for test_case in state.test_cases:
        test_cases.append({
            "rule_id": test_case.rule_id,
            "description": test_case.description,
            "expected_result": test_case.expected_result,
            "test_data": test_case.test_data,
            "is_positive": test_case.is_positive
        })
    
    with open(os.path.join(output_dir, "test_cases.json"), 'w') as f:
        json.dump(test_cases, f, indent=2)
    
    # Save formalized rules
    formalized_rules = []
    for rule in state.rules:
        formalized_rules.append({
            "id": rule.id,
            "condition": rule.condition,
            "formalized_condition": rule.formalized_condition,
            "message": rule.message,
            "severity": rule.severity.value if hasattr(rule.severity, 'value') else rule.severity
        })
    
    with open(os.path.join(output_dir, "formalized_rules.json"), 'w') as f:
        json.dump(formalized_rules, f, indent=2)
    
    # Save summary
    summary = {
        "status": state.status,
        "total_rules": len(state.rules),
        "valid_rules": sum(1 for r in state.validation_results if r.is_valid),
        "rules_with_errors": sum(1 for r in state.validation_results if not r.is_valid),
        "rules_with_warnings": sum(1 for r in state.validation_results if r.warnings),
        "total_test_cases": len(state.test_cases),
        "errors": state.errors
    }
    
    with open(os.path.join(output_dir, "summary.json"), 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Results saved to {output_dir}")

def main():
    """Main entry point."""
    # Parse command line arguments
    args = parse_args()
    
    # Validate input files
    if not os.path.exists(args.rules):
        logger.error(f"Rules file not found: {args.rules}")
        sys.exit(1)
    
    if not os.path.exists(args.spec):
        logger.error(f"Specification file not found: {args.spec}")
        sys.exit(1)
    
    # Load configuration
    config = load_config(args.config)
    
    # Override configuration with command line arguments
    config["formalize_rules"] = not args.no_formalize
    config["verify_with_z3"] = not args.no_verify
    config["generate_tests"] = not args.no_tests
    config["test_cases_per_rule"] = args.test_cases
    
    # Create output directory
    output_dir = args.output or os.path.join(os.getcwd(), "validation_results")
    
    # Initialize the workflow orchestrator
    orchestrator = WorkflowOrchestrator(config)
    
    # Run the validation workflow
    logger.info("Starting validation workflow...")
    state = orchestrator.run(args.rules, args.spec)
    
    # Save results
    save_results(state, output_dir)
    
    # Print summary
    valid_rules = sum(1 for r in state.validation_results if r.is_valid)
    total_rules = len(state.rules)
    
    print("\n=== Validation Summary ===")
    print(f"Status: {state.status}")
    print(f"Rules: {valid_rules}/{total_rules} valid")
    print(f"Test Cases: {len(state.test_cases)} generated")
    print(f"Results saved to: {output_dir}")
    
    if state.errors:
        print("\nErrors:")
        for error in state.errors:
            print(f"- {error['message']}")
    
    # Return exit code based on status
    if state.status == "failed":
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
