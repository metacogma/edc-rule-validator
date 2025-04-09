#!/usr/bin/env python
"""
Demonstration of LLM-based rule formalization for Edit Check Rule Validation System.

This script shows how the system uses Azure OpenAI to convert natural language rules
into structured logical expressions.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the necessary components
from src.llm.llm_orchestrator import LLMOrchestrator
from src.models.data_models import EditCheckRule, StudySpecification, Form, Field, FieldType, RuleSeverity
from src.parsers.custom_parser import CustomParser

def main():
    """Run a demonstration of LLM-based rule formalization."""
    # Load environment variables
    load_dotenv()
    
    # Check if Azure OpenAI API key is available
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("Azure OpenAI API key not found in .env file. Cannot run formalization demo.")
        sys.exit(1)
    
    logger.info("Starting LLM-based rule formalization demo...")
    
    # Create LLM orchestrator
    llm_orchestrator = LLMOrchestrator()
    
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
    
    # Parse files
    parser = CustomParser()
    spec, spec_errors = parser.parse_specification(spec_file)
    rules, rule_errors = parser.parse_rules(rules_file)
    
    if not rules:
        logger.error("Failed to parse rules file or no rules found")
        sys.exit(1)
    
    # Select a few rules for demonstration
    demo_rules = rules[:5]  # First 5 rules
    
    # Formalize each rule
    logger.info(f"Formalizing {len(demo_rules)} rules...")
    
    for i, rule in enumerate(demo_rules, 1):
        logger.info(f"\nRule {i}: {rule.id}")
        logger.info(f"Original condition: {rule.condition}")
        
        # Formalize the rule
        formalized_condition = llm_orchestrator.formalize_rule(rule, spec)
        
        if formalized_condition:
            logger.info(f"Formalized condition: {formalized_condition}")
            
            # Store the formalized condition in the rule
            setattr(rule, 'formalized_condition', formalized_condition)
        else:
            logger.warning(f"Failed to formalize rule {rule.id}")
    
    # Generate test cases for a rule using the formalized condition
    if demo_rules and hasattr(demo_rules[0], 'formalized_condition'):
        rule = demo_rules[0]
        logger.info(f"\nGenerating test cases for rule {rule.id}...")
        
        # Generate test cases
        test_cases = llm_orchestrator.generate_test_cases(rule, spec, num_cases=3)
        
        if test_cases:
            logger.info(f"Generated {len(test_cases)} test cases:")
            for j, test in enumerate(test_cases, 1):
                logger.info(f"  Test {j}: {test.description}")
                logger.info(f"    Expected result: {test.expected_result}")
                logger.info(f"    Test data: {test.test_data}")
        else:
            logger.warning(f"Failed to generate test cases for rule {rule.id}")
    
    logger.info("\nLLM-based rule formalization demo completed")

if __name__ == "__main__":
    main()
