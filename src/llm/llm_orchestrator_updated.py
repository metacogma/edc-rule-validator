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
            
            # Extract and process the formalized rule
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
                    
                    if hasattr(field, 'min_value') and field.min_value is not None:
                        field_data["min_value"] = field.min_value
                        
                    if hasattr(field, 'max_value') and field.max_value is not None:
                        field_data["max_value"] = field.max_value
                        
                    if hasattr(field, 'required'):
                        field_data["required"] = field.required
                    
                    form_data["fields"].append(field_data)
                
                context["forms"][form_name] = form_data
        
        return context
    
    def _construct_formalization_prompt(self, rule: EditCheckRule, context: Dict[str, Any], examples: List[Dict[str, str]]) -> str:
        """
        Construct a prompt for rule formalization with chain-of-thought.
        
        Args:
            rule: Rule to formalize
            context: Specification context
            examples: Few-shot examples
            
        Returns:
            Prompt string
        """
        prompt = "# Rule Formalization Task\n\n"
        prompt += "Convert the following clinical trial edit check rule into a structured logical expression.\n\n"
        
        # Add few-shot examples
        if examples:
            prompt += "## Examples\n\n"
            for i, example in enumerate(examples, 1):
                prompt += f"### Example {i}\n"
                prompt += f"**Original Rule**: {example['original']}\n\n"
                prompt += f"**Formalized Rule**: {example['formalized']}\n\n"
                if 'explanation' in example:
                    prompt += f"**Explanation**: {example['explanation']}\n\n"
            
            prompt += "---\n\n"
        
        # Add the rule to formalize
        prompt += "## Rule to Formalize\n\n"
        prompt += f"**Rule ID**: {rule.id}\n\n"
        prompt += f"**Rule Description**: {rule.description if hasattr(rule, 'description') else ''}\n\n"
        prompt += f"**Rule Condition**: {rule.condition}\n\n"
        
        # Add context information
        prompt += "## Context Information\n\n"
        
        # Add forms and fields
        for form_name, form_data in context["forms"].items():
            prompt += f"### Form: {form_name}\n"
            if form_data["fields"]:
                prompt += "Fields:\n"
                for field in form_data["fields"]:
                    prompt += f"- {field['name']} (Type: {field['type']})"
                    if "valid_values" in field:
                        prompt += f", Valid values: {field['valid_values']}"
                    if "min_value" in field:
                        prompt += f", Min: {field['min_value']}"
                    if "max_value" in field:
                        prompt += f", Max: {field['max_value']}"
                    if "required" in field and field["required"]:
                        prompt += ", Required"
                    prompt += "\n"
            prompt += "\n"
        
        # Add formalization guidelines
        prompt += """## Formalization Guidelines

1. Use standard logical operators: AND, OR, NOT, IMPLIES, IF-THEN-ELSE
2. Use comparison operators: =, !=, <, >, <=, >=
3. Reference fields using form.field notation (e.g., AdverseEvent.StartDate)
4. Use parentheses to clarify precedence
5. For date comparisons, use functions like DATE_DIFF(date1, date2) or DATE_BEFORE(date1, date2)
6. For categorical fields, use IN operator, e.g., field IN [value1, value2]
7. For missing values, use IS NULL or IS NOT NULL
8. For conditional logic, use IF condition THEN action ELSE alternative
9. If a rule should be removed under certain conditions, use REMOVE_RULE

## Your Task

Please formalize the rule above into a structured logical expression following these guidelines. 
Think step by step about the rule's meaning and how to represent it formally.
"""
        
        return prompt
    
    def _construct_test_generation_prompt(self, rule: EditCheckRule, context: Dict[str, Any], examples: List[Dict[str, Any]], num_cases: int) -> str:
        """
        Construct a prompt for test case generation.
        
        Args:
            rule: Rule to generate test cases for
            context: Specification context
            examples: Few-shot examples
            num_cases: Number of test cases to generate
            
        Returns:
            Prompt string
        """
        # Use formalized condition if available
        condition = rule.formalized_condition if hasattr(rule, 'formalized_condition') and rule.formalized_condition else rule.condition
        
        prompt = "# Test Case Generation Task\n\n"
        prompt += f"Generate {num_cases} test cases for the following clinical trial edit check rule.\n\n"
        
        # Add few-shot examples
        if examples:
            prompt += "## Examples\n\n"
            for i, example in enumerate(examples, 1):
                prompt += f"### Example {i}\n"
                prompt += f"**Rule**: {example['rule']}\n\n"
                prompt += "**Test Cases**:\n"
                for j, test in enumerate(example['test_cases'], 1):
                    prompt += f"Test {j}: {test['description']}\n"
                    prompt += f"- Expected Result: {test['expected_result']}\n"
                    prompt += f"- Test Data: {json.dumps(test['test_data'], indent=2)}\n\n"
            
            prompt += "---\n\n"
        
        # Add the rule to generate test cases for
        prompt += "## Rule for Test Generation\n\n"
        prompt += f"**Rule ID**: {rule.id}\n\n"
        prompt += f"**Rule Description**: {rule.description if hasattr(rule, 'description') else ''}\n\n"
        prompt += f"**Rule Condition**: {condition}\n\n"
        
        # Add context information
        prompt += "## Context Information\n\n"
        
        # Add forms and fields
        for form_name, form_data in context["forms"].items():
            prompt += f"### Form: {form_name}\n"
            if form_data["fields"]:
                prompt += "Fields:\n"
                for field in form_data["fields"]:
                    prompt += f"- {field['name']} (Type: {field['type']})"
                    if "valid_values" in field:
                        prompt += f", Valid values: {field['valid_values']}"
                    if "min_value" in field:
                        prompt += f", Min: {field['min_value']}"
                    if "max_value" in field:
                        prompt += f", Max: {field['max_value']}"
                    if "required" in field and field["required"]:
                        prompt += ", Required"
                    prompt += "\n"
            prompt += "\n"
        
        # Add test generation guidelines
        prompt += f"""## Test Generation Guidelines

Please generate {num_cases} diverse test cases that include:
1. At least one positive test case (expected to pass the rule check)
2. At least one negative test case (expected to fail the rule check)
3. At least one boundary condition test case (testing edge cases)

For each test case, provide:
1. A clear description of the test scenario
2. The expected result (true for pass, false for fail)
3. The test data as a JSON object with form and field values

## Output Format

Return the test cases in JSON format like this:
```json
[
  {{
    "description": "Test description explaining the scenario",
    "expected_result": true,
    "test_data": {{
      "FormName": {{
        "FieldName": "value"
      }}
    }}
  }}
]
```

## Your Task

Generate {num_cases} test cases for the rule above following these guidelines.
Think about different scenarios that could test the rule's behavior.
"""
        
        return prompt
    
    def _get_formalization_examples(self) -> List[Dict[str, str]]:
        """
        Get few-shot examples for rule formalization.
        
        Returns:
            List of example dictionaries
        """
        return [
            {
                "original": "If Adverse Event start time is not null, and Study Treatment Administration end time is null, then the difference between Adverse Event date and Overall Max Study Treatment Date per subject is less than or equal to 140 days.",
                "formalized": "IF (AdverseEvent.StartTime IS NOT NULL) AND (StudyTreatmentAdministration.EndTime IS NULL) THEN DATE_DIFF(AdverseEvent.Date, StudyTreatmentAdministration.OverallMaxStudyTreatmentDatePerSubject) <= 140 ELSE REMOVE_RULE",
                "explanation": "The rule is formalized as a conditional statement with a clear IF-THEN structure. It checks two conditions and applies a date difference comparison if both conditions are met."
            },
            {
                "original": "Subject's age must be between 18 and 65 years inclusive at the time of enrollment.",
                "formalized": "(Subject.Age >= 18) AND (Subject.Age <= 65)",
                "explanation": "This rule is formalized as a simple logical conjunction of two comparison operations, checking that the age is within the specified range."
            },
            {
                "original": "If gender is 'Female' and age is less than 50, then pregnancy test result must not be null.",
                "formalized": "IF (Subject.Gender = 'Female') AND (Subject.Age < 50) THEN (PregnancyTest.Result IS NOT NULL)",
                "explanation": "This rule is formalized as a conditional statement checking gender and age, with a requirement for the pregnancy test result if the conditions are met."
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
                "rule": "IF (AdverseEvent.StartTime IS NOT NULL) AND (StudyTreatmentAdministration.EndTime IS NULL) THEN DATE_DIFF(AdverseEvent.Date, StudyTreatmentAdministration.OverallMaxStudyTreatmentDatePerSubject) <= 140 ELSE REMOVE_RULE",
                "test_cases": [
                    {
                        "description": "Positive test: StartTime is not null, EndTime is null, and date difference is 100 days (within limit)",
                        "expected_result": True,
                        "test_data": {
                            "AdverseEvent": {
                                "StartTime": "10:30:00",
                                "Date": "2023-05-15"
                            },
                            "StudyTreatmentAdministration": {
                                "EndTime": None,
                                "OverallMaxStudyTreatmentDatePerSubject": "2023-02-04"
                            }
                        }
                    },
                    {
                        "description": "Negative test: StartTime is not null, EndTime is null, but date difference is 150 days (exceeds limit)",
                        "expected_result": False,
                        "test_data": {
                            "AdverseEvent": {
                                "StartTime": "08:15:00",
                                "Date": "2023-07-04"
                            },
                            "StudyTreatmentAdministration": {
                                "EndTime": None,
                                "OverallMaxStudyTreatmentDatePerSubject": "2023-02-04"
                            }
                        }
                    },
                    {
                        "description": "Boundary test: StartTime is not null, EndTime is null, and date difference is exactly 140 days (at limit)",
                        "expected_result": True,
                        "test_data": {
                            "AdverseEvent": {
                                "StartTime": "12:00:00",
                                "Date": "2023-06-24"
                            },
                            "StudyTreatmentAdministration": {
                                "EndTime": None,
                                "OverallMaxStudyTreatmentDatePerSubject": "2023-02-04"
                            }
                        }
                    }
                ]
            },
            {
                "rule": "(Subject.Age >= 18) AND (Subject.Age <= 65)",
                "test_cases": [
                    {
                        "description": "Positive test: Age is 35 (within range)",
                        "expected_result": True,
                        "test_data": {
                            "Subject": {
                                "Age": 35
                            }
                        }
                    },
                    {
                        "description": "Negative test: Age is 17 (below minimum)",
                        "expected_result": False,
                        "test_data": {
                            "Subject": {
                                "Age": 17
                            }
                        }
                    },
                    {
                        "description": "Boundary test: Age is exactly 18 (at minimum)",
                        "expected_result": True,
                        "test_data": {
                            "Subject": {
                                "Age": 18
                            }
                        }
                    }
                ]
            }
        ]
    
    def _extract_test_cases(self, response_text: str, rule_id: str) -> List[TestCase]:
        """
        Extract test cases from LLM response.
        
        Args:
            response_text: LLM response text
            rule_id: Rule ID
            
        Returns:
            List of test cases
        """
        test_cases = []
        
        try:
            # Try to extract JSON from the response
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_text = response_text.split("```")[1].strip()
            else:
                json_text = response_text.strip()
            
            # Parse JSON
            test_cases_data = json.loads(json_text)
            
            # Convert to TestCase objects
            for tc_data in test_cases_data:
                test_case = TestCase(
                    rule_id=rule_id,
                    description=tc_data.get("description", ""),
                    expected_result=tc_data.get("expected_result", True),
                    test_data=tc_data.get("test_data", {}),
                    is_positive=tc_data.get("expected_result", True)
                )
                
                # Add technique
                setattr(test_case, "technique", "llm")
                
                test_cases.append(test_case)
                
        except Exception as e:
            logger.error(f"Error extracting test cases: {str(e)}")
            
            # Create a fallback test case
            positive_test = TestCase(
                rule_id=rule_id,
                description=f"Basic positive test for rule {rule_id}",
                expected_result=True,
                test_data={},
                is_positive=True
            )
            setattr(positive_test, "technique", "llm_fallback")
            
            negative_test = TestCase(
                rule_id=rule_id,
                description=f"Basic negative test for rule {rule_id}",
                expected_result=False,
                test_data={},
                is_positive=False
            )
            setattr(negative_test, "technique", "llm_fallback")
            
            test_cases = [positive_test, negative_test]
        
        return test_cases
