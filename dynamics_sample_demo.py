#!/usr/bin/env python3
"""
Sample Dynamics and Derivatives Demo for Eclaire Trials Edit Check Rule Validation System.

This script demonstrates the dynamics and derivatives functionality using sample rules
that contain various dynamic functions.
"""

import os
import sys
import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import the necessary components
from src.models.data_models import EditCheckRule, StudySpecification, Form, Field, FieldType, RuleSeverity
from src.validators.rule_validator import RuleValidator
from src.utils.dynamics import DynamicsProcessor

def create_sample_specification():
    """Create a sample specification with forms and fields for dynamics demo."""
    spec = StudySpecification()
    
    # Demographics form
    demographics = Form(
        name="Demographics",
        label="Demographics"
    )
    demographics.fields.extend([
        Field(name="SubjectID", type=FieldType.TEXT, label="Subject ID", required=True),
        Field(name="Weight", type=FieldType.NUMBER, label="Weight (kg)"),
        Field(name="Height", type=FieldType.NUMBER, label="Height (cm)"),
        Field(name="DateOfBirth", type=FieldType.DATE, label="Date of Birth"),
        Field(name="Gender", type=FieldType.CATEGORICAL, label="Gender", valid_values=["Male", "Female", "Other"])
    ])
    spec.add_form(demographics)
    
    # Visit form
    visit = Form(
        name="Visit",
        label="Visit Information"
    )
    visit.fields.extend([
        Field(name="VisitDate", type=FieldType.DATE, label="Visit Date", required=True),
        Field(name="ScreeningDate", type=FieldType.DATE, label="Screening Date"),
        Field(name="BaselineDate", type=FieldType.DATE, label="Baseline Date"),
        Field(name="PreviousVisitDate", type=FieldType.DATE, label="Previous Visit Date"),
        Field(name="VisitNumber", type=FieldType.NUMBER, label="Visit Number", required=True)
    ])
    spec.add_form(visit)
    
    # Labs form
    labs = Form(
        name="Labs",
        label="Laboratory Tests"
    )
    labs.fields.extend([
        Field(name="Hemoglobin", type=FieldType.NUMBER, label="Hemoglobin (g/dL)"),
        Field(name="BaselineHemoglobin", type=FieldType.NUMBER, label="Baseline Hemoglobin (g/dL)"),
        Field(name="Platelets", type=FieldType.NUMBER, label="Platelets (10^9/L)"),
        Field(name="Creatinine", type=FieldType.NUMBER, label="Creatinine (mg/dL)"),
        Field(name="PreviousCreatinine", type=FieldType.NUMBER, label="Previous Creatinine (mg/dL)")
    ])
    spec.add_form(labs)
    
    return spec

def load_sample_rules():
    """Load sample rules with dynamics from JSON file."""
    with open("data/excel/sample_dynamics_rule.json", "r") as f:
        data = json.load(f)
    
    rules = []
    for rule_data in data["rules"]:
        rule = EditCheckRule(
            id=rule_data["id"],
            condition=rule_data["condition"],
            message=rule_data.get("message", ""),
            severity=RuleSeverity(rule_data.get("severity", "error")),
            forms=rule_data.get("forms", []),
            fields=rule_data.get("fields", [])
        )
        rules.append(rule)
    
    return rules

