"""
Test Generator Orchestrator for Edit Check Rule Validation System.

This module orchestrates the generation of test cases using multiple advanced techniques
including metamorphic testing, symbolic execution, adversarial testing, and causal inference.
"""

from typing import List, Dict, Any, Optional
import concurrent.futures
from tqdm import tqdm

from ..models.data_models import EditCheckRule, StudySpecification, TestCase
from ..llm.enhanced_llm_orchestrator import EnhancedLLMOrchestrator
from ..utils.logger import Logger
from .metamorphic_tester import MetamorphicTester
from .symbolic_executor import SymbolicExecutor
from .adversarial_generator import AdversarialTestGenerator
from .causal_inference import CausalInferenceGenerator
from .multimodal_verifier import MultiModalVerifier

logger = Logger(__name__)

class TestGenerator:
    """Orchestrate the generation of test cases using multiple advanced techniques."""
    
    def __init__(self, llm_orchestrator: Optional[EnhancedLLMOrchestrator] = None):
        """
        Initialize the test generator.
        
        Args:
            llm_orchestrator: LLM orchestrator for techniques that require LLM
        """
        self.llm_orchestrator = llm_orchestrator
        
        # Initialize test generation techniques
        self.metamorphic_tester = MetamorphicTester()
        self.symbolic_executor = SymbolicExecutor()
        self.adversarial_generator = AdversarialTestGenerator(llm_orchestrator)
        self.causal_inference_generator = CausalInferenceGenerator()
        
        # Initialize the multi-modal verifier
        self.multimodal_verifier = MultiModalVerifier()
        
        # Define the test generation pipeline
        self.test_generation_pipeline = [
            ("metamorphic", self.metamorphic_tester.generate_metamorphic_tests),
            ("symbolic", self.symbolic_executor.generate_symbolic_tests),
            ("adversarial", self.adversarial_generator.generate_adversarial_tests),
            ("causal", self.causal_inference_generator.generate_causal_tests)
        ]
    
    def generate_tests(
        self,
        rules: List[EditCheckRule],
        specification: StudySpecification,
        parallel: bool = True,
        techniques: Optional[List[str]] = None
    ) -> Dict[str, List[TestCase]]:
        """
        Generate test cases for a list of rules.
        
        Args:
            rules: List of rules to generate tests for
            specification: Study specification
            parallel: Whether to generate tests in parallel
            techniques: List of techniques to use (default: all)
            
        Returns:
            Dictionary mapping rule IDs to lists of test cases
        """
        # Filter techniques if specified
        if techniques:
            pipeline = [(name, func) for name, func in self.test_generation_pipeline if name in techniques]
        else:
            pipeline = self.test_generation_pipeline
        
        if parallel:
            return self._generate_tests_parallel(rules, specification, pipeline)
        else:
            return self._generate_tests_sequential(rules, specification, pipeline)
    
    def _generate_tests_sequential(
        self,
        rules: List[EditCheckRule],
        specification: StudySpecification,
        pipeline: List[tuple]
    ) -> Dict[str, List[TestCase]]:
        """
        Generate test cases sequentially.
        
        Args:
            rules: List of rules to generate tests for
            specification: Study specification
            pipeline: Test generation pipeline
            
        Returns:
            Dictionary mapping rule IDs to lists of test cases
        """
        all_tests = {}
        
        for rule in tqdm(rules, desc="Generating tests"):
            rule_tests = []
            
            # Apply each technique
            for technique_name, technique_func in pipeline:
                try:
                    logger.info(f"Generating {technique_name} tests for rule {rule.id}")
                    tests = technique_func(rule, specification)
                    
                    # Add technique name to test descriptions
                    for test in tests:
                        test.description = f"[{technique_name}] {test.description}"
                    
                    rule_tests.extend(tests)
                    logger.info(f"Generated {len(tests)} {technique_name} tests for rule {rule.id}")
                
                except Exception as e:
                    logger.error(f"Error generating {technique_name} tests for rule {rule.id}: {str(e)}")
            
            # Verify and filter tests
            verified_tests = self._verify_tests(rule, specification, rule_tests)
            
            # Store tests for this rule
            all_tests[rule.id] = verified_tests
            logger.info(f"Generated {len(verified_tests)} verified tests for rule {rule.id}")
        
        return all_tests
    
    def _generate_tests_parallel(
        self,
        rules: List[EditCheckRule],
        specification: StudySpecification,
        pipeline: List[tuple]
    ) -> Dict[str, List[TestCase]]:
        """
        Generate test cases in parallel.
        
        Args:
            rules: List of rules to generate tests for
            specification: Study specification
            pipeline: Test generation pipeline
            
        Returns:
            Dictionary mapping rule IDs to lists of test cases
        """
        all_tests = {}
        
        # Create tasks for parallel execution
        tasks = []
        for rule in rules:
            for technique_name, technique_func in pipeline:
                tasks.append((rule, technique_name, technique_func))
        
        # Execute tasks in parallel
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(tasks))) as executor:
            future_to_task = {
                executor.submit(self._execute_technique, rule, technique_name, technique_func, specification): 
                (rule.id, technique_name) 
                for rule, technique_name, technique_func in tasks
            }
            
            for future in tqdm(concurrent.futures.as_completed(future_to_task), 
                              total=len(future_to_task), 
                              desc="Generating tests"):
                rule_id, technique_name = future_to_task[future]
                try:
                    tests = future.result()
                    
                    # Add technique name to test descriptions
                    for test in tests:
                        test.description = f"[{technique_name}] {test.description}"
                    
                    if rule_id not in results:
                        results[rule_id] = []
                    
                    results[rule_id].extend(tests)
                    logger.info(f"Generated {len(tests)} {technique_name} tests for rule {rule_id}")
                
                except Exception as e:
                    logger.error(f"Error generating {technique_name} tests for rule {rule_id}: {str(e)}")
        
        # Verify and filter tests for each rule
        for rule in rules:
            rule_tests = results.get(rule.id, [])
            verified_tests = self._verify_tests(rule, specification, rule_tests)
            all_tests[rule.id] = verified_tests
            logger.info(f"Generated {len(verified_tests)} verified tests for rule {rule.id}")
        
        return all_tests
    
    def _execute_technique(
        self,
        rule: EditCheckRule,
        technique_name: str,
        technique_func: callable,
        specification: StudySpecification
    ) -> List[TestCase]:
        """
        Execute a test generation technique.
        
        Args:
            rule: Rule to generate tests for
            technique_name: Name of the technique
            technique_func: Function to execute
            specification: Study specification
            
        Returns:
            List of test cases
        """
        logger.info(f"Generating {technique_name} tests for rule {rule.id}")
        try:
            tests = technique_func(rule, specification)
            return tests
        except Exception as e:
            logger.error(f"Error in {technique_name} for rule {rule.id}: {str(e)}")
            return []
    
    def _verify_tests(
        self,
        rule: EditCheckRule,
        specification: StudySpecification,
        tests: List[TestCase]
    ) -> List[TestCase]:
        """
        Verify and filter test cases.
        
        Args:
            rule: Rule to verify tests for
            specification: Study specification
            tests: List of test cases to verify
            
        Returns:
            List of verified test cases
        """
        # Skip verification if no tests
        if not tests:
            return []
        
        try:
            # Verify tests using the multi-modal verifier
            verification_results = self.multimodal_verifier.verify_test_cases(rule, specification, tests)
            
            # Filter tests based on verification results
            verified_tests = []
            for test, result in verification_results:
                if result.is_valid:
                    # Update test description with verification result
                    test.description = f"{test.description} [Verified: {result.message}]"
                    verified_tests.append(test)
                else:
                    logger.warning(f"Test case failed verification: {result.message}")
            
            return verified_tests
        
        except Exception as e:
            logger.error(f"Error verifying tests for rule {rule.id}: {str(e)}")
            return tests  # Return all tests if verification fails
    
    def generate_tests_for_rule(
        self,
        rule: EditCheckRule,
        specification: StudySpecification,
        techniques: Optional[List[str]] = None
    ) -> List[TestCase]:
        """
        Generate test cases for a single rule.
        
        Args:
            rule: Rule to generate tests for
            specification: Study specification
            techniques: List of techniques to use (default: all)
            
        Returns:
            List of test cases
        """
        # Filter techniques if specified
        if techniques:
            pipeline = [(name, func) for name, func in self.test_generation_pipeline if name in techniques]
        else:
            pipeline = self.test_generation_pipeline
        
        rule_tests = []
        
        # Apply each technique
        for technique_name, technique_func in pipeline:
            try:
                logger.info(f"Generating {technique_name} tests for rule {rule.id}")
                tests = technique_func(rule, specification)
                
                # Add technique name to test descriptions
                for test in tests:
                    test.description = f"[{technique_name}] {test.description}"
                
                rule_tests.extend(tests)
                logger.info(f"Generated {len(tests)} {technique_name} tests for rule {rule.id}")
            
            except Exception as e:
                logger.error(f"Error generating {technique_name} tests for rule {rule.id}: {str(e)}")
        
        # Verify and filter tests
        verified_tests = self._verify_tests(rule, specification, rule_tests)
        logger.info(f"Generated {len(verified_tests)} verified tests for rule {rule.id}")
        
        return verified_tests
