#!/usr/bin/env python3
"""
Run the Dynamics and Derivatives Workflow for the Eclaire Trials Edit Check Rule Validation System.

This script demonstrates the dynamics and derivatives functionality with the real Excel files.
"""

import os
import sys
import json
import logging
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
from src.utils.dynamics import DynamicsProcessor
from src.models.data_models import EditCheckRule, StudySpecification

def main():
    """Run the dynamics and derivatives workflow."""
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
            logger.warning(f"  - {error['message']}")
    
    logger.info(f"Parsed specification with {len(spec.forms)} forms")
    
    # Parse rules
    logger.info("Parsing rules...")
    rules, rule_errors = parser.parse_rules(rules_file)
    if rule_errors:
        logger.warning(f"Found {len(rule_errors)} errors while parsing rules:")
        for error in rule_errors:
            logger.warning(f"  - {error['message']}")
    
    logger.info(f"Parsed {len(rules)} rules")
    
    # Step 2: Process dynamics
    logger.info("Step 2: Processing dynamics and derivatives...")
    dynamics_processor = DynamicsProcessor()
    
    # Extract dynamics from all rules
    all_dynamics = []
    for rule in rules:
        dynamics = dynamics_processor.extract_dynamics(rule.condition)
        if dynamics:
            for dynamic in dynamics:
                # Add rule_id to each dynamic for reference
                dynamic['rule_id'] = rule.id
            all_dynamics.extend(dynamics)
    
    logger.info(f"Found {len(all_dynamics)} total dynamic functions across all rules")
    
    # Group dynamics by function type
    dynamics_by_function = {}
    for dynamic in all_dynamics:
        func_name = dynamic["function"]
        if func_name not in dynamics_by_function:
            dynamics_by_function[func_name] = 0
        dynamics_by_function[func_name] += 1
    
    # Print dynamics by function type
    if dynamics_by_function:
        logger.info("Dynamic functions by type:")
        for func_name, count in dynamics_by_function.items():
            logger.info(f"  - {func_name}: {count} occurrences")
    else:
        logger.info("No dynamic functions found in the rules")
    
    # Step 3: Expand specification with derivatives
    logger.info("Step 3: Expanding specification with derivatives...")
    expanded_spec = dynamics_processor.expand_derivatives(spec, rules)
    
    if "Derivatives" in expanded_spec.forms:
        derivatives_form = expanded_spec.forms["Derivatives"]
        logger.info(f"Added Derivatives form with {len(derivatives_form.fields)} fields:")
        for field in derivatives_form.fields:
            logger.info(f"  - {field.name}: {field.type.value} - {field.label}")
    
    # Step 4: Validate rules with dynamics
    logger.info("Step 4: Validating rules with dynamics support...")
    validator = RuleValidator()
    validation_results = validator.validate_rules(rules, expanded_spec)
    
    valid_count = sum(1 for result in validation_results if result.is_valid)
    logger.info(f"Validation complete: {valid_count}/{len(validation_results)} rules are valid")
    
    # Count validation errors by type
    error_types = {}
    for result in validation_results:
        if not result.is_valid:
            for error in result.errors:
                error_type = error.get('error_type', 'unknown')
                if error_type not in error_types:
                    error_types[error_type] = 0
                error_types[error_type] += 1
    
    # Print error types
    if error_types:
        logger.info("Validation errors by type:")
        for error_type, count in error_types.items():
            logger.info(f"  - {error_type}: {count} occurrences")
    
    # Step 5: Output results
    logger.info("Step 5: Outputting results...")
    
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)
    
    # Output validation results
    with open("output/dynamics_workflow_results.json", "w") as f:
        results = {
            "status": "completed",
            "rules_count": len(rules),
            "valid_rules_count": valid_count,
            "dynamics_count": len(all_dynamics),
            "dynamics_by_function": dynamics_by_function,
            "derivatives_count": len(expanded_spec.forms.get("Derivatives", {}).fields) if "Derivatives" in expanded_spec.forms else 0,
            "error_types": error_types
        }
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved to output/dynamics_workflow_results.json")
    
    # Create HTML report with Eclaire Trials branding
    with open("output/dynamics_workflow_report.html", "w") as f:
        # Generate dynamic functions table rows
        dynamic_rows = ""
        for dynamic in all_dynamics:
            rule_id = dynamic.get('rule_id', '')
            dynamic_rows += f"""
            <tr>
                <td>{rule_id}</td>
                <td class="dynamics">{dynamic['function']}</td>
                <td>{', '.join(dynamic['parameters'])}</td>
                <td>{dynamic['original']}</td>
            </tr>
            """
        
        # Write the complete HTML
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>Eclaire Trials - Dynamics Workflow Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            color: #333;
        }}
        .header {{
            background-color: #0074D9;
            color: white;
            padding: 20px;
            text-align: center;
        }}
        .subheader {{
            background-color: #FF9500;
            color: white;
            padding: 10px 20px;
        }}
        .content {{
            padding: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        .valid {{
            color: green;
        }}
        .invalid {{
            color: red;
        }}
        .dynamics {{
            color: #7F4FBF;
        }}
        .footer {{
            background-color: #f2f2f2;
            padding: 10px 20px;
            text-align: center;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Eclaire Trials</h1>
        <h2>Dynamics and Derivatives Workflow Report</h2>
    </div>
    
    <div class="subheader">
        <h3>Summary</h3>
    </div>
    
    <div class="content">
        <p>Total Rules: {len(rules)}</p>
        <p>Valid Rules: {valid_count}/{len(validation_results)}</p>
        <p>Dynamic Functions: {len(all_dynamics)}</p>
        <p>Derivative Fields: {len(expanded_spec.forms.get('Derivatives', {}).fields) if 'Derivatives' in expanded_spec.forms else 0}</p>
    </div>
    
    <div class="subheader">
        <h3>Dynamic Functions</h3>
    </div>
    
    <div class="content">
        <table>
            <tr>
                <th>Rule ID</th>
                <th>Function</th>
                <th>Parameters</th>
                <th>Original Expression</th>
            </tr>
            {dynamic_rows}
        </table>
    </div>
    
    <div class="subheader">
        <h3>Validation Error Types</h3>
    </div>
    
    <div class="content">
        <table>
            <tr>
                <th>Error Type</th>
                <th>Count</th>
            </tr>
            {"".join(f'''
            <tr>
                <td>{error_type}</td>
                <td>{count}</td>
            </tr>
            ''' for error_type, count in error_types.items())}
        </table>
    </div>
    
    <div class="footer">
        <p>Generated by Eclaire Trials Edit Check Rule Validation System</p>
        <p>© 2025 Eclaire Trials - Enterprise Clinical Trial Intelligence Platform</p>
    </div>
</body>
</html>
        """)
    
    logger.info(f"HTML report saved to output/dynamics_workflow_report.html")
    
    # Print summary
    print("\n=== DYNAMICS WORKFLOW SUMMARY ===")
    print(f"Rules: {len(rules)}")
    print(f"Valid Rules: {valid_count}/{len(validation_results)}")
    print(f"Dynamic Functions: {len(all_dynamics)}")
    print(f"Derivative Fields: {len(expanded_spec.forms.get('Derivatives', {}).fields) if 'Derivatives' in expanded_spec.forms else 0}")
    print(f"Results saved to output/ directory")
    print(f"HTML report: output/dynamics_workflow_report.html")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
