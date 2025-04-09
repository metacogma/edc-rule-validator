#!/usr/bin/env python
"""
Advanced Test Generation Demo for Edit Check Rule Validation System.

This script demonstrates how to use the advanced test generation techniques
implemented in the system to generate robust test cases for clinical trial rules.
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add the parent directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.models.data_models import EditCheckRule, StudySpecification
from src.parsers.unified_parser import UnifiedParser
from src.test_generation.test_generator import TestGenerator
from src.llm.llm_orchestrator import LLMOrchestrator
from src.utils.logger import Logger

logger = Logger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Advanced Test Generation Demo')
    parser.add_argument('--rules', type=str, required=True, help='Path to the rules file')
    parser.add_argument('--spec', type=str, required=True, help='Path to the specification file')
    parser.add_argument('--output', type=str, default='test_cases.json', help='Path to output file')
    parser.add_argument('--techniques', type=str, nargs='+', 
                        default=['metamorphic', 'symbolic', 'adversarial', 'causal'],
                        help='Test generation techniques to use')
    parser.add_argument('--parallel', action='store_true', help='Run test generation in parallel')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    return parser.parse_args()

def main():
    """Run the advanced test generation demo."""
    args = parse_arguments()
    
    if args.verbose:
        Logger.set_level('DEBUG')
    
    logger.info("Starting advanced test generation demo")
    logger.info(f"Rules file: {args.rules}")
    logger.info(f"Specification file: {args.spec}")
    logger.info(f"Output file: {args.output}")
    logger.info(f"Techniques: {', '.join(args.techniques)}")
    logger.info(f"Parallel execution: {args.parallel}")
    
    # Parse the rules and specification files
    parser = UnifiedParser()
    
    logger.info("Parsing specification file...")
    spec, spec_errors = parser.parse_file(args.spec, "specification")
    if spec_errors:
        for error in spec_errors:
            logger.error(f"Specification error: {error}")
        sys.exit(1)
    
    if not spec:
        logger.error("Failed to parse specification file")
        sys.exit(1)
    
    logger.info("Parsing rules file...")
    rules, rule_errors = parser.parse_file(args.rules, "rules")
    if rule_errors:
        for error in rule_errors:
            logger.error(f"Rule error: {error}")
    
    if not rules:
        logger.error("Failed to parse rules file or no rules found")
        sys.exit(1)
    
    logger.info(f"Parsed {len(rules)} rules and specification successfully")
    
    # Initialize the test generator
    llm_orchestrator = LLMOrchestrator()
    test_generator = TestGenerator(llm_orchestrator)
    
    # Generate test cases
    logger.info("Generating test cases...")
    all_tests = test_generator.generate_tests(
        rules,
        spec,
        parallel=args.parallel,
        techniques=args.techniques
    )
    
    # Count total test cases
    total_tests = sum(len(tests) for tests in all_tests.values())
    logger.info(f"Generated a total of {total_tests} test cases across {len(rules)} rules")
    
    # Prepare results for export
    results = {}
    for rule_id, tests in all_tests.items():
        results[rule_id] = [test.dict() for test in tests]
    
    # Export test cases to JSON
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Test cases exported to {args.output}")
    
    # Print summary
    print("\n===== Test Generation Summary =====")
    print(f"Total rules: {len(rules)}")
    print(f"Total test cases: {total_tests}")
    print(f"Techniques used: {', '.join(args.techniques)}")
    print(f"Test cases per rule:")
    for rule_id, tests in all_tests.items():
        print(f"  Rule {rule_id}: {len(tests)} test cases")
    print(f"Test cases exported to {args.output}")
    print("==================================\n")
    
    # Print example test case
    if total_tests > 0:
        rule_id = next(iter(all_tests.keys()))
        test = all_tests[rule_id][0]
        print("Example test case:")
        print(f"  Rule ID: {test.rule_id}")
        print(f"  Description: {test.description}")
        print(f"  Expected result: {test.expected_result}")
        print(f"  Test data: {json.dumps(test.test_data, indent=2)}")

if __name__ == "__main__":
    main()
