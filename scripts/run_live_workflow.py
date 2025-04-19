#!/usr/bin/env python3
"""
Live Workflow for Eclaire Trials Edit Check Rule Validation System.

This script shows real-time processing of all records with detailed logging.
"""

import os
import sys
import json
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from tqdm import tqdm
import colorama
from colorama import Fore, Style

# Initialize colorama
colorama.init()

# Configure logging with colored output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)

# Create a custom logger
logger = logging.getLogger("EclaireTrials")

# Import the necessary components
from src.parsers.custom_parser import CustomParser
from src.validators.rule_validator import RuleValidator
from src.validators.dynamics_validator import DynamicsValidator
from src.utils.dynamics import DynamicsProcessor
from src.models.data_models import EditCheckRule, StudySpecification, ValidationResult

# Create output directory if it doesn't exist
os.makedirs("output", exist_ok=True)

def print_header(text):
    """Print a formatted header."""
    width = 80
    print("\n" + "=" * width)
    print(f"{Fore.BLUE}{text.center(width)}{Style.RESET_ALL}")
    print("=" * width + "\n")

def print_subheader(text):
    """Print a formatted subheader."""
    width = 80
    print("\n" + "-" * width)
    print(f"{Fore.CYAN}{text}{Style.RESET_ALL}")
    print("-" * width + "\n")

def print_success(text):
    """Print a success message."""
    print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")

def print_warning(text):
    """Print a warning message."""
    print(f"{Fore.YELLOW}⚠ {text}{Style.RESET_ALL}")

def print_error(text):
    """Print an error message."""
    print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")

def print_info(text):
    """Print an info message."""
    print(f"{Fore.WHITE}{text}{Style.RESET_ALL}")

def print_rule_info(rule, index, total):
    """Print information about a rule."""
    print(f"{Fore.CYAN}Rule {index}/{total}: {rule.id}{Style.RESET_ALL}")
    print(f"  Description: {rule.description}")
    print(f"  Condition: {rule.condition}")
    if hasattr(rule, 'forms') and rule.forms:
        print(f"  Forms: {', '.join(rule.forms)}")
    print()

def print_validation_result(result, rule_id):
    """Print a validation result."""
    if result.is_valid:
        print(f"{Fore.GREEN}✓ Rule {rule_id} passed validation{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}✗ Rule {rule_id} failed validation with {len(result.errors)} errors{Style.RESET_ALL}")
        for error in result.errors:
            print(f"  {Fore.RED}- {error}{Style.RESET_ALL}")
        if result.warnings:
            for warning in result.warnings:
                print(f"  {Fore.YELLOW}! {warning}{Style.RESET_ALL}")
    print()

