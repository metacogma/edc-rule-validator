#!/usr/bin/env python
"""
Integration tests for advanced test generation techniques.

This module tests the integration of advanced test generation techniques
with the workflow orchestrator to ensure they work seamlessly together.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.models.data_models import EditCheckRule, StudySpecification, TestCase
from src.workflow.workflow_orchestrator import WorkflowOrchestrator
from src.test_generation.test_generator import TestGenerator
from src.test_generation.metamorphic_tester import MetamorphicTester
from src.test_generation.symbolic_executor import SymbolicExecutor
from src.test_generation.adversarial_generator import AdversarialTestGenerator
from src.test_generation.causal_inference import CausalInferenceGenerator
from src.test_generation.multimodal_verifier import MultiModalVerifier


class TestAdvancedTestGeneration(unittest.TestCase):
    """Test the integration of advanced test generation techniques with the workflow orchestrator."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a sample rule
        self.rule = EditCheckRule(
            id="R001",
            description="Test rule",
            condition="AGE > 18 AND GENDER = 'MALE'",
            error_message="Subject must be an adult male",
            formalized_condition="(AGE > 18) and (GENDER == 'MALE')"
        )
        
        # Create a sample specification
        self.spec = StudySpecification(
            study_name="Test Study",
            fields=[
                {"name": "AGE", "type": "INTEGER", "min": 0, "max": 120},
                {"name": "GENDER", "type": "STRING", "allowed_values": ["MALE", "FEMALE", "OTHER"]}
            ]
        )
        
        # Create a mock for the LLM orchestrator
        self.llm_mock = MagicMock()
        self.llm_mock.is_available = True
        
        # Create test cases that would be returned by the test generator
        self.test_cases = {
            "R001": [
                TestCase(
                    rule_id="R001",
                    description="Metamorphic test case - valid data",
                    test_data={"AGE": 25, "GENDER": "MALE"},
                    expected_result=True,
                    technique="metamorphic"
                ),
                TestCase(
                    rule_id="R001",
                    description="Symbolic test case - boundary condition",
                    test_data={"AGE": 18, "GENDER": "MALE"},
                    expected_result=False,
                    technique="symbolic"
                ),
                TestCase(
                    rule_id="R001",
                    description="Adversarial test case - type confusion",
                    test_data={"AGE": "19", "GENDER": "MALE"},
                    expected_result="error",
                    technique="adversarial"
                ),
                TestCase(
                    rule_id="R001",
                    description="Causal test case - intervention",
                    test_data={"AGE": 30, "GENDER": "FEMALE"},
                    expected_result=False,
                    technique="causal"
                )
            ]
        }

    @patch('src.parsers.unified_parser.UnifiedParser')
    @patch('src.validators.rule_validator.RuleValidator')
    @patch('src.validators.z3_verifier.Z3Verifier')
    @patch('src.test_generation.test_generator.TestGenerator')
    def test_workflow_with_advanced_test_generation(self, mock_test_generator, mock_verifier, mock_validator, mock_parser):
        """Test that the workflow orchestrator correctly integrates with advanced test generation."""
        # Set up mocks
        mock_parser_instance = mock_parser.return_value
        mock_parser_instance.parse_file.side_effect = [
            (self.spec, []),  # First call returns specification
            ([self.rule], [])  # Second call returns rules
        ]
        
        mock_validator_instance = mock_validator.return_value
        mock_validator_instance.validate_rules.return_value = [MagicMock(rule_id="R001", is_valid=True)]
        
        mock_verifier_instance = mock_verifier.return_value
        mock_verifier_instance.verify_rules.return_value = [MagicMock(rule_id="R001", is_valid=True)]
        
        mock_test_generator_instance = mock_test_generator.return_value
        mock_test_generator_instance.generate_tests.return_value = self.test_cases
        
        # Create the workflow orchestrator with a configuration that enables advanced test generation
        config = {
            "formalize_rules": True,
            "verify_with_z3": True,
            "generate_tests": True,
            "test_techniques": ["metamorphic", "symbolic", "adversarial", "causal"],
            "parallel_test_generation": False,
            "test_cases_per_rule": 5
        }
        
        orchestrator = WorkflowOrchestrator(config)
        orchestrator.llm_orchestrator = self.llm_mock
        
        # Run the workflow
        result = orchestrator.run("dummy_rules.xlsx", "dummy_spec.xlsx")
        
        # Verify that the test generator was called with the correct parameters
        mock_test_generator_instance.generate_tests.assert_called_once()
        args, kwargs = mock_test_generator_instance.generate_tests.call_args
        self.assertEqual(kwargs["techniques"], ["metamorphic", "symbolic", "adversarial", "causal"])
        self.assertEqual(kwargs["parallel"], False)
        
        # Verify that the test cases were added to the workflow state
        self.assertEqual(len(result.test_cases), 4)
        self.assertEqual(result.test_cases[0].rule_id, "R001")
        self.assertEqual(result.test_cases[0].technique, "metamorphic")
        
        # Verify that we have test cases from each technique
        techniques = [test.technique for test in result.test_cases]
        self.assertIn("metamorphic", techniques)
        self.assertIn("symbolic", techniques)
        self.assertIn("adversarial", techniques)
        self.assertIn("causal", techniques)
        
        # Verify the status of the workflow
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.current_step, "finalize")

    @patch('src.parsers.unified_parser.UnifiedParser')
    @patch('src.validators.rule_validator.RuleValidator')
    @patch('src.validators.z3_verifier.Z3Verifier')
    @patch('src.test_generation.test_generator.TestGenerator')
    def test_fallback_to_llm_when_advanced_generation_fails(self, mock_test_generator, mock_verifier, mock_validator, mock_parser):
        """Test that the workflow falls back to LLM-based test generation when advanced generation fails."""
        # Set up mocks
        mock_parser_instance = mock_parser.return_value
        mock_parser_instance.parse_file.side_effect = [
            (self.spec, []),  # First call returns specification
            ([self.rule], [])  # Second call returns rules
        ]
        
        mock_validator_instance = mock_validator.return_value
        mock_validator_instance.validate_rules.return_value = [MagicMock(rule_id="R001", is_valid=True)]
        
        mock_verifier_instance = mock_verifier.return_value
        mock_verifier_instance.verify_rules.return_value = [MagicMock(rule_id="R001", is_valid=True)]
        
        # Make the test generator raise an exception
        mock_test_generator_instance = mock_test_generator.return_value
        mock_test_generator_instance.generate_tests.side_effect = Exception("Test generation failed")
        
        # Set up LLM mock to return test cases
        llm_test_cases = [
            TestCase(
                rule_id="R001",
                description="LLM generated test case",
                test_data={"AGE": 25, "GENDER": "MALE"},
                expected_result=True
            )
        ]
        self.llm_mock.generate_test_cases.return_value = llm_test_cases
        
        # Create the workflow orchestrator
        orchestrator = WorkflowOrchestrator()
        orchestrator.llm_orchestrator = self.llm_mock
        
        # Run the workflow
        result = orchestrator.run("dummy_rules.xlsx", "dummy_spec.xlsx")
        
        # Verify that the test generator was called
        mock_test_generator_instance.generate_tests.assert_called_once()
        
        # Verify that the LLM orchestrator was called as a fallback
        self.llm_mock.generate_test_cases.assert_called()
        
        # Verify that the LLM test cases were added to the workflow state
        self.assertEqual(len(result.test_cases), 1)
        self.assertEqual(result.test_cases[0].rule_id, "R001")
        
        # Verify that an error was recorded
        self.assertTrue(any(e["error_type"] == "advanced_test_generation_failure" for e in result.errors))
        
        # Verify the status of the workflow
        self.assertEqual(result.status, "completed")

    def test_individual_test_generators(self):
        """Test that each individual test generator can be instantiated and used."""
        # Test MetamorphicTester
        metamorphic_tester = MetamorphicTester()
        self.assertIsNotNone(metamorphic_tester)
        
        # Test SymbolicExecutor
        symbolic_executor = SymbolicExecutor()
        self.assertIsNotNone(symbolic_executor)
        
        # Test AdversarialTestGenerator
        adversarial_generator = AdversarialTestGenerator(self.llm_mock)
        self.assertIsNotNone(adversarial_generator)
        
        # Test CausalInferenceGenerator
        causal_generator = CausalInferenceGenerator()
        self.assertIsNotNone(causal_generator)
        
        # Test MultiModalVerifier
        verifier = MultiModalVerifier()
        self.assertIsNotNone(verifier)


if __name__ == "__main__":
    unittest.main()
