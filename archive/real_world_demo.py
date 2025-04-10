#!/usr/bin/env python
"""
Real-World End-to-End Demo for the Edit Check Rule Validation System.

This script demonstrates the full production workflow of the system, showcasing:
1. Rule and specification parsing from Excel files
2. LLM-based rule formalization using Azure OpenAI
3. Formal verification using Z3 theorem prover
4. Advanced test generation using multiple techniques:
   - Metamorphic Testing
   - Symbolic Execution
   - Adversarial Testing
   - Causal Inference
   - LLM-based Testing
5. Comprehensive results reporting and visualization

This demonstrates how Eclaire Trials uses AI to revolutionize clinical trial data validation.
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
from src.parsers.rule_parser import RuleParser
from src.parsers.specification_parser import SpecificationParser
from src.llm.llm_orchestrator_updated import LLMOrchestrator
from src.test_generation.test_generator import TestGenerator
from src.verification.rule_verifier import RuleVerifier
from src.models.data_models import EditCheckRule, StudySpecification, TestCase

# Eclaire Trials brand colors
ECLAIRE_BLUE = "#0074D9"
ECLAIRE_ORANGE = "#FF9500"
ECLAIRE_PURPLE = "#7F4FBF"

class RealWorldDemo:
    """Real-world demonstration of the Edit Check Rule Validation System."""
    
    def __init__(self):
        """Initialize the demo."""
        self.rule_parser = RuleParser()
        self.spec_parser = SpecificationParser()
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
        Run the full end-to-end demonstration.
        
        Args:
            rules_file: Path to the rules Excel file
            spec_file: Path to the specification Excel file
            output_dir: Directory to save output files
        """
        start_time = time.time()
        
        logger.info("=" * 80)
        logger.info("ECLAIRE TRIALS - EDIT CHECK RULE VALIDATION SYSTEM")
        logger.info("Real-World Enterprise Demonstration")
        logger.info("=" * 80)
        
        # Step 1: Parse rules and specification
        self._parse_files(rules_file, spec_file)
        
        # Step 2: Formalize rules with LLM
        self._formalize_rules()
        
        # Step 3: Verify rules with Z3
        self._verify_rules()
        
        # Step 4: Generate test cases
        self._generate_tests()
        
        # Step 5: Generate reports and visualizations
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
            
            # If no rules were parsed from Excel, use JSON files as fallback
            if len(self.rules) == 0:
                json_rules_file = "data/rules.json"
                if os.path.exists(json_rules_file):
                    from src.parsers.json_rule_parser import JSONRuleParser
                    json_rule_parser = JSONRuleParser()
                    self.rules = json_rule_parser.parse(json_rules_file)
                    logger.info(f"Fallback: Parsed {len(self.rules)} rules from JSON file")
        except Exception as e:
            error = {
                "error_type": "rule_parsing_error",
                "message": str(e)
            }
            self.errors.append(error)
            logger.error(f"Error parsing rules: {str(e)}")
            
            # Try to use JSON files as fallback
            json_rules_file = "data/rules.json"
            if os.path.exists(json_rules_file):
                from src.parsers.json_rule_parser import JSONRuleParser
                json_rule_parser = JSONRuleParser()
                self.rules = json_rule_parser.parse(json_rules_file)
                logger.info(f"Fallback: Parsed {len(self.rules)} rules from JSON file")
        
        # Parse specification
        logger.info(f"Parsing specification from {spec_file}...")
        try:
            self.specification = self.spec_parser.parse(spec_file)
            logger.info(f"Successfully parsed specification with {len(self.specification.forms)} forms")
            
            # If no forms were parsed from Excel, use JSON file as fallback
            if len(self.specification.forms) == 0:
                json_spec_file = "data/specification.json"
                if os.path.exists(json_spec_file):
                    from src.parsers.json_specification_parser import JSONSpecificationParser
                    json_spec_parser = JSONSpecificationParser()
                    self.specification = json_spec_parser.parse(json_spec_file)
                    logger.info(f"Fallback: Parsed specification with {len(self.specification.forms)} forms from JSON file")
        except Exception as e:
            error = {
                "error_type": "specification_parsing_error",
                "message": str(e)
            }
            self.errors.append(error)
            logger.error(f"Error parsing specification: {str(e)}")
            
            # Try to use JSON file as fallback
            json_spec_file = "data/specification.json"
            if os.path.exists(json_spec_file):
                from src.parsers.json_specification_parser import JSONSpecificationParser
                json_spec_parser = JSONSpecificationParser()
                self.specification = json_spec_parser.parse(json_spec_file)
                logger.info(f"Fallback: Parsed specification with {len(self.specification.forms)} forms from JSON file")
        
        # Record parsing time
        self.metrics["parsing_time"] = time.time() - parsing_start
        
        # Print sample rules
        for i, rule in enumerate(self.rules[:3], 1):
            logger.info(f"Rule {i}: {rule.id}")
            logger.info(f"  Condition: {rule.condition}")
        
        if len(self.rules) > 3:
            logger.info(f"  ... and {len(self.rules) - 3} more rules")
    
    def _formalize_rules(self):
        """Formalize rules using LLM."""
        logger.info("\n=== STEP 2: FORMALIZING RULES WITH LLM ===")
        
        formalization_start = time.time()
        
        if self.llm_orchestrator.is_available:
            logger.info("Azure OpenAI is available. Proceeding with rule formalization...")
            formalized_count = 0
            
            for rule in self.rules:
                # Skip rules that are already formalized
                if hasattr(rule, 'formalized_condition') and rule.formalized_condition:
                    logger.info(f"Rule {rule.id} is already formalized")
                    formalized_count += 1
                    continue
                    
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
                    
                    if verification_result.errors:
                        for error in verification_result.errors:
                            logger.warning(f"Verification issue for rule {rule.id}: {error}")
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
        
        # Generate visualizations if matplotlib is available
        try:
            # Create test technique distribution chart
            self._create_test_technique_chart(output_dir)
            
            # Create performance metrics chart
            self._create_performance_chart(output_dir)
            
            # Create verification results chart
            self._create_verification_chart(output_dir)
        except Exception as e:
            logger.error(f"Error generating visualizations: {str(e)}")
        
        logger.info(f"Reports and visualizations exported to {output_dir}")
    
    def _create_test_technique_chart(self, output_dir: str):
        """Create a chart showing test case distribution by technique."""
        if not self.test_stats:
            return
        
        # Count tests by technique
        techniques = ["metamorphic", "symbolic", "adversarial", "causal", "llm"]
        technique_counts = {}
        
        for technique in techniques:
            technique_counts[technique] = sum(
                stats.get(technique, 0) for stats in self.test_stats.values()
            )
        
        # Filter out techniques with zero tests
        technique_counts = {k: v for k, v in technique_counts.items() if v > 0}
        
        # Create bar chart
        plt.figure(figsize=(10, 6))
        bars = plt.bar(technique_counts.keys(), technique_counts.values(), color=[ECLAIRE_BLUE, ECLAIRE_ORANGE, ECLAIRE_PURPLE, "#4CAF50", "#9C27B0"])
        
        # Add labels
        plt.title("Test Cases by Generation Technique", fontsize=16)
        plt.xlabel("Technique", fontsize=14)
        plt.ylabel("Number of Test Cases", fontsize=14)
        
        # Add count labels on top of bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{height:.0f}', ha='center', va='bottom', fontsize=12)
        
        # Save chart
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "test_technique_distribution.png"))
        plt.close()
    
    def _create_performance_chart(self, output_dir: str):
        """Create a chart showing performance metrics."""
        # Extract relevant metrics
        metrics = {
            "Parsing": self.metrics["parsing_time"],
            "Formalization": self.metrics["formalization_time"],
            "Verification": self.metrics["verification_time"],
            "Test Generation": self.metrics["test_generation_time"]
        }
        
        # Create bar chart
        plt.figure(figsize=(10, 6))
        bars = plt.bar(metrics.keys(), metrics.values(), color=[ECLAIRE_BLUE, ECLAIRE_ORANGE, ECLAIRE_PURPLE, "#4CAF50"])
        
        # Add labels
        plt.title("Performance Metrics by Stage", fontsize=16)
        plt.xlabel("Stage", fontsize=14)
        plt.ylabel("Time (seconds)", fontsize=14)
        
        # Add time labels on top of bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{height:.1f}s', ha='center', va='bottom', fontsize=12)
        
        # Save chart
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "performance_metrics.png"))
        plt.close()
    
    def _create_verification_chart(self, output_dir: str):
        """Create a chart showing verification results."""
        # Count verification results
        results = {"Valid": 0, "Invalid": 0, "Unknown": 0, "Not Verified": 0}
        
        for rule in self.rules:
            if hasattr(rule, 'verification_result'):
                status = rule.verification_result.status.capitalize()
                if status in results:
                    results[status] += 1
                else:
                    results["Unknown"] += 1
            else:
                results["Not Verified"] += 1
        
        # Create pie chart
        plt.figure(figsize=(10, 8))
        colors = [ECLAIRE_BLUE, ECLAIRE_ORANGE, ECLAIRE_PURPLE, "#E91E63"]
        explode = (0.1, 0, 0, 0)  # explode the 1st slice (Valid)
        
        plt.pie(results.values(), explode=explode, labels=results.keys(), colors=colors,
                autopct='%1.1f%%', shadow=True, startangle=140)
        
        # Add title
        plt.title("Rule Verification Results", fontsize=16)
        
        # Equal aspect ratio ensures that pie is drawn as a circle
        plt.axis('equal')
        
        # Save chart
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "verification_results.png"))
        plt.close()
    
    def _print_summary(self):
        """Print a summary of the demonstration results."""
        logger.info("\n" + "=" * 80)
        logger.info("DEMONSTRATION SUMMARY")
        logger.info("=" * 80)
        
        # Rules summary
        logger.info(f"Rules: {len(self.rules)} total")
        formalized_count = sum(1 for rule in self.rules if hasattr(rule, 'formalized_condition') and rule.formalized_condition)
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
        for technique, count in technique_counts.items():
            logger.info(f"  {technique}: {count} ({count/len(self.test_cases)*100:.1f}%)")
        
        # Performance summary
        logger.info("\nPerformance:")
        logger.info(f"  Total time: {self.metrics['total_time']:.2f} seconds")
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
    """Run the real-world demonstration."""
    # Define file paths
    rules_file = "tests/data/sample_rules.xlsx"
    spec_file = "tests/data/sample_specification.xlsx"
    output_dir = "output/real_world_demo"
    
    # Create and run the demo
    demo = RealWorldDemo()
    demo.run(rules_file, spec_file, output_dir)


if __name__ == "__main__":
    main()
