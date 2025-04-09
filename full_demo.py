#!/usr/bin/env python
"""
Full End-to-End Demo for the Edit Check Rule Validation System.

This script demonstrates all the advanced features of the system including:
1. LLM-based rule formalization
2. Advanced test generation techniques (metamorphic, symbolic, adversarial, causal, LLM)
3. Z3-based verification
"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import components
from src.parsers.json_rule_parser import JSONRuleParser
from src.parsers.json_specification_parser import JSONSpecificationParser
from src.llm.llm_orchestrator_updated import LLMOrchestrator
from src.test_generation.test_generator import TestGenerator
from src.verification.rule_verifier import RuleVerifier
from src.models.data_models import EditCheckRule, StudySpecification, TestCase, FieldType, Form, Field

def create_sample_rules():
    """Create sample rules for demonstration."""
    rules = []
    
    # Rule 1: Systolic BP > Diastolic BP
    rule1 = EditCheckRule(
        id="VS_F_001_2024R1U0",
        condition="Systolic blood pressure is less than diastolic blood pressure."
    )
    rule1.formalized_condition = "(VitalSigns.SystolicBP <= VitalSigns.DiastolicBP)"
    rule1.forms = ["VitalSigns"]
    rule1.fields = ["SystolicBP", "DiastolicBP"]
    rules.append(rule1)
    
    # Rule 2: Age range check
    rule2 = EditCheckRule(
        id="DM_F_003_2024R1U0",
        condition="If gender is 'Female' and age is less than 50, then pregnancy test result must not be null."
    )
    rule2.formalized_condition = "IF (Demographics.Gender = 'Female') AND (Demographics.Age < 50) THEN (PregnancyTest.Result IS NOT NULL)"
    rule2.forms = ["Demographics", "PregnancyTest"]
    rule2.fields = ["Gender", "Age", "Result"]
    rules.append(rule2)
    
    # Rule 3: Date difference check
    rule3 = EditCheckRule(
        id="AE_F_002_2024R1U0",
        condition="If Adverse Event start time is not null, and Study Treatment Administration end time is null, then the difference between Adverse Event date and Overall Max Study Treatment Date per subject is less than or equal to 140 days."
    )
    rule3.formalized_condition = "IF (AdverseEvent.StartTime IS NOT NULL) AND (StudyTreatmentAdministration.EndTime IS NULL) THEN DATE_DIFF(AdverseEvent.Date, StudyTreatmentAdministration.OverallMaxStudyTreatmentDatePerSubject) <= 140 ELSE REMOVE_RULE"
    rule3.forms = ["AdverseEvent", "StudyTreatmentAdministration"]
    rule3.fields = ["StartTime", "EndTime", "Date", "OverallMaxStudyTreatmentDatePerSubject"]
    rules.append(rule3)
    
    return rules

def create_sample_specification():
    """Create sample study specification for demonstration."""
    forms = {}
    
    # VitalSigns form
    vs_fields = [
        Field(name="SystolicBP", label="Systolic Blood Pressure", type=FieldType.NUMERIC),
        Field(name="DiastolicBP", label="Diastolic Blood Pressure", type=FieldType.NUMERIC)
    ]
    # Set min/max values
    vs_fields[0].min_value = 60
    vs_fields[0].max_value = 250
    vs_fields[1].min_value = 30
    vs_fields[1].max_value = 150
    
    forms["VitalSigns"] = Form(
        name="VitalSigns",
        label="Vital Signs Form",
        fields=vs_fields
    )
    
    # Demographics form
    dm_fields = [
        Field(name="Gender", label="Gender", type=FieldType.CATEGORICAL),
        Field(name="Age", label="Age", type=FieldType.NUMERIC)
    ]
    # Set valid values and min/max
    dm_fields[0].valid_values = ["Male", "Female", "Other"]
    dm_fields[1].min_value = 18
    dm_fields[1].max_value = 99
    
    forms["Demographics"] = Form(
        name="Demographics",
        label="Demographics Form",
        fields=dm_fields
    )
    
    # PregnancyTest form
    pt_fields = [
        Field(name="Result", label="Pregnancy Test Result", type=FieldType.CATEGORICAL)
    ]
    # Set valid values
    pt_fields[0].valid_values = ["Positive", "Negative", "Indeterminate"]
    
    forms["PregnancyTest"] = Form(
        name="PregnancyTest",
        label="Pregnancy Test Form",
        fields=pt_fields
    )
    
    # AdverseEvent form
    ae_fields = [
        Field(name="StartTime", label="Start Time", type=FieldType.TIME),
        Field(name="Date", label="Adverse Event Date", type=FieldType.DATE)
    ]
    
    forms["AdverseEvent"] = Form(
        name="AdverseEvent",
        label="Adverse Event Form",
        fields=ae_fields
    )
    
    # StudyTreatmentAdministration form
    sta_fields = [
        Field(name="EndTime", label="End Time", type=FieldType.TIME),
        Field(name="OverallMaxStudyTreatmentDatePerSubject", label="Overall Max Study Treatment Date Per Subject", type=FieldType.DATE)
    ]
    
    forms["StudyTreatmentAdministration"] = Form(
        name="StudyTreatmentAdministration",
        label="Study Treatment Administration Form",
        fields=sta_fields
    )
    
    return StudySpecification(forms=forms)

def run_full_demo():
    """Run the full end-to-end demo."""
    logger.info("Starting full end-to-end demo of the Edit Check Rule Validation System...")
    
    # Step 1: Create or load rules and specification
    logger.info("\n=== STEP 1: PREPARING RULES AND SPECIFICATION ===")
    
    # Check if we have JSON data files
    json_rules_file = "data/rules.json"
    json_spec_file = "data/specification.json"
    
    if os.path.exists(json_rules_file) and os.path.exists(json_spec_file):
        logger.info("Using JSON data files for rules and specification")
        json_rule_parser = JSONRuleParser()
        json_spec_parser = JSONSpecificationParser()
        
        rules = json_rule_parser.parse(json_rules_file)
        specification = json_spec_parser.parse(json_spec_file)
        
        logger.info(f"Loaded {len(rules)} rules from JSON file")
        logger.info(f"Loaded specification with {len(specification.forms)} forms from JSON file")
    else:
        logger.info("Creating sample rules and specification for demonstration")
        rules = create_sample_rules()
        specification = create_sample_specification()
        
        logger.info(f"Created {len(rules)} sample rules")
        logger.info(f"Created specification with {len(specification.forms)} forms")
    
    # Print sample rules
    for i, rule in enumerate(rules[:3], 1):
        logger.info(f"Rule {i}: {rule.id}")
        logger.info(f"  Condition: {rule.condition}")
        if hasattr(rule, 'formalized_condition') and rule.formalized_condition:
            logger.info(f"  Formalized: {rule.formalized_condition}")
    
    if len(rules) > 3:
        logger.info(f"  ... and {len(rules) - 3} more rules")
    
    # Step 2: Formalize rules with LLM
    logger.info("\n=== STEP 2: FORMALIZING RULES WITH LLM ===")
    start_time = time.time()
    llm_orchestrator = LLMOrchestrator()
    
    if llm_orchestrator.is_available:
        logger.info("Azure OpenAI is available. Proceeding with rule formalization...")
        formalized_count = 0
        
        for rule in rules:
            # Skip rules that are already formalized
            if hasattr(rule, 'formalized_condition') and rule.formalized_condition:
                logger.info(f"Rule {rule.id} is already formalized")
                formalized_count += 1
                continue
                
            try:
                formalized_condition = llm_orchestrator.formalize_rule(rule, specification)
                if formalized_condition:
                    setattr(rule, 'formalized_condition', formalized_condition)
                    logger.info(f"Formalized rule {rule.id}")
                    logger.info(f"  Original: {rule.condition}")
                    logger.info(f"  Formalized: {formalized_condition}")
                    formalized_count += 1
                else:
                    logger.warning(f"Failed to formalize rule {rule.id}")
            except Exception as e:
                logger.error(f"Error formalizing rule {rule.id}: {str(e)}")
        
        logger.info(f"Formalized {formalized_count} rules in {time.time() - start_time:.2f} seconds")
    else:
        logger.warning("Azure OpenAI is not available. Skipping rule formalization for non-formalized rules.")
    
    # Step 3: Verify rules with Z3
    logger.info("\n=== STEP 3: VERIFYING RULES WITH Z3 ===")
    start_time = time.time()
    verifier = RuleVerifier()
    verified_count = 0
    
    for rule in rules:
        if hasattr(rule, 'formalized_condition') and rule.formalized_condition:
            try:
                verification_result = verifier.verify(rule, specification)
                setattr(rule, 'verification_result', verification_result)
                logger.info(f"Verified rule {rule.id}: {verification_result.status}")
                
                if verification_result.errors:
                    for error in verification_result.errors:
                        logger.warning(f"Verification issue for rule {rule.id}: {error}")
                
                verified_count += 1
            except Exception as e:
                logger.error(f"Error verifying rule {rule.id}: {str(e)}")
    
    logger.info(f"Verified {verified_count} rules in {time.time() - start_time:.2f} seconds")
    
    # Step 4: Generate test cases using individual techniques
    logger.info("\n=== STEP 4: DEMONSTRATING INDIVIDUAL TEST GENERATION TECHNIQUES ===")
    
    # Select a rule for individual technique demonstration
    demo_rule = rules[0]  # Use the first rule
    logger.info(f"Selected rule {demo_rule.id} for technique demonstration:")
    logger.info(f"  Condition: {demo_rule.condition}")
    logger.info(f"  Formalized: {demo_rule.formalized_condition}")
    
    # 4.1: Metamorphic Testing
    logger.info("\n--- Metamorphic Testing ---")
    start_time = time.time()
    from src.test_generation.metamorphic_tester import MetamorphicTester
    metamorphic_tester = MetamorphicTester()
    
    try:
        metamorphic_tests = metamorphic_tester.generate_metamorphic_tests(demo_rule, specification)
        logger.info(f"Generated {len(metamorphic_tests)} metamorphic test cases in {time.time() - start_time:.2f} seconds")
        
        # Print example test cases
        for i, test in enumerate(metamorphic_tests[:2], 1):
            logger.info(f"Test {i}: {test.description}")
            logger.info(f"  Expected Result: {test.expected_result}")
            logger.info(f"  Test Data: {json.dumps(test.test_data, indent=2)}")
    except Exception as e:
        logger.error(f"Error generating metamorphic tests: {str(e)}")
    
    # 4.2: Symbolic Execution
    logger.info("\n--- Symbolic Execution ---")
    start_time = time.time()
    from src.test_generation.symbolic_executor import SymbolicExecutor
    symbolic_executor = SymbolicExecutor()
    
    try:
        symbolic_tests = symbolic_executor.generate_symbolic_tests(demo_rule, specification)
        logger.info(f"Generated {len(symbolic_tests)} symbolic test cases in {time.time() - start_time:.2f} seconds")
        
        # Print example test cases
        for i, test in enumerate(symbolic_tests[:2], 1):
            logger.info(f"Test {i}: {test.description}")
            logger.info(f"  Expected Result: {test.expected_result}")
            logger.info(f"  Test Data: {json.dumps(test.test_data, indent=2)}")
    except Exception as e:
        logger.error(f"Error generating symbolic tests: {str(e)}")
    
    # 4.3: Adversarial Testing
    logger.info("\n--- Adversarial Testing ---")
    start_time = time.time()
    from src.test_generation.adversarial_generator import AdversarialGenerator
    adversarial_generator = AdversarialGenerator()
    
    try:
        adversarial_tests = adversarial_generator.generate_adversarial_tests(demo_rule, specification)
        logger.info(f"Generated {len(adversarial_tests)} adversarial test cases in {time.time() - start_time:.2f} seconds")
        
        # Print example test cases
        for i, test in enumerate(adversarial_tests[:2], 1):
            logger.info(f"Test {i}: {test.description}")
            logger.info(f"  Expected Result: {test.expected_result}")
            logger.info(f"  Test Data: {json.dumps(test.test_data, indent=2)}")
    except Exception as e:
        logger.error(f"Error generating adversarial tests: {str(e)}")
    
    # 4.4: Causal Inference
    logger.info("\n--- Causal Inference ---")
    start_time = time.time()
    from src.test_generation.causal_inference import CausalInferenceGenerator
    causal_generator = CausalInferenceGenerator()
    
    try:
        causal_tests = causal_generator.generate_causal_tests(demo_rule, specification)
        logger.info(f"Generated {len(causal_tests)} causal inference test cases in {time.time() - start_time:.2f} seconds")
        
        # Print example test cases
        for i, test in enumerate(causal_tests[:2], 1):
            logger.info(f"Test {i}: {test.description}")
            logger.info(f"  Expected Result: {test.expected_result}")
            logger.info(f"  Test Data: {json.dumps(test.test_data, indent=2)}")
    except Exception as e:
        logger.error(f"Error generating causal inference tests: {str(e)}")
    
    # 4.5: LLM-based Testing
    logger.info("\n--- LLM-based Testing ---")
    start_time = time.time()
    
    if llm_orchestrator.is_available:
        try:
            llm_tests = llm_orchestrator.generate_test_cases(demo_rule, specification, num_cases=3)
            logger.info(f"Generated {len(llm_tests)} LLM-based test cases in {time.time() - start_time:.2f} seconds")
            
            # Print example test cases
            for i, test in enumerate(llm_tests[:2], 1):
                logger.info(f"Test {i}: {test.description}")
                logger.info(f"  Expected Result: {test.expected_result}")
                logger.info(f"  Test Data: {json.dumps(test.test_data, indent=2)}")
        except Exception as e:
            logger.error(f"Error generating LLM-based tests: {str(e)}")
    else:
        logger.warning("LLM is not available. Skipping LLM-based testing.")
    
    # Step 5: Generate test cases using all techniques combined
    logger.info("\n=== STEP 5: GENERATING TEST CASES WITH ALL TECHNIQUES COMBINED ===")
    start_time = time.time()
    
    # Configure test generator with all techniques
    test_techniques = ["metamorphic", "symbolic", "adversarial", "causal"]
    if llm_orchestrator.is_available:
        test_techniques.append("llm")
    
    test_generator = TestGenerator()
    
    # Generate test cases
    try:
        # Only use rules that have been formalized for test generation
        formalized_rules = [rule for rule in rules if hasattr(rule, 'formalized_condition') and rule.formalized_condition]
        
        if formalized_rules:
            logger.info(f"Generating tests for {len(formalized_rules)} formalized rules using techniques: {', '.join(test_techniques)}")
            test_cases = test_generator.generate_tests(
                formalized_rules, 
                specification, 
                parallel=True, 
                techniques=test_techniques
            )
            
            logger.info(f"Generated {len(test_cases)} test cases in {time.time() - start_time:.2f} seconds")
            
            # Group test cases by technique
            techniques = {}
            for test in test_cases:
                technique = getattr(test, 'technique', 'unknown')
                if technique not in techniques:
                    techniques[technique] = 0
                techniques[technique] += 1
            
            # Print technique breakdown
            logger.info("Test cases by technique:")
            for technique, count in techniques.items():
                logger.info(f"  - {technique}: {count} tests")
            
            # Group test cases by rule
            test_cases_by_rule = {}
            for test in test_cases:
                if test.rule_id not in test_cases_by_rule:
                    test_cases_by_rule[test.rule_id] = []
                test_cases_by_rule[test.rule_id].append(test)
            
            # Print example test cases for each rule
            logger.info("\n=== EXAMPLE TEST CASES ===")
            for rule_id, tests in test_cases_by_rule.items():
                logger.info(f"Rule {rule_id}: {len(tests)} test cases")
                
                # Show one example of each technique for this rule
                shown_techniques = set()
                for test in tests:
                    technique = getattr(test, 'technique', 'unknown')
                    if technique not in shown_techniques and len(shown_techniques) < 5:
                        shown_techniques.add(technique)
                        logger.info(f"  [{technique}] {test.description}")
                        logger.info(f"    Expected Result: {test.expected_result}")
                        logger.info(f"    Test Data: {json.dumps(test.test_data, indent=2)}")
            
            # Export results to JSON
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            
            # Export validation results
            validation_file = os.path.join(output_dir, "validation_results.json")
            validation_results = []
            for rule in rules:
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
            for test in test_cases:
                test_export = {
                    "rule_id": test.rule_id,
                    "description": test.description,
                    "expected_result": test.expected_result,
                    "test_data": test.test_data,
                    "technique": getattr(test, 'technique', 'unknown')
                }
                test_cases_export.append(test_export)
            
            with open(test_cases_file, "w") as f:
                json.dump(test_cases_export, f, indent=2)
            
            logger.info(f"Validation results exported to {validation_file}")
            logger.info(f"Test cases exported to {test_cases_file}")
            
            return test_cases
        else:
            logger.warning("No formalized rules available for test generation.")
            return []
            
    except Exception as e:
        logger.error(f"Error generating test cases: {str(e)}")
        return []

if __name__ == "__main__":
    run_full_demo()
