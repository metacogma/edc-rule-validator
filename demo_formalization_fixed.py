#!/usr/bin/env python
"""
Demonstration of LLM-based rule formalization for Edit Check Rule Validation System.

This script shows how the system uses Azure OpenAI to convert natural language rules
into structured logical expressions.
"""

import os
import sys
import logging
import json
from dotenv import load_dotenv
import openai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the necessary components
from src.models.data_models import EditCheckRule, StudySpecification, Form, Field, FieldType, RuleSeverity
from src.parsers.custom_parser import CustomParser

# Updated LLM Orchestrator that works with OpenAI v1.0+
class ModernLLMOrchestrator:
    """Orchestrate interactions with Azure OpenAI for rule formalization and test generation."""
    
    def __init__(self, api_key: str = None, api_version: str = None, deployment_name: str = None):
        """
        Initialize the LLM orchestrator.
        
        Args:
            api_key: Azure OpenAI API key (defaults to environment variable)
            api_version: Azure OpenAI API version (defaults to environment variable)
            deployment_name: Azure OpenAI deployment name (defaults to environment variable)
        """
        # Set up Azure OpenAI client
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_version = api_version or os.getenv("OPENAI_API_VERSION", "2025-01-01-preview")
        self.deployment_name = deployment_name or os.getenv("AZURE_DEPLOYMENT_NAME")
        self.azure_endpoint = os.getenv("AZURE_ENDPOINT", "https://api.openai.com/v1")
        
        # Check if API key is available
        if not self.api_key:
            logger.warning("Azure OpenAI API key not found. LLM features will not be available.")
            self.is_available = False
        else:
            self.is_available = True
            
            # Configure OpenAI client for Azure
            self.client = openai.AzureOpenAI(
                api_key=self.api_key,
                api_version=self.api_version,
                azure_endpoint=self.azure_endpoint
            )
    
    def formalize_rule(self, rule: EditCheckRule, specification: StudySpecification) -> str:
        """
        Formalize a rule using Azure OpenAI with chain-of-thought prompting.
        
        Args:
            rule: Rule to formalize
            specification: Study specification for context
            
        Returns:
            Formalized rule condition or None if error
        """
        if not self.is_available:
            logger.error("Azure OpenAI is not available. Cannot formalize rule.")
            return None
        
        try:
            # Prepare context for the LLM
            context = self._prepare_specification_context(specification, rule)
            
            # Construct the prompt with chain-of-thought
            prompt = self._construct_formalization_prompt(rule, context)
            
            # Call Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert in formalizing clinical trial edit check rules. Your task is to convert natural language rules into structured logical expressions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000,
                top_p=0.95,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            # Extract the formalized rule
            formalized_rule = response.choices[0].message.content.strip()
            
            # Extract the logical expression part if it's wrapped in explanation
            if "```" in formalized_rule:
                # Extract code block
                code_blocks = formalized_rule.split("```")
                for block in code_blocks:
                    if block.strip() and not block.startswith("python") and not block.startswith("logical"):
                        formalized_rule = block.strip()
                        break
            
            logger.info(f"Successfully formalized rule {rule.id}")
            return formalized_rule
            
        except Exception as e:
            logger.error(f"Error formalizing rule {rule.id}: {str(e)}")
            return None
    
    def generate_test_cases(self, rule: EditCheckRule, specification: StudySpecification, num_cases: int = 3) -> list:
        """
        Generate test cases for a rule using Azure OpenAI.
        
        Args:
            rule: Rule to generate test cases for
            specification: Study specification for context
            num_cases: Number of test cases to generate
            
        Returns:
            List of test cases
        """
        if not self.is_available:
            logger.error("Azure OpenAI is not available. Cannot generate test cases.")
            return []
        
        try:
            # Prepare context for the LLM
            context = self._prepare_specification_context(specification, rule)
            
            # Construct the prompt
            prompt = self._construct_test_generation_prompt(rule, context, num_cases)
            
            # Call Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert in generating test cases for clinical trial edit check rules. Your task is to create diverse test cases that cover positive, negative, and boundary conditions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,  # Higher temperature for more diverse test cases
                max_tokens=2000,
                top_p=0.95,
                frequency_penalty=0.2,
                presence_penalty=0.2
            )
            
            # Extract the test cases
            test_cases_text = response.choices[0].message.content.strip()
            
            # Try to parse as JSON
            test_cases = []
            try:
                # Look for JSON in the response
                if "```json" in test_cases_text:
                    json_parts = test_cases_text.split("```json")
                    json_text = json_parts[1].split("```")[0].strip()
                    test_cases_data = json.loads(json_text)
                    
                    # Convert to TestCase objects
                    for tc_data in test_cases_data:
                        test_case = {
                            "rule_id": rule.id,
                            "description": tc_data.get("description", ""),
                            "expected_result": tc_data.get("expected_result", True),
                            "test_data": tc_data.get("test_data", {}),
                            "is_positive": tc_data.get("expected_result", True),
                            "technique": "llm"
                        }
                        test_cases.append(test_case)
                else:
                    # Try to parse the whole response as JSON
                    test_cases_data = json.loads(test_cases_text)
                    
                    # Convert to TestCase objects
                    for tc_data in test_cases_data:
                        test_case = {
                            "rule_id": rule.id,
                            "description": tc_data.get("description", ""),
                            "expected_result": tc_data.get("expected_result", True),
                            "test_data": tc_data.get("test_data", {}),
                            "is_positive": tc_data.get("expected_result", True),
                            "technique": "llm"
                        }
                        test_cases.append(test_case)
            except json.JSONDecodeError:
                # If not valid JSON, create a simple test case with the raw response
                test_case = {
                    "rule_id": rule.id,
                    "description": "LLM generated test case",
                    "expected_result": True,
                    "test_data": {"raw_response": test_cases_text},
                    "is_positive": True,
                    "technique": "llm"
                }
                test_cases.append(test_case)
            
            logger.info(f"Successfully generated {len(test_cases)} test cases for rule {rule.id}")
            return test_cases
            
        except Exception as e:
            logger.error(f"Error generating test cases for rule {rule.id}: {str(e)}")
            return []
    
    def _prepare_specification_context(self, specification: StudySpecification, rule: EditCheckRule) -> dict:
        """
        Prepare study specification context for the LLM.
        
        Args:
            specification: Study specification
            rule: Rule for context
            
        Returns:
            Dictionary with relevant context
        """
        context = {"forms": {}}
        
        # If rule has specific forms, only include those
        relevant_forms = rule.forms if hasattr(rule, 'forms') and rule.forms else list(specification.forms.keys())
        
        for form_name in relevant_forms:
            if form_name in specification.forms:
                form = specification.forms[form_name]
                form_data = {
                    "name": form.name,
                    "label": form.label,
                    "fields": []
                }
                
                # If rule has specific fields, prioritize those
                relevant_fields = []
                if hasattr(rule, 'fields') and rule.fields:
                    for field_name in rule.fields:
                        for field in form.fields:
                            if field.name == field_name:
                                relevant_fields.append(field)
                
                # If no specific fields or not all were found, include all fields
                if not relevant_fields:
                    relevant_fields = form.fields
                
                # Add field data
                for field in relevant_fields:
                    field_data = {
                        "name": field.name,
                        "type": field.type.value,
                        "label": field.label
                    }
                    
                    # Add optional field properties if available
                    if hasattr(field, 'valid_values') and field.valid_values:
                        field_data["valid_values"] = field.valid_values
                    
                    form_data["fields"].append(field_data)
                
                context["forms"][form_name] = form_data
        
        return context
    
    def _construct_formalization_prompt(self, rule: EditCheckRule, context: dict) -> str:
        """
        Construct a prompt for rule formalization.
        
        Args:
            rule: Rule to formalize
            context: Specification context
            
        Returns:
            Prompt string
        """
        prompt = f"""
I need to formalize the following clinical trial edit check rule into a structured logical expression:

Rule ID: {rule.id}
Rule Condition: {rule.condition}

The rule applies to the following forms and fields:
"""
        
        # Add forms and fields information
        for form_name, form_data in context["forms"].items():
            prompt += f"\nForm: {form_name}"
            if form_data["fields"]:
                prompt += "\nFields:"
                for field in form_data["fields"]:
                    prompt += f"\n- {field['name']} (Type: {field['type']})"
                    if "valid_values" in field:
                        prompt += f" Valid values: {field['valid_values']}"
        
        prompt += """

Please convert this rule into a formal logical expression that can be used for validation.
Use the following guidelines:
1. Use standard logical operators: AND, OR, NOT, IMPLIES
2. Use comparison operators: =, !=, <, >, <=, >=
3. Reference fields using form.field notation
4. Use parentheses to clarify precedence
5. For date comparisons, use clear date functions like DATE_DIFF(date1, date2) or DATE_BEFORE(date1, date2)
6. For categorical fields, use IN operator, e.g., field IN [value1, value2]

Provide only the formalized expression without explanation.
"""
        
        return prompt
    
    def _construct_test_generation_prompt(self, rule: EditCheckRule, context: dict, num_cases: int) -> str:
        """
        Construct a prompt for test case generation.
        
        Args:
            rule: Rule to generate test cases for
            context: Specification context
            num_cases: Number of test cases to generate
            
        Returns:
            Prompt string
        """
        # Use formalized condition if available
        condition = rule.formalized_condition if hasattr(rule, 'formalized_condition') and rule.formalized_condition else rule.condition
        
        prompt = f"""
I need to generate {num_cases} test cases for the following clinical trial edit check rule:

Rule ID: {rule.id}
Rule Condition: {condition}

The rule applies to the following forms and fields:
"""
        
        # Add forms and fields information
        for form_name, form_data in context["forms"].items():
            prompt += f"\nForm: {form_name}"
            if form_data["fields"]:
                prompt += "\nFields:"
                for field in form_data["fields"]:
                    prompt += f"\n- {field['name']} (Type: {field['type']})"
                    if "valid_values" in field:
                        prompt += f" Valid values: {field['valid_values']}"
        
        prompt += f"""

Please generate {num_cases} diverse test cases that include:
- At least one positive test case (expected to pass)
- At least one negative test case (expected to fail)
- At least one boundary condition test case

For each test case, provide:
1. A description of the test case
2. The expected result (true for pass, false for fail)
3. The test data (form and field values)

Return the test cases in JSON format like this:
[
  {{
    "description": "Test description",
    "expected_result": true,
    "test_data": {{
      "form_name": {{
        "field_name": "value"
      }}
    }}
  }}
]
"""
        
        return prompt


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
    llm_orchestrator = ModernLLMOrchestrator()
    
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
    demo_rules = rules[:3]  # First 3 rules
    
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
                logger.info(f"  Test {j}: {test['description']}")
                logger.info(f"    Expected result: {test['expected_result']}")
                logger.info(f"    Test data: {test['test_data']}")
        else:
            logger.warning(f"Failed to generate test cases for rule {rule.id}")
    
    logger.info("\nLLM-based rule formalization demo completed")

if __name__ == "__main__":
    main()