def main():
    """Run the live workflow with detailed logging."""
    print_header("ECLAIRE TRIALS EDIT CHECK RULE VALIDATION SYSTEM")
    print_info("Live Workflow with Real-Time Processing")
    print_info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Define file paths
    rules_file = "data/excel/rules_study.xlsx"
    spec_file = "data/excel/rules_spec.xlsx"
    
    # Check if files exist
    if not os.path.exists(rules_file):
        print_error(f"Rules file not found: {rules_file}")
        return 1
    
    if not os.path.exists(spec_file):
        print_error(f"Specification file not found: {spec_file}")
        return 1
    
    print_info(f"Rules file: {rules_file}")
    print_info(f"Specification file: {spec_file}")
    print()
    
    # Step 1: Parse the files using the custom parser with dynamics support
    print_subheader("STEP 1: PARSING FILES WITH DYNAMICS SUPPORT")
    parser = CustomParser()
    
    # Parse specification
    print_info("Parsing specification...")
    start_time = time.time()
    spec, spec_errors = parser.parse_specification(spec_file)
    parse_spec_time = time.time() - start_time
    
    if spec_errors:
        print_warning(f"Found {len(spec_errors)} errors while parsing specification:")
        for error in spec_errors:
            print_warning(f"  - {error}")
    
    print_success(f"Parsed specification with {len(spec.forms)} forms in {parse_spec_time:.2f} seconds")
    print_info("Forms in specification:")
    for i, form_name in enumerate(spec.forms, 1):
        form = spec.forms[form_name]
        print(f"  {i}. {form_name} ({len(form.fields)} fields)")
    print()
    
    # Parse rules
    print_info("Parsing rules...")
    start_time = time.time()
    rules, rule_errors = parser.parse_rules(rules_file)
    parse_rules_time = time.time() - start_time
    
    if rule_errors:
        print_warning(f"Found {len(rule_errors)} errors while parsing rules:")
        for error in rule_errors:
            print_warning(f"  - {error}")
    
    print_success(f"Parsed {len(rules)} rules in {parse_rules_time:.2f} seconds")
    print()
    
    # Step 2: Process dynamics and update specification with derivatives
    print_subheader("STEP 2: PROCESSING DYNAMICS AND UPDATING SPECIFICATION")
    dynamics_processor = DynamicsProcessor()
    
    # Extract dynamics from rules
    print_info("Extracting dynamics from rules...")
    dynamics = parser.dynamics if hasattr(parser, 'dynamics') else []
    
    if dynamics:
        print_success(f"Found {len(dynamics)} dynamic functions across all rules")
        for dynamic in dynamics:
            print_info(f"  - {dynamic['function']}: {dynamic['expression']}")
        
        # Add derivatives to specification
        print_info("Adding derivatives to specification...")
        spec = dynamics_processor.add_derivatives_to_spec(spec, dynamics)
        print_success(f"Updated specification now has {len(spec.forms)} forms")
    else:
        print_info("No dynamic functions found in rules")
    print()
    
    # Step 3: Validate rules with dynamics support
    print_subheader("STEP 3: VALIDATING RULES WITH DYNAMICS SUPPORT")
    validator = RuleValidator()
    dynamics_validator = DynamicsValidator()
    
    # Validate each rule
    valid_rules = []
    invalid_rules = []
    validation_results = []
    
    print_info(f"Validating {len(rules)} rules...")
    
    # Create progress bar
    with tqdm(total=len(rules), desc="Validating rules", unit="rule") as pbar:
        for i, rule in enumerate(rules, 1):
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
            else:
                invalid_rules.append(rule)
            
            # Update progress bar
            pbar.update(1)
            
            # Display detailed info for every 10th rule or if it has errors
            if i % 10 == 0 or not result.is_valid:
                pbar.clear()
                print_rule_info(rule, i, len(rules))
                print_validation_result(result, rule.id)
                pbar.display()
    
    # Print validation summary
    valid_percent = (len(valid_rules) / len(rules) * 100) if rules else 0
    print_success(f"Validation complete: {len(valid_rules)}/{len(rules)} rules are valid ({valid_percent:.1f}%)")
    
    # Print common error types
    error_types = {}
    for result in validation_results:
        for error in result.errors:
            error_type = error.get('error_type', 'unknown')
            if error_type not in error_types:
                error_types[error_type] = 0
            error_types[error_type] += 1
    
    if error_types:
        print_info("Common error types:")
        for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {error_type}: {count} occurrences")
    print()
    
    # Step 4: Generate reports
    print_subheader("STEP 4: GENERATING REPORTS")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Export validation results to JSON
    validation_output = f"output/live_validation_results_{timestamp}.json"
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
    
    print_success(f"Validation results exported to {validation_output}")
    
    # Generate HTML report
    html_output = f"output/live_report_{timestamp}.html"
    
    # Prepare data for HTML report
    report_data = {
        "title": "Eclaire Trials Edit Check Rule Validation Report",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total_rules": len(rules),
            "valid_rules": len(valid_rules),
            "invalid_rules": len(invalid_rules),
            "dynamics_count": len(dynamics) if dynamics else 0,
            "test_cases_count": 0
        },
        "rules": [
            {
                "id": rule.id,
                "description": rule.description,
                "condition": rule.condition,
                "is_valid": any(r.rule_id == rule.id and r.is_valid for r in validation_results),
                "errors": [e for r in validation_results if r.rule_id == rule.id for e in r.errors],
                "warnings": [w for r in validation_results if r.rule_id == rule.id for w in r.warnings],
                "test_cases": []
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
        from src.utils.html_generator import generate_html_report
        generate_html_report(report_data, html_output)
        print_success(f"HTML report generated at {html_output}")
    except Exception as e:
        print_error(f"Error generating HTML report: {str(e)}")
    
    # Print final summary
    print_header("WORKFLOW SUMMARY")
    print_info(f"Total rules processed: {len(rules)}")
    print_success(f"Valid rules: {len(valid_rules)} ({valid_percent:.1f}%)")
    print_warning(f"Invalid rules: {len(invalid_rules)} ({100-valid_percent:.1f}%)")
    print_info(f"Dynamic functions: {len(dynamics) if dynamics else 0}")
    print_info(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
