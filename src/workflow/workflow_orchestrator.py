"""
LangGraph Workflow Orchestrator for the Edit Check Rule Validation System.

This module provides a workflow orchestration system using LangGraph,
managing state and transitions between parsing, validation, test generation, and export.
"""

import os
from typing import Dict, List, Any, Optional, Union, Tuple, TypedDict, Annotated
# Updated imports for LangGraph 0.3.27
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from ..models.data_models import EditCheckRule, StudySpecification, ValidationResult, TestCase
from ..parsers.unified_parser import UnifiedParser
from ..validators.rule_validator import RuleValidator
from ..validators.z3_verifier import Z3Verifier
from ..llm.llm_orchestrator import LLMOrchestrator
from ..test_generation.test_generator import TestGenerator
from ..utils.logger import Logger

logger = Logger(__name__)

class WorkflowState(BaseModel):
    """State model for the workflow."""
    
    # Input files
    rules_file: Optional[str] = None
    spec_file: Optional[str] = None
    
    # Parsed data
    rules: List[EditCheckRule] = Field(default_factory=list)
    specification: Optional[StudySpecification] = None
    
    # Validation results
    validation_results: List[ValidationResult] = Field(default_factory=list)
    
    # Test cases
    test_cases: List[TestCase] = Field(default_factory=list)
    
    # Error tracking
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Status tracking
    status: str = "initialized"
    current_step: str = "initialization"
    
    # Configuration
    config: Dict[str, Any] = Field(default_factory=dict)


