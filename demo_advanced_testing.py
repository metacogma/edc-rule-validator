#!/usr/bin/env python
"""
Advanced Test Generation Demo for the Edit Check Rule Validation System.

This script demonstrates all the advanced test generation techniques:
1. Metamorphic Testing
2. Symbolic Execution
3. Adversarial Testing (Counterfactual Reasoning)
4. Causal Inference
5. LLM-Based Testing
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
from src.test_generation.metamorphic_tester import MetamorphicTester
from src.test_generation.symbolic_executor import SymbolicExecutor
from src.test_generation.adversarial_generator import AdversarialTestGenerator
from src.test_generation.causal_inference import CausalInferenceGenerator
from src.models.data_models import EditCheckRule, StudySpecification, TestCase, FieldType, Form, Field

def run_advanced_testing_demo():
    """Run the advanced test generation demo."""
    logger.info("Starting advanced test generation demo...")
    
    # Step 1: Load rules and specification from JSON files
    logger.info("\n=== STEP 1: LOADING RULES AND SPECIFICATION ===")
    
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
        logger.error("JSON data files not found. Please run the setup script first.")
        sys.exit(1)
    
    # Step 2: Formalize rules with LLM if not already formalized
    logger.info("\n=== STEP 2: ENSURING RULES ARE FORMALIZED ===")
    llm_orchestrator = LLMOrchestrator()
    
    # Count already formalized rules
    formalized_count = sum(1 for rule in rules if hasattr(rule, 'formalized_condition') and rule.formalized_condition)
    
    if formalized_count < len(rules) and llm_orchestrator.is_available:
        logger.info(f"{formalized_count}/{len(rules)} rules already formalized. Formalizing remaining rules...")
        
        for rule in rules:
            if not hasattr(rule, 'formalized_condition') or not rule.formalized_condition:
                try:
                    formalized_condition = llm_orchestrator.formalize_rule(rule, specification)
                    if formalized_condition:
                        setattr(rule, 'formalized_condition', formalized_condition)
                        logger.info(f"Formalized rule {rule.id}")
                        formalized_count += 1
                except Exception as e:
                    logger.error(f"Error formalizing rule {rule.id}: {str(e)}")
    
    logger.info(f"{formalized_count}/{len(rules)} rules are now formalized")
    
    # Select a rule for demonstration
    if formalized_count > 0:
        # Find a rule that has been formalized
        demo_rule = next((rule for rule in rules if hasattr(rule, 'formalized_condition') and rule.formalized_condition), rules[0])
    else:
        # If no rules are formalized, use the first rule
        demo_rule = rules[0]
        # Add a simple formalized condition if needed
        if not hasattr(demo_rule, 'formalized_condition') or not demo_rule.formalized_condition:
            if demo_rule.id == "VS_F_001_2024R1U0":
                setattr(demo_rule, 'formalized_condition', "(VitalSigns.SystolicBP <= VitalSigns.DiastolicBP)")
            else:
                setattr(demo_rule, 'formalized_condition', "PLACEHOLDER_CONDITION")
    
    logger.info(f"Selected rule {demo_rule.id} for demonstration:")
    logger.info(f"  Condition: {demo_rule.condition}")
    logger.info(f"  Formalized: {demo_rule.formalized_condition}")
    
    # Step 3: Demonstrate individual test generation techniques
    logger.info("\n=== STEP 3: DEMONSTRATING INDIVIDUAL TEST GENERATION TECHNIQUES ===")
    
    # 3.1: Metamorphic Testing
    logger.info("\n--- Metamorphic Testing ---")
    metamorphic_tester = MetamorphicTester()
    
    try:
        metamorphic_tests = metamorphic_tester.generate_metamorphic_tests(demo_rule, specification)
        logger.info(f"Generated {len(metamorphic_tests)} metamorphic test cases")
        
        # Print example test cases
        for i, test in enumerate(metamorphic_tests[:2], 1):
            logger.info(f"Test {i}: {test.description}")
            logger.info(f"  Expected Result: {test.expected_result}")
            logger.info(f"  Test Data: {json.dumps(test.test_data, indent=2)}")
    except Exception as e:
        logger.error(f"Error generating metamorphic tests: {str(e)}")
    
    # 3.2: Symbolic Execution
    logger.info("\n--- Symbolic Execution ---")
    symbolic_executor = SymbolicExecutor()
    
    try:
        symbolic_tests = symbolic_executor.generate_symbolic_tests(demo_rule, specification)
        logger.info(f"Generated {len(symbolic_tests)} symbolic test cases")
        
        # Print example test cases
        for i, test in enumerate(symbolic_tests[:2], 1):
            logger.info(f"Test {i}: {test.description}")
            logger.info(f"  Expected Result: {test.expected_result}")
            logger.info(f"  Test Data: {json.dumps(test.test_data, indent=2)}")
    except Exception as e:
        logger.error(f"Error generating symbolic tests: {str(e)}")
    
    # 3.3: Adversarial Testing
    logger.info("\n--- Adversarial Testing ---")
    adversarial_generator = AdversarialTestGenerator()
    
    try:
        # Check if the method is generate_adversarial_tests or generate_tests
        if hasattr(adversarial_generator, 'generate_adversarial_tests'):
            adversarial_tests = adversarial_generator.generate_adversarial_tests(demo_rule, specification)
        else:
            adversarial_tests = adversarial_generator.generate_tests(demo_rule, specification)
            
        logger.info(f"Generated {len(adversarial_tests)} adversarial test cases")
        
        # Print example test cases
        for i, test in enumerate(adversarial_tests[:2], 1):
            logger.info(f"Test {i}: {test.description}")
            logger.info(f"  Expected Result: {test.expected_result}")
            logger.info(f"  Test Data: {json.dumps(test.test_data, indent=2)}")
    except Exception as e:
        logger.error(f"Error generating adversarial tests: {str(e)}")
    
    # 3.4: Causal Inference
    logger.info("\n--- Causal Inference ---")
    causal_generator = CausalInferenceGenerator()
    
    try:
        # Check if the method is generate_causal_tests or generate_tests
        if hasattr(causal_generator, 'generate_causal_tests'):
            causal_tests = causal_generator.generate_causal_tests(demo_rule, specification)
        else:
            causal_tests = causal_generator.generate_tests(demo_rule, specification)
            
        logger.info(f"Generated {len(causal_tests)} causal inference test cases")
        
        # Print example test cases
        for i, test in enumerate(causal_tests[:2], 1):
            logger.info(f"Test {i}: {test.description}")
            logger.info(f"  Expected Result: {test.expected_result}")
            logger.info(f"  Test Data: {json.dumps(test.test_data, indent=2)}")
    except Exception as e:
        logger.error(f"Error generating causal inference tests: {str(e)}")
    
    # 3.5: LLM-based Testing
    logger.info("\n--- LLM-based Testing ---")
    
    if llm_orchestrator.is_available:
        try:
            llm_tests = llm_orchestrator.generate_test_cases(demo_rule, specification, num_cases=3)
            logger.info(f"Generated {len(llm_tests)} LLM-based test cases")
            
            # Print example test cases
            for i, test in enumerate(llm_tests[:2], 1):
                logger.info(f"Test {i}: {test.description}")
                logger.info(f"  Expected Result: {test.expected_result}")
                logger.info(f"  Test Data: {json.dumps(test.test_data, indent=2)}")
        except Exception as e:
            logger.error(f"Error generating LLM-based tests: {str(e)}")
    else:
        logger.warning("LLM is not available. Skipping LLM-based testing.")
    
    # Step 4: Demonstrate combined test generation with TestGenerator
    logger.info("\n=== STEP 4: DEMONSTRATING COMBINED TEST GENERATION ===")
    
    # Configure test generator with all techniques
    test_techniques = ["metamorphic", "symbolic", "adversarial", "causal"]
    if llm_orchestrator.is_available:
        test_techniques.append("llm")
    
    test_generator = TestGenerator()
    
    try:
        logger.info(f"Generating tests using all techniques: {', '.join(test_techniques)}")
        combined_tests = test_generator.generate_tests(
            [demo_rule], 
            specification, 
            parallel=True, 
            techniques=test_techniques
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
        
        for test in combined_tests:
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
        
    except Exception as e:
        logger.error(f"Error generating combined tests: {str(e)}")
    
    logger.info("\n=== ADVANCED TEST GENERATION DEMO COMPLETED ===")
    logger.info("This demonstration showed how the Edit Check Rule Validation System")
    logger.info("uses multiple advanced techniques to generate comprehensive test cases:")
    logger.info("1. Metamorphic Testing: Creates related test cases that preserve certain properties")
    logger.info("2. Symbolic Execution: Uses Z3 to mathematically derive test cases")
    logger.info("3. Adversarial Testing: Finds edge cases and boundary conditions")
    logger.info("4. Causal Inference: Explores relationships between interdependent fields")
    logger.info("5. LLM-based Testing: Leverages Azure OpenAI to generate realistic test scenarios")
    logger.info("")
    logger.info("Each technique provides unique test cases that complement each other,")
    logger.info("resulting in more comprehensive validation of clinical trial edit check rules.")

if __name__ == "__main__":
    run_advanced_testing_demo()
