#!/usr/bin/env python
"""
Full Excel Demo for Eclaire Trials Edit Check Rule Validation System.

This script demonstrates the full workflow using all records from Excel files.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Any, Optional

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import components
from src.models.data_models import EditCheckRule, StudySpecification, TestCase, Form, Field, FieldType
from src.llm.llm_orchestrator_updated import LLMOrchestrator
from src.test_generation.test_generator import TestGenerator
from src.verification.rule_verifier import RuleVerifier

# Eclaire Trials brand colors
ECLAIRE_BLUE = "#0074D9"
ECLAIRE_ORANGE = "#FF9500"
ECLAIRE_PURPLE = "#7F4FBF"

class ExcelRuleParser:
    """Parse rules from Excel files with flexible column mapping."""
    
    def parse(self, file_path: str) -> List[EditCheckRule]:
        """
        Parse rules from an Excel file with flexible column mapping.
        
        Args:
            file_path: Path to the Excel file containing rules
            
        Returns:
            List of parsed rules
        """
        logger.info(f"Parsing rules from Excel file: {file_path}")
        
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Map column names (case-insensitive)
            column_mapping = {
                'id': ['ruleid', 'rule_id', 'rule id', 'id', 'check_id', 'checkid', 'check id'],
                'condition': ['condition', 'rule', 'rule_condition', 'check'],
                'description': ['description', 'desc', 'message'],
                'forms': ['forms', 'form', 'form_name', 'form name'],
                'fields': ['fields', 'field', 'field_name', 'field name'],
                'severity': ['severity', 'sev']
            }
            
            # Find actual column names
            actual_columns = {}
            for key, possible_names in column_mapping.items():
                for col in df.columns:
                    if col.lower() in possible_names:
                        actual_columns[key] = col
                        break
            
            # Parse rules
            rules = []
            for _, row in df.iterrows():
                rule = self._parse_rule(row, actual_columns)
                if rule:
                    rules.append(rule)
            
            logger.info(f"Successfully parsed {len(rules)} rules from Excel file")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing rules from Excel file: {str(e)}")
            raise
    
    def _parse_rule(self, row: pd.Series, columns: Dict[str, str]) -> Optional[EditCheckRule]:
        """
        Parse a single rule from an Excel row.
        
        Args:
            row: DataFrame row containing rule data
            columns: Mapping of standard column names to actual column names
            
        Returns:
            Parsed rule or None if row is invalid
        """
        try:
            # Extract required fields
            rule_id = str(row.get(columns.get('id', ''), ''))
            condition = str(row.get(columns.get('condition', ''), ''))
            
            # Skip empty rows
            if not rule_id or not condition:
                return None
            
            # Create rule object
            rule = EditCheckRule(
                id=rule_id,
                condition=condition
            )
            
            # Add optional attributes if present in the Excel
            if 'description' in columns and pd.notna(row[columns['description']]):
                setattr(rule, 'description', str(row[columns['description']]))
            else:
                # Use condition as description if not provided
                setattr(rule, 'description', condition)
            
            if 'forms' in columns and pd.notna(row[columns['forms']]):
                forms = str(row[columns['forms']]).split(',')
                forms = [form.strip() for form in forms]
                setattr(rule, 'forms', forms)
            
            if 'fields' in columns and pd.notna(row[columns['fields']]):
                fields = str(row[columns['fields']]).split(',')
                fields = [field.strip() for field in fields]
                setattr(rule, 'fields', fields)
            
            if 'severity' in columns and pd.notna(row[columns['severity']]):
                setattr(rule, 'severity', str(row[columns['severity']]))
            
            return rule
            
        except Exception as e:
            logger.error(f"Error parsing rule row: {str(e)}")
            return None


class ExcelSpecificationParser:
    """Parse specifications from Excel files with flexible column mapping."""
    
    def parse(self, file_path: str) -> StudySpecification:
        """
        Parse a study specification from an Excel file.
        
        Args:
            file_path: Path to the Excel file containing the specification
            
        Returns:
            Parsed study specification
        """
        logger.info(f"Parsing specification from Excel file: {file_path}")
        
        try:
            # Read the Excel file
            xls = pd.ExcelFile(file_path)
            
            # Create study specification
            specification = StudySpecification()
            
            # Parse each sheet as a form
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Skip empty sheets
                if df.empty:
                    continue
                
                # Create form
                form = Form(
                    name=sheet_name,
                    label=sheet_name,
                    fields=[]
                )
                
                # Parse fields from columns
                for column in df.columns:
                    # Infer field type
                    field_type = self._infer_field_type(df[column])
                    
                    # Create field
                    field = Field(
                        name=column,
                        type=field_type,
                        label=column,
                        required=False
                    )
                    form.fields.append(field)
                
                # Add form to specification
                specification.add_form(form)
            
            logger.info(f"Successfully parsed specification with {len(specification.forms)} forms")
            return specification
            
        except Exception as e:
            logger.error(f"Error parsing specification from Excel file: {str(e)}")
            raise
    
    def _infer_field_type(self, series: pd.Series) -> FieldType:
        """
        Infer the data type of a field based on its values.
        
        Args:
            series: Series of values for the field
            
        Returns:
            Inferred data type as FieldType enum
        """
        # Check for date fields
        if pd.api.types.is_datetime64_any_dtype(series):
            return FieldType.DATE
        
        # Check for numeric fields
        if pd.api.types.is_numeric_dtype(series):
            if all(isinstance(x, int) or pd.isna(x) for x in series):
                return FieldType.NUMBER
            else:
                return FieldType.NUMBER
        
        # Check for boolean fields
        if pd.api.types.is_bool_dtype(series):
            return FieldType.BOOLEAN
        
        # Try to detect categorical fields
        if len(series.unique()) < 10 and len(series) > 10:
            return FieldType.CATEGORICAL
        
        # Default to text
        return FieldType.TEXT


class FullExcelDemo:
    """Full demonstration using all records from Excel files."""
    
    def __init__(self):
        """Initialize the demo."""
        self.rule_parser = ExcelRuleParser()
        self.spec_parser = ExcelSpecificationParser()
        self.llm_orchestrator = LLMOrchestrator()
        self.test_generator = TestGenerator()
        self.rule_verifier = RuleVerifier()
        
        # Results storage
        self.rules = []
        self.specification = None
        self.test_cases = []
        self.errors = []
        
        # Performance metrics
        self.metrics = {
            "parsing_time": 0,
            "formalization_time": 0,
            "verification_time": 0,
            "test_generation_time": 0,
            "total_time": 0
        }
        
        # Test generation statistics
        self.test_stats = {}
    
    def run(self, rules_file: str, spec_file: str, output_dir: str = "output"):
        """
        Run the full demonstration.
        
        Args:
            rules_file: Path to the rules Excel file
            spec_file: Path to the specification Excel file
            output_dir: Directory to save output files
        """
        start_time = time.time()
        
        logger.info("=" * 80)
        logger.info("ECLAIRE TRIALS - EDIT CHECK RULE VALIDATION SYSTEM")
        logger.info("Full Excel Demonstration")
        logger.info("=" * 80)
        
        # Step 1: Parse files
        self._parse_files(rules_file, spec_file)
        
        # Step 2: Formalize rules
        self._formalize_rules()
        
        # Step 3: Verify rules
        self._verify_rules()
        
        # Step 4: Generate tests
        self._generate_tests()
        
        # Step 5: Generate reports
        self._generate_reports(output_dir)
        
        # Calculate total time
        self.metrics["total_time"] = time.time() - start_time
        
        # Print summary
        self._print_summary()
    
    def _parse_files(self, rules_file: str, spec_file: str):
        """Parse rules and specification files."""
        logger.info("\n=== STEP 1: PARSING FILES ===")
        
        parsing_start = time.time()
        
        # Parse rules
        logger.info(f"Parsing rules from {rules_file}...")
        try:
            self.rules = self.rule_parser.parse(rules_file)
            logger.info(f"Successfully parsed {len(self.rules)} rules")
        except Exception as e:
            error = {
                "error_type": "rule_parsing_error",
                "message": str(e)
            }
            self.errors.append(error)
            logger.error(f"Error parsing rules: {str(e)}")
        
        # Parse specification
        logger.info(f"Parsing specification from {spec_file}...")
        try:
            self.specification = self.spec_parser.parse(spec_file)
            logger.info(f"Successfully parsed specification with {len(self.specification.forms)} forms")
        except Exception as e:
            error = {
                "error_type": "specification_parsing_error",
                "message": str(e)
            }
            self.errors.append(error)
            logger.error(f"Error parsing specification: {str(e)}")
        
        # Record parsing time
        self.metrics["parsing_time"] = time.time() - parsing_start
        
        # Print sample rules
        for i, rule in enumerate(self.rules[:5], 1):
            logger.info(f"Rule {i}: {rule.id}")
            logger.info(f"  Condition: {rule.condition}")
        
        if len(self.rules) > 5:
            logger.info(f"  ... and {len(self.rules) - 5} more rules")
    
    def _formalize_rules(self):
        """Formalize rules using LLM."""
        logger.info("\n=== STEP 2: FORMALIZING RULES WITH LLM ===")
        
        formalization_start = time.time()
        
        if self.llm_orchestrator.is_available:
            logger.info("Azure OpenAI is available. Proceeding with rule formalization...")
            formalized_count = 0
            
            for rule in self.rules:
                try:
                    formalized_condition = self.llm_orchestrator.formalize_rule(rule, self.specification)
                    if formalized_condition:
                        setattr(rule, 'formalized_condition', formalized_condition)
                        logger.info(f"Formalized rule {rule.id}")
                        logger.info(f"  Original: {rule.condition}")
                        logger.info(f"  Formalized: {formalized_condition}")
                        formalized_count += 1
                    else:
                        logger.warning(f"Failed to formalize rule {rule.id}")
                except Exception as e:
                    error = {
                        "error_type": "formalization_error",
                        "rule_id": rule.id,
                        "message": str(e)
                    }
                    self.errors.append(error)
                    logger.error(f"Error formalizing rule {rule.id}: {str(e)}")
            
            logger.info(f"Formalized {formalized_count}/{len(self.rules)} rules")
        else:
            logger.warning("Azure OpenAI is not available. Skipping rule formalization.")
        
        # Record formalization time
        self.metrics["formalization_time"] = time.time() - formalization_start
    
    def _verify_rules(self):
        """Verify rules using Z3 theorem prover."""
        logger.info("\n=== STEP 3: VERIFYING RULES WITH Z3 ===")
        
        verification_start = time.time()
        
        verified_count = 0
        valid_count = 0
        invalid_count = 0
        unknown_count = 0
        
        for rule in self.rules:
            if hasattr(rule, 'formalized_condition') and rule.formalized_condition:
                try:
                    verification_result = self.rule_verifier.verify(rule, self.specification)
                    setattr(rule, 'verification_result', verification_result)
                    logger.info(f"Verified rule {rule.id}: {verification_result.status}")
                    
                    verified_count += 1
                    if verification_result.status == "valid":
                        valid_count += 1
                    elif verification_result.status == "invalid":
                        invalid_count += 1
                    else:
                        unknown_count += 1
                except Exception as e:
                    error = {
                        "error_type": "verification_error",
                        "rule_id": rule.id,
                        "message": str(e)
                    }
                    self.errors.append(error)
                    logger.error(f"Error verifying rule {rule.id}: {str(e)}")
        
        logger.info(f"Verified {verified_count}/{len(self.rules)} rules")
        logger.info(f"  Valid: {valid_count}")
        logger.info(f"  Invalid: {invalid_count}")
        logger.info(f"  Unknown: {unknown_count}")
        
        # Record verification time
        self.metrics["verification_time"] = time.time() - verification_start
    
    def _generate_tests(self):
        """Generate test cases using multiple techniques."""
        logger.info("\n=== STEP 4: GENERATING TEST CASES ===")
        
        test_generation_start = time.time()
        
        # Configure test generator with all techniques
        test_techniques = ["metamorphic", "symbolic", "adversarial", "causal"]
        if self.llm_orchestrator.is_available:
            test_techniques.append("llm")
        
        # Only use rules that have been formalized for test generation
        formalized_rules = [rule for rule in self.rules if hasattr(rule, 'formalized_condition') and rule.formalized_condition]
        
        if formalized_rules:
            logger.info(f"Generating tests for {len(formalized_rules)} formalized rules using techniques: {', '.join(test_techniques)}")
            
            # Generate tests for each rule individually to better track statistics
            all_test_cases = []
            
            for rule in formalized_rules:
                logger.info(f"Generating tests for rule {rule.id}...")
                
                # Initialize statistics for this rule
                self.test_stats[rule.id] = {technique: 0 for technique in test_techniques}
                
                # Generate tests using each technique individually
                for technique in test_techniques:
                    try:
                        logger.info(f"  Using {technique} technique...")
                        rule_test_cases = self.test_generator.generate_tests(
                            [rule], 
                            self.specification, 
                            parallel=False, 
                            techniques=[technique]
                        )
                        
                        # Count tests by technique
                        technique_count = sum(1 for test in rule_test_cases if hasattr(test, 'technique') and test.technique == technique)
                        self.test_stats[rule.id][technique] = technique_count
                        
                        logger.info(f"  Generated {technique_count} {technique} test cases")
                        all_test_cases.extend(rule_test_cases)
                    except Exception as e:
                        error = {
                            "error_type": f"{technique}_test_generation_error",
                            "rule_id": rule.id,
                            "message": str(e)
                        }
                        self.errors.append(error)
                        logger.error(f"Error generating {technique} tests for rule {rule.id}: {str(e)}")
            
            self.test_cases = all_test_cases
            logger.info(f"Generated {len(self.test_cases)} test cases in total")
            
            # Print test statistics
            logger.info("\nTest case statistics by technique:")
            for technique in test_techniques:
                technique_count = sum(stats[technique] for stats in self.test_stats.values())
                logger.info(f"  {technique}: {technique_count} test cases")
        else:
            logger.warning("No formalized rules available for test generation.")
        
        # Record test generation time
        self.metrics["test_generation_time"] = time.time() - test_generation_start
    
    def _generate_reports(self, output_dir: str):
        """Generate reports and visualizations."""
        logger.info("\n=== STEP 5: GENERATING REPORTS AND VISUALIZATIONS ===")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Export validation results
        validation_file = os.path.join(output_dir, "validation_results.json")
        validation_results = []
        for rule in self.rules:
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
        for test in self.test_cases:
            # Handle both TestCase objects and string test cases
            if isinstance(test, str):
                test_export = {
                    "description": test,
                    "rule_id": "unknown",
                    "expected_result": "unknown",
                    "test_data": {},
                    "technique": "unknown"
                }
            else:
                test_export = {
                    "rule_id": getattr(test, 'rule_id', 'unknown'),
                    "description": getattr(test, 'description', str(test)),
                    "expected_result": getattr(test, 'expected_result', 'unknown'),
                    "test_data": getattr(test, 'test_data', {}),
                    "technique": getattr(test, 'technique', 'unknown')
                }
            test_cases_export.append(test_export)
        
        with open(test_cases_file, "w") as f:
            json.dump(test_cases_export, f, indent=2)
        
        # Export performance metrics
        metrics_file = os.path.join(output_dir, "performance_metrics.json")
        with open(metrics_file, "w") as f:
            json.dump(self.metrics, f, indent=2)
        
        # Export test statistics
        stats_file = os.path.join(output_dir, "test_statistics.json")
        with open(stats_file, "w") as f:
            json.dump(self.test_stats, f, indent=2)
        
        logger.info(f"Reports and visualizations exported to {output_dir}")
    
    def _print_summary(self):
        """Print a summary of the demonstration results."""
        logger.info("\n" + "=" * 80)
        logger.info("DEMONSTRATION SUMMARY")
        logger.info("=" * 80)
        
        # Rules summary
        logger.info(f"Rules: {len(self.rules)} total")
        formalized_count = sum(1 for rule in self.rules if hasattr(rule, 'formalized_condition') and rule.formalized_condition)
        if len(self.rules) > 0:
            logger.info(f"  Formalized: {formalized_count} ({formalized_count/len(self.rules)*100:.1f}%)")
            
            verified_count = sum(1 for rule in self.rules if hasattr(rule, 'verification_result'))
            logger.info(f"  Verified: {verified_count} ({verified_count/len(self.rules)*100:.1f}%)")
        
        # Test cases summary
        logger.info(f"Test Cases: {len(self.test_cases)} total")
        
        # Group test cases by technique
        technique_counts = {}
        for test in self.test_cases:
            technique = getattr(test, 'technique', 'unknown')
            if technique not in technique_counts:
                technique_counts[technique] = 0
            technique_counts[technique] += 1
        
        # Print test cases by technique
        if self.test_cases:
            for technique, count in technique_counts.items():
                logger.info(f"  {technique}: {count} ({count/len(self.test_cases)*100:.1f}%)")
        
        # Performance summary
        logger.info("\nPerformance:")
        logger.info(f"  Total time: {self.metrics['total_time']:.2f} seconds")
        if self.metrics['total_time'] > 0:
            logger.info(f"  Parsing: {self.metrics['parsing_time']:.2f} seconds ({self.metrics['parsing_time']/self.metrics['total_time']*100:.1f}%)")
            logger.info(f"  Formalization: {self.metrics['formalization_time']:.2f} seconds ({self.metrics['formalization_time']/self.metrics['total_time']*100:.1f}%)")
            logger.info(f"  Verification: {self.metrics['verification_time']:.2f} seconds ({self.metrics['verification_time']/self.metrics['total_time']*100:.1f}%)")
            logger.info(f"  Test Generation: {self.metrics['test_generation_time']:.2f} seconds ({self.metrics['test_generation_time']/self.metrics['total_time']*100:.1f}%)")
        
        # Errors summary
        if self.errors:
            logger.info(f"\nErrors: {len(self.errors)} total")
            error_types = {}
            for error in self.errors:
                error_type = error.get('error_type', 'unknown')
                if error_type not in error_types:
                    error_types[error_type] = 0
                error_types[error_type] += 1
            
            for error_type, count in error_types.items():
                logger.info(f"  {error_type}: {count}")
        else:
            logger.info("\nErrors: None")
        
        logger.info("\n" + "=" * 80)
        logger.info("DEMONSTRATION COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)


def main():
    """Run the full Excel demonstration."""
    # Define file paths
    rules_file = "tests/data/sample_rules.xlsx"
    spec_file = "tests/data/sample_specification.xlsx"
    output_dir = "output/full_excel_demo"
    
    # Create and run the demo
    demo = FullExcelDemo()
    demo.run(rules_file, spec_file, output_dir)


if __name__ == "__main__":
    main()
