"""
LLM Orchestrator for the Edit Check Rule Validation System.

This module provides functionality to interact with Azure OpenAI for rule formalization
and test case generation, implementing chain-of-thought prompting and few-shot learning.
"""

import os
import json
from typing import Dict, List, Any, Optional, Union
import openai
from dotenv import load_dotenv

from ..models.data_models import EditCheckRule, StudySpecification, TestCase
from ..utils.logger import Logger

logger = Logger(__name__)

# Load environment variables
load_dotenv()

class LLMOrchestrator:
    """Orchestrate interactions with Azure OpenAI for rule formalization and test generation."""
    
    def __init__(self, api_key: Optional[str] = None, api_version: Optional[str] = None, deployment_name: Optional[str] = None):
        """
        Initialize the LLM orchestrator.
        
        Args:
            api_key: Azure OpenAI API key (defaults to environment variable)
            api_version: Azure OpenAI API version (defaults to environment variable)
            deployment_name: Azure OpenAI deployment name (defaults to environment variable)
        """
        # Set up Azure OpenAI client
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_version = api_version or os.getenv("OPENAI_API_VERSION", "2023-05-15")
        self.deployment_name = deployment_name or os.getenv("AZURE_DEPLOYMENT_NAME")
        
        # Check if API key is available
        if not self.api_key:
            logger.warning("Azure OpenAI API key not found. LLM features will not be available.")
            self.is_available = False
        else:
            self.is_available = True
            
            # Configure OpenAI client for Azure
            openai.api_key = self.api_key
            openai.api_version = self.api_version
            openai.api_type = "azure"
            openai.api_base = os.getenv("AZURE_ENDPOINT", "https://api.openai.com/v1")
    
    def formalize_rule(self, rule: EditCheckRule, specification: StudySpecification) -> Optional[str]:
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
            
            # Prepare few-shot examples
            examples = self._get_formalization_examples()
            
            # Construct the prompt with chain-of-thought
            prompt = self._construct_formalization_prompt(rule, context, examples)
            
            # Call Azure OpenAI
            response = openai.ChatCompletion.create(
                deployment_id=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert in formalizing clinical trial edit check rules. Your task is to convert natural language rules into structured logical expressions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000,
                top_p=0.95,
                frequency_penalty=0,
                presence_penalty=0,
                stop=None
            )
            
            # Extract and process the formalized rule
            formalized_rule = self._extract_formalized_rule(response.choices[0].message.content)
            
            logger.info(f"Successfully formalized rule {rule.id}")
            return formalized_rule
            
        except Exception as e:
            logger.error(f"Error formalizing rule {rule.id}: {str(e)}")
            return None
    
    def generate_test_cases(self, rule: EditCheckRule, specification: StudySpecification, num_cases: int = 3) -> List[TestCase]:
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
            
            # Prepare few-shot examples
            examples = self._get_test_generation_examples()
            
            # Construct the prompt
            prompt = self._construct_test_generation_prompt(rule, context, examples, num_cases)
            
            # Call Azure OpenAI
            response = openai.ChatCompletion.create(
                deployment_id=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert in generating test cases for clinical trial edit check rules. Your task is to create diverse test cases that cover positive, negative, and boundary conditions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,  # Higher temperature for more diverse test cases
                max_tokens=2000,
                top_p=0.95,
                frequency_penalty=0.2,
                presence_penalty=0.2,
                stop=None
            )
            
            # Extract and process the test cases
            test_cases = self._extract_test_cases(response.choices[0].message.content, rule.id)
            
            logger.info(f"Successfully generated {len(test_cases)} test cases for rule {rule.id}")
            return test_cases
            
        except Exception as e:
            logger.error(f"Error generating test cases for rule {rule.id}: {str(e)}")
            return []
    
    def _prepare_specification_context(self, specification: StudySpecification, rule: EditCheckRule) -> Dict[str, Any]:
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
        relevant_forms = rule.forms if rule.forms else list(specification.forms.keys())
        
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
                if rule.fields:
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
                    if field.valid_values:
                        field_data["valid_values"] = field.valid_values
                    
                    if field.required:
                        field_data["required"] = field.required
                    
                    if field.min_value is not None:
                        field_data["min_value"] = field.min_value
                    
                    if field.max_value is not None:
                        field_data["max_value"] = field.max_value
                    
                    form_data["fields"].append(field_data)
                
                context["forms"][form_name] = form_data
        
        return context
    
    def _get_formalization_examples(self) -> List[Dict[str, str]]:
        """
        Get few-shot examples for rule formalization.
        
        Returns:
            List of example dictionaries
        """
        return [
            {
                "rule": "Age must be between 18 and 65 years",
                "context": "Form: Demographics, Field: age, Type: number",
                "thought_process": "This rule is checking if the age is within a specific range. I need to use comparison operators to check if age is greater than or equal to 18 AND less than or equal to 65.",
                "formalized_rule": "Demographics.age >= 18 AND Demographics.age <= 65"
            },
            {
                "rule": "If gender is Female, then pregnancy test must be completed",
                "context": "Form: Demographics, Field: gender, Type: categorical, Valid Values: Male,Female,Other\nForm: ScreeningTests, Field: pregnancy_test, Type: categorical, Valid Values: Positive,Negative,Not Done",
                "thought_process": "This is a conditional rule. If gender equals 'Female', then pregnancy_test must have a value other than 'Not Done'. I'll use an IF-THEN structure.",
                "formalized_rule": "IF Demographics.gender = \"Female\" THEN ScreeningTests.pregnancy_test != \"Not Done\""
            },
            {
                "rule": "Systolic blood pressure must be less than 140 mmHg and diastolic blood pressure must be less than 90 mmHg",
                "context": "Form: VitalSigns, Field: systolic_bp, Type: number\nForm: VitalSigns, Field: diastolic_bp, Type: number",
                "thought_process": "This rule has two conditions that must both be true. Systolic BP must be less than 140 AND diastolic BP must be less than 90.",
                "formalized_rule": "VitalSigns.systolic_bp < 140 AND VitalSigns.diastolic_bp < 90"
            }
        ]
    
    def _get_test_generation_examples(self) -> List[Dict[str, Any]]:
        """
        Get few-shot examples for test case generation.
        
        Returns:
            List of example dictionaries
        """
        return [
            {
                "rule": "Demographics.age >= 18 AND Demographics.age <= 65",
                "test_cases": [
                    {
                        "description": "Valid age within range",
                        "test_data": {"Demographics": {"age": 35}},
                        "expected_result": True,
                        "is_positive": True
                    },
                    {
                        "description": "Invalid age below minimum",
                        "test_data": {"Demographics": {"age": 17}},
                        "expected_result": False,
                        "is_positive": False
                    },
                    {
                        "description": "Invalid age above maximum",
                        "test_data": {"Demographics": {"age": 66}},
                        "expected_result": False,
                        "is_positive": False
                    },
                    {
                        "description": "Boundary case at minimum age",
                        "test_data": {"Demographics": {"age": 18}},
                        "expected_result": True,
                        "is_positive": True
                    }
                ]
            },
            {
                "rule": "IF Demographics.gender = \"Female\" THEN ScreeningTests.pregnancy_test != \"Not Done\"",
                "test_cases": [
                    {
                        "description": "Female with completed pregnancy test (Positive)",
                        "test_data": {"Demographics": {"gender": "Female"}, "ScreeningTests": {"pregnancy_test": "Positive"}},
                        "expected_result": True,
                        "is_positive": True
                    },
                    {
                        "description": "Female with completed pregnancy test (Negative)",
                        "test_data": {"Demographics": {"gender": "Female"}, "ScreeningTests": {"pregnancy_test": "Negative"}},
                        "expected_result": True,
                        "is_positive": True
                    },
                    {
                        "description": "Female with incomplete pregnancy test",
                        "test_data": {"Demographics": {"gender": "Female"}, "ScreeningTests": {"pregnancy_test": "Not Done"}},
                        "expected_result": False,
                        "is_positive": False
                    },
                    {
                        "description": "Male with no pregnancy test",
                        "test_data": {"Demographics": {"gender": "Male"}, "ScreeningTests": {"pregnancy_test": "Not Done"}},
                        "expected_result": True,
                        "is_positive": True
                    }
                ]
            }
        ]
    
    def _construct_formalization_prompt(self, rule: EditCheckRule, context: Dict[str, Any], examples: List[Dict[str, str]]) -> str:
        """
        Construct a prompt for rule formalization with chain-of-thought.
        
        Args:
            rule: Rule to formalize
            context: Study specification context
            examples: Few-shot examples
            
        Returns:
            Formatted prompt
        """
        # Format the context
        context_str = "Study Specification Context:\n"
        for form_name, form_data in context["forms"].items():
            context_str += f"Form: {form_name}"
            if form_data.get("label"):
                context_str += f" ({form_data['label']})"
            context_str += "\n"
            
            for field in form_data["fields"]:
                context_str += f"  Field: {field['name']}, Type: {field['type']}"
                if field.get("label"):
                    context_str += f", Label: {field['label']}"
                if field.get("valid_values"):
                    context_str += f", Valid Values: {field['valid_values']}"
                if field.get("required"):
                    context_str += ", Required: Yes"
                if field.get("min_value") is not None:
                    context_str += f", Min: {field['min_value']}"
                if field.get("max_value") is not None:
                    context_str += f", Max: {field['max_value']}"
                context_str += "\n"
        
        # Format the examples
        examples_str = "Examples of Rule Formalization:\n\n"
        for i, example in enumerate(examples, 1):
            examples_str += f"Example {i}:\n"
            examples_str += f"Rule: {example['rule']}\n"
            examples_str += f"Context: {example['context']}\n"
            examples_str += f"Thought Process: {example['thought_process']}\n"
            examples_str += f"Formalized Rule: {example['formalized_rule']}\n\n"
        
        # Construct the full prompt
        prompt = f"""
Your task is to formalize the following edit check rule into a structured logical expression.

Rule ID: {rule.id}
Rule Condition: {rule.condition}
Rule Message: {rule.message if rule.message else 'N/A'}
Rule Severity: {rule.severity.value}

{context_str}

{examples_str}

Now, please formalize the above rule.

Step 1: Understand the rule and identify the forms and fields involved.
Step 2: Determine the logical structure (simple condition, AND/OR combination, IF-THEN, etc.).
Step 3: Express the rule using the proper syntax with form.field references.

Thought Process: 

Formalized Rule:
"""
        
        return prompt
    
    def _construct_test_generation_prompt(self, rule: EditCheckRule, context: Dict[str, Any], examples: List[Dict[str, Any]], num_cases: int) -> str:
        """
        Construct a prompt for test case generation.
        
        Args:
            rule: Rule to generate test cases for
            context: Study specification context
            examples: Few-shot examples
            num_cases: Number of test cases to generate
            
        Returns:
            Formatted prompt
        """
        # Format the context
        context_str = "Study Specification Context:\n"
        for form_name, form_data in context["forms"].items():
            context_str += f"Form: {form_name}"
            if form_data.get("label"):
                context_str += f" ({form_data['label']})"
            context_str += "\n"
            
            for field in form_data["fields"]:
                context_str += f"  Field: {field['name']}, Type: {field['type']}"
                if field.get("label"):
                    context_str += f", Label: {field['label']}"
                if field.get("valid_values"):
                    context_str += f", Valid Values: {field['valid_values']}"
                if field.get("required"):
                    context_str += ", Required: Yes"
                if field.get("min_value") is not None:
                    context_str += f", Min: {field['min_value']}"
                if field.get("max_value") is not None:
                    context_str += f", Max: {field['max_value']}"
                context_str += "\n"
        
        # Format the examples
        examples_str = "Examples of Test Case Generation:\n\n"
        for i, example in enumerate(examples, 1):
            examples_str += f"Example {i}:\n"
            examples_str += f"Rule: {example['rule']}\n"
            examples_str += "Test Cases:\n"
            for j, test_case in enumerate(example['test_cases'], 1):
                examples_str += f"  {j}. {test_case['description']}\n"
                examples_str += f"     Test Data: {json.dumps(test_case['test_data'])}\n"
                examples_str += f"     Expected Result: {test_case['expected_result']}\n"
                examples_str += f"     Is Positive Test: {test_case['is_positive']}\n"
            examples_str += "\n"
        
        # Construct the full prompt
        prompt = f"""
Your task is to generate {num_cases} test cases for the following edit check rule.

Rule ID: {rule.id}
Rule Condition: {rule.condition}
Formalized Rule: {rule.formalized_condition if rule.formalized_condition else rule.condition}
Rule Message: {rule.message if rule.message else 'N/A'}
Rule Severity: {rule.severity.value}

{context_str}

{examples_str}

Please generate {num_cases} test cases for the above rule. Include:
1. At least one positive test case (rule should pass)
2. At least one negative test case (rule should fail)
3. Boundary test cases where applicable

For each test case, provide:
1. A description of the test case
2. The test data as a JSON object with form and field values
3. The expected result (true for pass, false for fail)
4. Whether it's a positive or negative test

Format your response as a JSON array of test cases.
"""
        
        return prompt
    
    def _extract_formalized_rule(self, response_text: str) -> Optional[str]:
        """
        Extract the formalized rule from the LLM response.
        
        Args:
            response_text: Text response from the LLM
            
        Returns:
            Formalized rule or None if extraction failed
        """
        try:
            # Look for the formalized rule after the "Formalized Rule:" marker
            if "Formalized Rule:" in response_text:
                parts = response_text.split("Formalized Rule:")
                if len(parts) > 1:
                    formalized_rule = parts[1].strip()
                    # Remove any markdown code block markers
                    formalized_rule = formalized_rule.replace("```", "").strip()
                    return formalized_rule
            
            # If not found with marker, try to find a line that looks like a rule
            lines = response_text.strip().split("\n")
            for line in lines:
                line = line.strip()
                # Look for lines that contain typical rule syntax
                if any(op in line for op in ["AND", "OR", "IF", "THEN", "=", "<", ">"]):
                    # Remove any markdown code block markers
                    line = line.replace("```", "").strip()
                    return line
            
            # If still not found, return the last non-empty line as a fallback
            for line in reversed(lines):
                line = line.strip()
                if line and not line.startswith("```"):
                    return line
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting formalized rule: {str(e)}")
            return None
    
    def _extract_test_cases(self, response_text: str, rule_id: str) -> List[TestCase]:
        """
        Extract test cases from the LLM response.
        
        Args:
            response_text: Text response from the LLM
            rule_id: ID of the rule
            
        Returns:
            List of TestCase objects
        """
        test_cases = []
        
        try:
            # Try to extract JSON from the response
            # First, look for code blocks
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
            
            if json_match:
                json_str = json_match.group(1)
                test_cases_data = json.loads(json_str)
            else:
                # If no code blocks, try to find a JSON array in the text
                json_match = re.search(r"\[\s*\{[\s\S]*\}\s*\]", response_text)
                if json_match:
                    json_str = json_match.group(0)
                    test_cases_data = json.loads(json_str)
                else:
                    # If still no JSON found, return empty list
                    logger.error("Could not extract JSON test cases from response")
                    return []
            
            # Convert JSON data to TestCase objects
            for tc_data in test_cases_data:
                # Ensure rule_id is set
                tc_data["rule_id"] = rule_id
                
                # Create TestCase object
                test_case = TestCase.from_dict(tc_data)
                test_cases.append(test_case)
            
            return test_cases
            
        except Exception as e:
            logger.error(f"Error extracting test cases: {str(e)}")
            return []
