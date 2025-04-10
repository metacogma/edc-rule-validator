#!/usr/bin/env python
"""
Advanced Demo for the Edit Check Rule Validation System.

This script demonstrates the advanced test generation techniques
including metamorphic testing, symbolic execution, adversarial testing,
causal inference, and LLM-based testing.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the updated LLM orchestrator
from src.llm.llm_orchestrator_updated import LLMOrchestrator
from src.models.data_models import EditCheckRule, StudySpecification, TestCase, FieldType, Form, Field
from src.test_generation.test_generator import TestGenerator
from src.test_generation.metamorphic_tester import MetamorphicTester
from src.test_generation.symbolic_executor import SymbolicExecutor
from src.test_generation.adversarial_generator import AdversarialGenerator
from src.test_generation.causal_inference import CausalInferenceGenerator

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

def demonstrate_metamorphic_testing(rule, specification):
    """Demonstrate metamorphic testing."""
    logger.info("\n=== METAMORPHIC TESTING ===")
    logger.info(f"Generating metamorphic tests for rule {rule.id}...")
    
    metamorphic_tester = MetamorphicTester()
    test_cases = metamorphic_tester.generate_metamorphic_tests(rule, specification)
    
    logger.info(f"Generated {len(test_cases)} metamorphic test cases")
    
    # Print example test cases
    for i, test in enumerate(test_cases[:3], 1):
        logger.info(f"Test {i}: {test.description}")
        logger.info(f"  Expected Result: {test.expected_result}")
        logger.info(f"  Test Data: {json.dumps(test.test_data, indent=2)}")
    
    return test_cases

def demonstrate_symbolic_execution(rule, specification):
    """Demonstrate symbolic execution."""
    logger.info("\n=== SYMBOLIC EXECUTION ===")
    logger.info(f"Generating symbolic tests for rule {rule.id}...")
    
    symbolic_executor = SymbolicExecutor()
    test_cases = symbolic_executor.generate_symbolic_tests(rule, specification)
    
    logger.info(f"Generated {len(test_cases)} symbolic test cases")
    
    # Print example test cases
    for i, test in enumerate(test_cases[:3], 1):
        logger.info(f"Test {i}: {test.description}")
        logger.info(f"  Expected Result: {test.expected_result}")
        logger.info(f"  Test Data: {json.dumps(test.test_data, indent=2)}")
    
    return test_cases

def demonstrate_adversarial_testing(rule, specification):
    """Demonstrate adversarial testing."""
    logger.info("\n=== ADVERSARIAL TESTING ===")
    logger.info(f"Generating adversarial tests for rule {rule.id}...")
    
    adversarial_generator = AdversarialGenerator()
    test_cases = adversarial_generator.generate_adversarial_tests(rule, specification)
    
    logger.info(f"Generated {len(test_cases)} adversarial test cases")
    
    # Print example test cases
    for i, test in enumerate(test_cases[:3], 1):
        logger.info(f"Test {i}: {test.description}")
        logger.info(f"  Expected Result: {test.expected_result}")
        logger.info(f"  Test Data: {json.dumps(test.test_data, indent=2)}")
    
    return test_cases

def demonstrate_causal_inference(rule, specification):
    """Demonstrate causal inference testing."""
    logger.info("\n=== CAUSAL INFERENCE TESTING ===")
    logger.info(f"Generating causal inference tests for rule {rule.id}...")
    
    causal_generator = CausalInferenceGenerator()
    test_cases = causal_generator.generate_causal_tests(rule, specification)
    
    logger.info(f"Generated {len(test_cases)} causal inference test cases")
    
    # Print example test cases
    for i, test in enumerate(test_cases[:3], 1):
        logger.info(f"Test {i}: {test.description}")
        logger.info(f"  Expected Result: {test.expected_result}")
        logger.info(f"  Test Data: {json.dumps(test.test_data, indent=2)}")
    
    return test_cases

def demonstrate_llm_testing(rule, specification):
    """Demonstrate LLM-based testing."""
    logger.info("\n=== LLM-BASED TESTING ===")
    logger.info(f"Generating LLM-based tests for rule {rule.id}...")
    
    llm_orchestrator = LLMOrchestrator()
    
    if llm_orchestrator.is_available:
        test_cases = llm_orchestrator.generate_test_cases(rule, specification, num_cases=3)
        
        logger.info(f"Generated {len(test_cases)} LLM-based test cases")
        
        # Print example test cases
        for i, test in enumerate(test_cases[:3], 1):
            logger.info(f"Test {i}: {test.description}")
            logger.info(f"  Expected Result: {test.expected_result}")
            logger.info(f"  Test Data: {json.dumps(test.test_data, indent=2)}")
        
        return test_cases
    else:
        logger.warning("LLM is not available. Skipping LLM-based testing.")
        return []

def main():
    """Run the advanced demonstration."""
    logger.info("Starting advanced test generation demonstration...")
    
    # Create sample rules and specification
    rules = create_sample_rules()
    specification = create_sample_specification()
    
    logger.info(f"Created {len(rules)} sample rules")
    
    # Select a rule for demonstration (the vital signs rule is good for showing different techniques)
    demo_rule = rules[0]  # VS_F_001_2024R1U0
    
    logger.info(f"Selected rule {demo_rule.id} for demonstration:")
    logger.info(f"  Condition: {demo_rule.condition}")
    logger.info(f"  Formalized: {demo_rule.formalized_condition}")
    
    # Demonstrate each test generation technique
    all_test_cases = []
    
    # Metamorphic testing
    metamorphic_tests = demonstrate_metamorphic_testing(demo_rule, specification)
    all_test_cases.extend(metamorphic_tests)
    
    # Symbolic execution
    symbolic_tests = demonstrate_symbolic_execution(demo_rule, specification)
    all_test_cases.extend(symbolic_tests)
    
    # Adversarial testing
    adversarial_tests = demonstrate_adversarial_testing(demo_rule, specification)
    all_test_cases.extend(adversarial_tests)
    
    # Causal inference
    causal_tests = demonstrate_causal_inference(demo_rule, specification)
    all_test_cases.extend(causal_tests)
    
    # LLM-based testing
    llm_tests = demonstrate_llm_testing(demo_rule, specification)
    all_test_cases.extend(llm_tests)
    
    # Demonstrate combined test generation
    logger.info("\n=== COMBINED TEST GENERATION ===")
    logger.info("Demonstrating combined test generation with all techniques...")
    
    test_generator = TestGenerator()
    combined_tests = test_generator.generate_tests(
        rules, 
        specification, 
        parallel=True, 
        techniques=["metamorphic", "symbolic", "adversarial", "causal", "llm"]
    )
    
    logger.info(f"Generated {len(combined_tests)} test cases using all techniques")
    
    # Group test cases by technique
    techniques = {}
    for test in combined_tests:
        technique = getattr(test, 'technique', 'unknown')
        if technique not in techniques:
            techniques[technique] = 0
        techniques[technique] += 1
    
    # Print technique breakdown
    logger.info("Test cases by technique:")
    for technique, count in techniques.items():
        logger.info(f"  - {technique}: {count} tests")
    
    # Export results to JSON
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Export test cases
    test_cases_file = os.path.join(output_dir, "advanced_test_cases.json")
    test_cases_export = []
    
    for test in all_test_cases:
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
    
    logger.info(f"Test cases exported to {test_cases_file}")
    
    return all_test_cases

if __name__ == "__main__":
    main()