class WorkflowOrchestrator:
    """Orchestrate the validation workflow using LangGraph."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the workflow orchestrator.
        
        Args:
            config: Optional configuration dictionary
        """
        self.parser = UnifiedParser()
        self.validator = RuleValidator()
        self.verifier = Z3Verifier()
        self.llm_orchestrator = LLMOrchestrator()
        self.test_generator = TestGenerator(self.llm_orchestrator)
        
        # Default configuration
        self.config = {
            "formalize_rules": True,
            "verify_with_z3": True,
            "generate_tests": True,
            "test_techniques": ["metamorphic", "symbolic", "adversarial", "causal"],
            "test_cases_per_rule": 5,
            "parallel_test_generation": True,
            "max_retries": 3
        }
        
        # Update with provided config
        if config:
            self.config.update(config)
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self):
        """
        Build the workflow graph.
        
        Returns:
            Compiled StateGraph instance for LangGraph 0.3.27
        """
        # Create a new graph
        workflow = StateGraph(WorkflowState)
        
        # Define nodes
        workflow.add_node("parse_files", self._parse_files)
        workflow.add_node("validate_rules", self._validate_rules)
        workflow.add_node("formalize_rules", self._formalize_rules)
        workflow.add_node("verify_rules", self._verify_rules)
        workflow.add_node("generate_tests", self._generate_tests)
        workflow.add_node("finalize", self._finalize)
        
        # Define edges
        workflow.add_edge("parse_files", "validate_rules")
        
        # Conditional edge based on configuration
        workflow.add_conditional_edges(
            "validate_rules",
            self._should_formalize_rules,
            {
                True: "formalize_rules",
                False: "verify_rules" if self.config["verify_with_z3"] else "generate_tests"
            }
        )
        
        workflow.add_conditional_edges(
            "formalize_rules",
            self._should_verify_rules,
            {
                True: "verify_rules",
                False: "generate_tests" if self.config["generate_tests"] else "finalize"
            }
        )
        
        workflow.add_conditional_edges(
            "verify_rules",
            self._should_generate_tests,
            {
                True: "generate_tests",
                False: "finalize"
            }
        )
        
        workflow.add_edge("generate_tests", "finalize")
        workflow.add_edge("finalize", END)
        
        # Set the entry point
        workflow.set_entry_point("parse_files")
        
        # In LangGraph 0.3.27, we need to compile the graph
        return workflow.compile()
    
    def run(self, rules_file: str, spec_file: str) -> WorkflowState:
        """
        Run the validation workflow.
        
        Args:
            rules_file: Path to the rules file
            spec_file: Path to the specification file
            
        Returns:
            Final workflow state
        """
        # Initialize the state
        initial_state = WorkflowState(
            rules_file=rules_file,
            spec_file=spec_file,
            config=self.config,
            status="running",
            current_step="parse_files"
        )
        
        logger.info(f"Starting validation workflow for rules: {rules_file}, spec: {spec_file}")
        
        # Run the workflow
        try:
            # In LangGraph 0.3.27, we use the stream_async method
            for event in self.workflow.stream_async(initial_state):
                if event.get("type") == "end":
                    final_state = event.get("data", {})
                    logger.info("Workflow completed successfully")
                    return final_state
            
            # If we didn't get an end event, return the initial state with an error
            logger.error("Workflow did not complete")
            initial_state.status = "failed"
            initial_state.current_step = "error"
            initial_state.errors.append({
                "error_type": "workflow_incomplete",
                "message": "Workflow did not complete"
            })
            return initial_state
        except Exception as e:
            logger.error(f"Workflow failed: {str(e)}")
            # Create an error state
            error_state = WorkflowState(
                rules_file=rules_file,
                spec_file=spec_file,
                status="failed",
                current_step="error",
                errors=[{
                    "error_type": "workflow_failure",
                    "message": f"Workflow failed: {str(e)}",
                    "exception": str(e)
                }]
            )
            return error_state
    
    def _parse_files(self, state: WorkflowState) -> WorkflowState:
        """
        Parse the rules and specification files.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        state.current_step = "parse_files"
        logger.info("Parsing files...")
        
        # Parse specification file
        spec, spec_errors = self.parser.parse_file(state.spec_file, "specification")
        if spec_errors:
            state.errors.extend(spec_errors)
        
        if spec is None:
            state.status = "failed"
            state.errors.append({
                "error_type": "parsing_failure",
                "message": "Failed to parse specification file",
                "file": state.spec_file
            })
            return state
        
        state.specification = spec
        
        # Parse rules file
        rules, rule_errors = self.parser.parse_file(state.rules_file, "rules")
        if rule_errors:
            state.errors.extend(rule_errors)
        
        if not rules:
            state.status = "failed"
            state.errors.append({
                "error_type": "parsing_failure",
                "message": "Failed to parse rules file or no rules found",
                "file": state.rules_file
            })
            return state
        
        state.rules = rules
        logger.info(f"Parsed {len(rules)} rules and specification successfully")
        
        return state
    
    def _validate_rules(self, state: WorkflowState) -> WorkflowState:
        """
        Validate the rules against the specification.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        state.current_step = "validate_rules"
        logger.info("Validating rules...")
        
        # Validate rules
        validation_results = self.validator.validate_rules(state.rules, state.specification)
        state.validation_results = validation_results
        
        # Check for validation failures
        validation_failed = False
        for result in validation_results:
            if not result.is_valid:
                validation_failed = True
                break
        
        if validation_failed:
            logger.warning("Some rules failed validation")
        else:
            logger.info("All rules passed validation")
        
        return state
    
    def _formalize_rules(self, state: WorkflowState) -> WorkflowState:
        """
        Formalize the rules using LLM.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        state.current_step = "formalize_rules"
        logger.info("Formalizing rules...")
        
        # Check if LLM is available
        if not self.llm_orchestrator.is_available:
            logger.warning("LLM is not available. Skipping rule formalization.")
            return state
        
        # Formalize each rule
        for i, rule in enumerate(state.rules):
            logger.info(f"Formalizing rule {rule.id} ({i+1}/{len(state.rules)})")
            
            # Skip rules that failed validation
            if any(r.rule_id == rule.id and not r.is_valid for r in state.validation_results):
                logger.info(f"Skipping formalization for invalid rule {rule.id}")
                continue
            
            # Formalize the rule
            formalized_condition = self.llm_orchestrator.formalize_rule(rule, state.specification)
            
            if formalized_condition:
                rule.formalized_condition = formalized_condition
                logger.info(f"Successfully formalized rule {rule.id}")
            else:
                logger.warning(f"Failed to formalize rule {rule.id}")
                state.errors.append({
                    "error_type": "formalization_failure",
                    "message": f"Failed to formalize rule {rule.id}",
                    "rule_id": rule.id
                })
        
        return state
    
    def _verify_rules(self, state: WorkflowState) -> WorkflowState:
        """
        Verify the rules using Z3.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        state.current_step = "verify_rules"
        logger.info("Verifying rules with Z3...")
        
        # Verify rules
        verification_results = self.verifier.verify_rules(state.rules, state.specification)
        
        # Merge verification results with validation results
        for ver_result in verification_results:
            for i, val_result in enumerate(state.validation_results):
                if ver_result.rule_id == val_result.rule_id:
                    # Merge errors and warnings
                    val_result.errors.extend(ver_result.errors)
                    val_result.warnings.extend(ver_result.warnings)
                    
                    # Update validity
                    if not ver_result.is_valid:
                        val_result.is_valid = False
                    
                    # Update the validation result
                    state.validation_results[i] = val_result
                    break
        
        # Check for verification failures
        verification_failed = False
        for result in verification_results:
            if not result.is_valid:
                verification_failed = True
                break
        
        if verification_failed:
            logger.warning("Some rules failed verification")
        else:
            logger.info("All rules passed verification")
        
        return state
    
    def _generate_tests(self, state: WorkflowState) -> WorkflowState:
        """
        Generate test cases for the rules using advanced techniques.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        state.current_step = "generate_tests"
        logger.info("Generating test cases using advanced techniques...")
        
        # Get valid rules (those that passed validation and verification)
        valid_rules = []
        for rule in state.rules:
            if not any(r.rule_id == rule.id and not r.is_valid for r in state.validation_results):
                valid_rules.append(rule)
            else:
                logger.info(f"Skipping test generation for invalid rule {rule.id}")
        
        if not valid_rules:
            logger.warning("No valid rules to generate tests for.")
            return state
        
        # Get test generation techniques from config
        techniques = state.config.get("test_techniques", ["metamorphic", "symbolic", "adversarial", "causal"])
        parallel = state.config.get("parallel_test_generation", True)
        
        logger.info(f"Using test generation techniques: {', '.join(techniques)}")
        logger.info(f"Parallel test generation: {parallel}")
        
        try:
            # Generate test cases using the advanced test generator
            all_tests = self.test_generator.generate_tests(
                valid_rules,
                state.specification,
                parallel=parallel,
                techniques=techniques
            )
            
            # Add test cases to state
            total_tests = 0
            for rule_id, tests in all_tests.items():
                state.test_cases.extend(tests)
                total_tests += len(tests)
                logger.info(f"Generated {len(tests)} advanced test cases for rule {rule_id}")
            
            logger.info(f"Generated a total of {total_tests} test cases across {len(valid_rules)} rules")
            
            # If advanced test generation produced no tests, fall back to LLM-based generation
            if total_tests == 0 and self.llm_orchestrator.is_available:
                logger.warning("Advanced test generation produced no tests. Falling back to LLM-based generation.")
                self._generate_llm_tests(state, valid_rules)
        
        except Exception as e:
            logger.error(f"Error in advanced test generation: {str(e)}")
            state.errors.append({
                "error_type": "advanced_test_generation_failure",
                "message": f"Failed to generate advanced test cases: {str(e)}"
            })
            
            # Fall back to LLM-based generation if available
            if self.llm_orchestrator.is_available:
                logger.info("Falling back to LLM-based test generation.")
                self._generate_llm_tests(state, valid_rules)
        
        return state
    
    def _generate_llm_tests(self, state: WorkflowState, valid_rules: List[EditCheckRule]) -> None:
        """
        Generate test cases using LLM as a fallback method.
        
        Args:
            state: Current workflow state
            valid_rules: List of valid rules
        """
        if not self.llm_orchestrator.is_available:
            logger.warning("LLM is not available. Skipping fallback test generation.")
            return
        
        # Generate test cases for each rule
        for i, rule in enumerate(valid_rules):
            logger.info(f"Generating LLM test cases for rule {rule.id} ({i+1}/{len(valid_rules)})")
            
            # Generate test cases
            test_cases = self.llm_orchestrator.generate_test_cases(
                rule, 
                state.specification,
                state.config.get("test_cases_per_rule", 5)
            )
            
            if test_cases:
                # Add a marker to indicate these are LLM-generated tests
                for test in test_cases:
                    test.description = f"[LLM] {test.description}"
                
                state.test_cases.extend(test_cases)
                logger.info(f"Generated {len(test_cases)} LLM test cases for rule {rule.id}")
            else:
                logger.warning(f"Failed to generate LLM test cases for rule {rule.id}")
                state.errors.append({
                    "error_type": "llm_test_generation_failure",
                    "message": f"Failed to generate LLM test cases for rule {rule.id}",
                    "rule_id": rule.id
                })
    
    def _finalize(self, state: WorkflowState) -> WorkflowState:
        """
        Finalize the workflow.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        state.current_step = "finalize"
        logger.info("Finalizing workflow...")
        
        # Summarize the results
        valid_rules = sum(1 for r in state.validation_results if r.is_valid)
        total_rules = len(state.rules)
        total_test_cases = len(state.test_cases)
        
        logger.info(f"Validation complete: {valid_rules}/{total_rules} rules valid, {total_test_cases} test cases generated")
        
        # Set final status
        if valid_rules == total_rules and not state.errors:
            state.status = "completed"
        elif valid_rules > 0:
            state.status = "completed_with_warnings"
        else:
            state.status = "failed"
        
        return state
    
    def _should_formalize_rules(self, state: WorkflowState) -> bool:
        """
        Determine if rules should be formalized.
        
        Args:
            state: Current workflow state
            
        Returns:
            True if rules should be formalized, False otherwise
        """
        return (
            state.config.get("formalize_rules", True) and 
            self.llm_orchestrator.is_available and
            state.status != "failed"
        )
    
    def _should_verify_rules(self, state: WorkflowState) -> bool:
        """
        Determine if rules should be verified with Z3.
        
        Args:
            state: Current workflow state
            
        Returns:
            True if rules should be verified, False otherwise
        """
        return (
            state.config.get("verify_with_z3", True) and
            state.status != "failed"
        )
    
    def _should_generate_tests(self, state: WorkflowState) -> bool:
        """
        Determine if test cases should be generated.
        
        Args:
            state: Current workflow state
            
        Returns:
            True if test cases should be generated, False otherwise
        """
        return (
            state.config.get("generate_tests", True) and
            self.llm_orchestrator.is_available and
            state.status != "failed"
        )