def main():
    """Run a sample dynamics and derivatives demo."""
    logger.info("Creating sample specification...")
    spec = create_sample_specification()
    
    logger.info("Loading sample rules with dynamics...")
    rules = load_sample_rules()
    
    logger.info(f"Loaded {len(rules)} sample rules with dynamics")
    for rule in rules:
        logger.info(f"Rule {rule.id}: {rule.condition}")
    
    # Step 1: Extract dynamics from rules
    logger.info("Step 1: Extracting dynamics from rules...")
    dynamics_processor = DynamicsProcessor()
    
    all_dynamics = []
    for rule in rules:
        dynamics = dynamics_processor.extract_dynamics(rule.condition)
        if dynamics:
            for dynamic in dynamics:
                # Add rule_id to each dynamic for reference
                dynamic['rule_id'] = rule.id
            all_dynamics.extend(dynamics)
            logger.info(f"Rule {rule.id} contains {len(dynamics)} dynamic functions:")
            for dynamic in dynamics:
                logger.info(f"  - {dynamic['function']}: {dynamic['original']}")
    
    logger.info(f"Found {len(all_dynamics)} total dynamic functions across all rules")
    
    # Step 2: Expand specification with derivatives
    logger.info("Step 2: Expanding specification with derivatives...")
    expanded_spec = dynamics_processor.expand_derivatives(spec, rules)
    
    if "Derivatives" in expanded_spec.forms:
        derivatives_form = expanded_spec.forms["Derivatives"]
        logger.info(f"Added Derivatives form with {len(derivatives_form.fields)} fields:")
        for field in derivatives_form.fields:
            logger.info(f"  - {field.name}: {field.type.value} - {field.label}")
    
    # Step 3: Validate rules with dynamics
    logger.info("Step 3: Validating rules with dynamics...")
    validator = RuleValidator()
    validation_results = validator.validate_rules(rules, expanded_spec)
    
    valid_count = sum(1 for result in validation_results if result.is_valid)
    logger.info(f"Validation complete: {valid_count}/{len(validation_results)} rules are valid")
    
    # Show validation errors
    for i, result in enumerate(validation_results):
        if not result.is_valid:
            logger.warning(f"Rule {result.rule_id} failed validation with {len(result.errors)} errors:")
            for error in result.errors:
                logger.warning(f"  - {error['message']}")
    
    # Step 4: Output validation results with Eclaire Trials branding
    logger.info("Step 4: Outputting validation results...")
    
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)
    
    # Create HTML report with Eclaire Trials branding
    with open("output/dynamics_report.html", "w") as f:
        # Generate dynamic functions table rows
        dynamic_rows = ""
        for dynamic in all_dynamics:
            rule_id = dynamic.get('rule_id', '')
            message = next((rule.message for rule in rules if rule.id == rule_id), "")
            dynamic_rows += f"""
            <tr>
                <td>{rule_id}</td>
                <td class="dynamics">{dynamic['function']}</td>
                <td>{', '.join(dynamic['parameters'])}</td>
                <td>{message}</td>
            </tr>
            """
        
        # Generate validation results table rows
        result_rows = ""
        for result in validation_results:
            rule_condition = next((rule.condition for rule in rules if rule.id == result.rule_id), "")
            status_class = "valid" if result.is_valid else "invalid"
            status_text = "Valid" if result.is_valid else "Invalid"
            error_messages = "<br>".join(error['message'] for error in result.errors) if not result.is_valid else ""
            result_rows += f"""
            <tr>
                <td>{result.rule_id}</td>
                <td class="{status_class}">{status_text}</td>
                <td>{rule_condition}</td>
                <td>{error_messages}</td>
            </tr>
            """
        
        # Write the complete HTML
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>Eclaire Trials - Dynamics Validation Report</title>
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
        <h2>Dynamics and Derivatives Validation Report</h2>
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
                <th>Description</th>
            </tr>
            {dynamic_rows}
        </table>
    </div>
    
    <div class="subheader">
        <h3>Validation Results</h3>
    </div>
    
    <div class="content">
        <table>
            <tr>
                <th>Rule ID</th>
                <th>Status</th>
                <th>Condition</th>
                <th>Errors</th>
            </tr>
            {result_rows}
        </table>
    </div>
    
    <div class="footer">
        <p>Generated by Eclaire Trials Edit Check Rule Validation System</p>
        <p>© 2025 Eclaire Trials - Enterprise Clinical Trial Intelligence Platform</p>
    </div>
</body>
</html>
        """)
    
    logger.info(f"HTML report saved to output/dynamics_report.html")
    
    # Print summary
    print("\n=== DYNAMICS SAMPLE DEMO SUMMARY ===")
    print(f"Rules: {len(rules)}")
    print(f"Valid Rules: {valid_count}/{len(validation_results)}")
    print(f"Dynamic Functions: {len(all_dynamics)}")
    print(f"Derivative Fields: {len(expanded_spec.forms.get('Derivatives', {}).fields) if 'Derivatives' in expanded_spec.forms else 0}")
    print(f"Results saved to output/ directory")
    print(f"HTML report: output/dynamics_report.html")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
