import os
import json
import re
from typing import Dict, List, Any, Optional, Union
import openai
from dotenv import load_dotenv

from ..models.data_models import EditCheckRule, StudySpecification, TestCase
from ..utils.logger import Logger

logger = Logger(__name__)

# Load environment variables
load_dotenv()

class EnhancedLLMOrchestrator:
    """Enhanced LLM orchestration with robust validation and extraction."""
    
    def __init__(self, api_key=None, api_version=None, deployment_name=None):
        """Initialize with better error handling and fallbacks."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_version = api_version or os.getenv("OPENAI_API_VERSION", "2025-01-01-preview")
        self.deployment_name = deployment_name or os.getenv("AZURE_DEPLOYMENT_NAME")
        self.azure_endpoint = os.getenv("AZURE_ENDPOINT", "https://api.openai.com/v1")
        
        # Enhanced error handling with tracked state
        self.last_error = None
        self.retry_count = 0
        self.max_retries = 3
        
        # Domain-specific validators
        self.clinical_validator = ClinicalDomainValidator()
        self.syntax_validator = RuleSyntaxValidator()
        
        # Initialize client with proper error handling
        try:
            if self.api_key:
                self.client = openai.AzureOpenAI(
                    api_key=self.api_key,
                    api_version=self.api_version,
                    azure_endpoint=self.azure_endpoint
                )
                self.is_available = True
                logger.info("LLM client successfully initialized")
            else:
                self.is_available = False
                logger.warning("LLM initialization failed: No API key available")
        except Exception as e:
            self.is_available = False
            self.last_error = str(e)
            logger.error(f"LLM initialization failed: {str(e)}")
    
    def formalize_rule(self, rule: EditCheckRule, specification: StudySpecification) -> Optional[str]:
        """Formalize a rule with robust extraction and validation."""
        if not self.is_available:
            logger.error("LLM is not available. Cannot formalize rule.")
            return self._fallback_formalization(rule, specification)
        
        # Reset retry count for this rule
        self.retry_count = 0
        
        while self.retry_count < self.max_retries:
            try:
                # Prepare enhanced context with clinical domain knowledge
                context = self._prepare_enhanced_context(specification, rule)
                
                # Use structured output format in prompt
                prompt = self._construct_structured_formalization_prompt(rule, context)
                
                # Request JSON response format
                response = self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=[
                        {"role": "system", "content": "You are an expert in formalizing clinical trial edit check rules, with deep knowledge of medical terminology and data validation. Your task is to convert natural language rules into precisely structured logical expressions following a strict schema."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=1000
                )
                
                # Extract with schema validation
                formalized_rule = self._extract_validated_formalization(response.choices[0].message.content, rule)
                
                # Validate against domain knowledge
                if formalized_rule:
                    validation_result = self.clinical_validator.validate(formalized_rule, rule, specification)
                    if not validation_result.is_valid:
                        logger.warning(f"Clinical validation failed for rule {rule.id}: {validation_result.errors}")
                        self.retry_count += 1
                        continue
                    
                    # Syntax validation
                    syntax_result = self.syntax_validator.validate(formalized_rule)
                    if not syntax_result.is_valid:
                        logger.warning(f"Syntax validation failed for rule {rule.id}: {syntax_result.errors}")
                        self.retry_count += 1
                        continue
                    
                    logger.info(f"Successfully formalized and validated rule {rule.id}")
                    return formalized_rule
                else:
                    logger.warning(f"Failed to extract formalized rule for {rule.id}, attempt {self.retry_count + 1}")
                    self.retry_count += 1
            
            except Exception as e:
                logger.error(f"Error formalizing rule {rule.id}: {str(e)}")
                self.last_error = str(e)
                self.retry_count += 1
        
        # All retries failed, use fallback
        return self._fallback_formalization(rule, specification)
    
    def _extract_validated_formalization(self, response_text: str, rule: EditCheckRule) -> Optional[str]:
        """Extract and validate formalized rule from LLM response with schema validation."""
        try:
            # Parse as JSON
            response_data = json.loads(response_text)
            
            # Validate against expected schema
            required_fields = ["formalized_rule", "explanation", "field_references"]
            for field in required_fields:
                if field not in response_data:
                    logger.error(f"Missing required field '{field}' in LLM response for rule {rule.id}")
                    return None
            
            # Extract formalized rule
            formalized_rule = response_data["formalized_rule"]
            
            # Validate field references against the actual rule condition
            referenced_fields = response_data["field_references"]
            for field_ref in referenced_fields:
                if field_ref not in rule.condition:
                    logger.warning(f"Field reference '{field_ref}' in LLM response not found in original rule {rule.id}")
            
            return formalized_rule
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in LLM response for rule {rule.id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error extracting formalized rule for {rule.id}: {str(e)}")
            return None
    
    def _fallback_formalization(self, rule: EditCheckRule, specification: StudySpecification) -> Optional[str]:
        """Provide a fallback formalization when LLM fails."""
        logger.info(f"Using fallback formalization for rule {rule.id}")
        
        # Simple rule pattern matching as fallback
        condition = rule.condition.upper()
        
        # Check for common patterns
        if "IF" in condition and "THEN" in condition:
            parts = condition.split("THEN", 1)
            if_part = parts[0].replace("IF", "").strip()
            then_part = parts[1].strip()
            return f"IF ({if_part}) THEN ({then_part})"
        
        # Extract comparisons
        comparisons = self._extract_comparisons(rule.condition)
        if comparisons:
            return " AND ".join(comparisons)
        
        # Last resort: just wrap the original condition
        return f"({rule.condition})"
    
    def _construct_structured_formalization_prompt(self, rule: EditCheckRule, context: Dict[str, Any]) -> str:
        """Construct a prompt that requests structured JSON output."""
        prompt = "# Rule Formalization Task\n\n"
        prompt += "Convert the following clinical trial edit check rule into a structured logical expression.\n\n"
        
        # Add the rule details
        prompt += f"## Rule to Formalize\n\n"
        prompt += f"**Rule ID**: {rule.id}\n\n"
        prompt += f"**Rule Description**: {getattr(rule, 'description', '')}\n\n"
        prompt += f"**Rule Condition**: {rule.condition}\n\n"
        
        # Add context information with enhanced clinical context
        prompt += "## Context Information\n\n"
        
        # Add forms and fields with clinical metadata
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
                    if "clinical_unit" in field:
                        prompt += f", Unit: {field['clinical_unit']}"
                    if "clinical_category" in field:
                        prompt += f", Category: {field['clinical_category']}"
                    prompt += "\n"
            prompt += "\n"
        
        # Clinical domain guidance
        prompt += "## Clinical Domain Guidance\n\n"
        prompt += "- Laboratory values have standardized units (e.g., mg/dL for glucose)\n"
        prompt += "- Normal ranges vary by patient demographics (age, sex, etc.)\n"
        prompt += "- Temporal relationships between clinical events are important\n"
        prompt += "- Some comparisons require unit conversions\n\n"
        
        # Request structured output
        prompt += """## Output Requirements

Please provide your response in the following JSON format:

```json
{
  "formalized_rule": "The complete formalized logical expression",
  "explanation": "Step-by-step explanation of your reasoning",
  "field_references": ["List", "of", "all", "fields", "referenced"],
  "operators_used": ["List", "of", "all", "operators", "used"],
  "clinical_considerations": "Any clinical considerations relevant to this rule"
}
Use standard logical operators (AND, OR, NOT, IMPLIES), comparison operators (=, !=, <, >, <=, >=), and field references in form.field format.
"""
        return prompt

    def _prepare_enhanced_context(self, specification: StudySpecification, rule: EditCheckRule) -> Dict[str, Any]:
        """Prepare enhanced context with clinical metadata."""
        context = {"forms": {}}
        
        # If rule has specific forms, prioritize those
        relevant_forms = rule.forms if hasattr(rule, 'forms') and rule.forms else list(specification.forms.keys())
        
        for form_name in relevant_forms:
            if form_name in specification.forms:
                form = specification.forms[form_name]
                form_data = {
                    "name": form.name,
                    "label": form.label,
                    "fields": [],
                    "clinical_domain": self._infer_clinical_domain(form_name, form.label)
                }
                
                # Process fields with enhanced clinical metadata
                for field in form.fields:
                    field_data = {
                        "name": field.name,
                        "type": field.type.value,
                        "label": field.label,
                        "clinical_unit": self._infer_clinical_unit(field.name, field.label, field.type.value),
                        "clinical_category": self._infer_clinical_category(field.name, field.label)
                    }
                    
                    # Add standard field properties
                    if hasattr(field, 'valid_values') and field.valid_values:
                        field_data["valid_values"] = field.valid_values
                    
                    if hasattr(field, 'min_value') and field.min_value is not None:
                        field_data["min_value"] = field.min_value
                        
                    if hasattr(field, 'max_value') and field.max_value is not None:
                        field_data["max_value"] = field.max_value
                    
                    form_data["fields"].append(field_data)
                
                context["forms"][form_name] = form_data
        
        # Add clinical trial phase context if available
        if hasattr(specification, 'trial_phase'):
            context["trial_phase"] = specification.trial_phase
        
        # Add therapeutic area context if available
        if hasattr(specification, 'therapeutic_area'):
            context["therapeutic_area"] = specification.therapeutic_area
        
        return context

    def _infer_clinical_domain(self, form_name: str, form_label: str) -> str:
        """Infer clinical domain from form name and label."""
        form_name_lower = form_name.lower()
        form_label_lower = form_label.lower() if form_label else ""
        
        # Common clinical domains
        if any(term in form_name_lower or term in form_label_lower for term in ["lab", "laboratory", "test"]):
            return "laboratory"
        elif any(term in form_name_lower or term in form_label_lower for term in ["vital", "sign", "vs"]):
            return "vital_signs"
        elif any(term in form_name_lower or term in form_label_lower for term in ["ae", "adverse", "event"]):
            return "adverse_events"
        elif any(term in form_name_lower or term in form_label_lower for term in ["med", "medication", "drug"]):
            return "medications"
        elif any(term in form_name_lower or term in form_label_lower for term in ["demo", "demographic"]):
            return "demographics"
        
        return "other"

    def _infer_clinical_unit(self, field_name: str, field_label: str, field_type: str) -> Optional[str]:
        """Infer clinical unit from field name and label."""
        if field_type not in ["number"]:
            return None
            
        field_name_lower = field_name.lower()
        field_label_lower = field_label.lower() if field_label else ""
        
        # Common clinical units
        if any(term in field_name_lower or term in field_label_lower for term in ["temp", "temperature"]):
            return "Celsius"
        elif any(term in field_name_lower or term in field_label_lower for term in ["weight", "wt"]):
            return "kg"
        elif any(term in field_name_lower or term in field_label_lower for term in ["height", "ht"]):
            return "cm"
        elif any(term in field_name_lower or term in field_label_lower for term in ["bp", "blood pressure", "systolic", "diastolic"]):
            return "mmHg"
        elif any(term in field_name_lower or term in field_label_lower for term in ["pulse", "heart rate", "hr"]):
            return "bpm"
        
        return None

    def _infer_clinical_category(self, field_name: str, field_label: str) -> Optional[str]:
        """Infer clinical category from field name and label."""
        field_name_lower = field_name.lower()
        field_label_lower = field_label.lower() if field_label else ""
        
        # Common clinical categories
        if any(term in field_name_lower or term in field_label_lower for term in ["gender", "sex"]):
            return "demographic"
        elif any(term in field_name_lower or term in field_label_lower for term in ["dose", "dosage"]):
            return "intervention"
        elif any(term in field_name_lower or term in field_label_lower for term in ["result", "outcome"]):
            return "outcome"
        
        return "other"

    def _extract_comparisons(self, condition: str) -> List[str]:
        """Extract comparisons from a condition string as fallback."""
        comparisons = []
        
        # Common comparison operators
        operators = ["<=", ">=", "!=", "=", "<", ">"]
        
        # Simple tokenization
        tokens = []
        i = 0
        while i < len(condition):
            # Check for operators
            found_operator = False
            for op in operators:
                if condition[i:i+len(op)] == op:
                    tokens.append(op)
                    i += len(op)
                    found_operator = True
                    break
            
            if not found_operator:
                # Check for words
                if condition[i].isalnum() or condition[i] == '.':
                    word_start = i
                    while i < len(condition) and (condition[i].isalnum() or condition[i] in '._'):
                        i += 1
                    tokens.append(condition[word_start:i])
                else:
                    # Skip other characters
                    i += 1
        
        # Build comparisons
        for i in range(1, len(tokens) - 1):
            if tokens[i] in operators:
                left = tokens[i-1]
                right = tokens[i+1]
                comparisons.append(f"{left} {tokens[i]} {right}")
        
        return comparisons

    def generate_counterfactual_tests(self, prompt: str, context: Dict[str, Any]) -> Optional[str]:
        """Generate counterfactual test cases using LLM."""
        if not self.is_available:
            logger.error("LLM is not available. Cannot generate counterfactual tests.")
            return None
        
        try:
            # Request JSON response format
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert in clinical trial data validation and test generation. Your task is to generate realistic test cases for edit check rules."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating counterfactual tests: {str(e)}")
            self.last_error = str(e)
            return None

    def generate_test_cases(self, rule: EditCheckRule, specification: StudySpecification, num_cases: int = 5) -> List[TestCase]:
        """Generate test cases for a rule."""
        if not self.is_available:
            logger.error("LLM is not available. Cannot generate test cases.")
            return []
        
        try:
            # Prepare context for the LLM
            context = self._prepare_enhanced_context(specification, rule)
            
            # Construct prompt for test case generation
            prompt = f"""
            Generate {num_cases} test cases for the following edit check rule:
            
            Rule ID: {rule.id}
            Rule Condition: {rule.formalized_condition or rule.condition}
            
            Study Specification:
            {json.dumps(context, indent=2)}
            
            For each test case, provide:
            - A description of the test case
            - The expected result (true/false)
            - The test data in JSON format
            
            Include both positive and negative test cases.
            
            Format your response as valid JSON like this:
            {{
                "test_cases": [
                    {{
                        "description": "...",
                        "expected_result": true/false,
                        "test_data": {{...}}
                    }},
                    ...
                ]
            }}
            """
            
            # Call the LLM
            response = self.generate_counterfactual_tests(prompt, context)
            
            # Parse the response
            test_cases = []
            if response and isinstance(response, str):
                try:
                    # Extract JSON from the response
                    json_start = response.find('{')
                    json_end = response.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = response[json_start:json_end]
                        data = json.loads(json_str)
                        
                        if 'test_cases' in data and isinstance(data['test_cases'], list):
                            for tc in data['test_cases']:
                                if all(k in tc for k in ['description', 'expected_result', 'test_data']):
                                    test_case = TestCase(
                                        rule_id=rule.id,
                                        description=tc['description'],
                                        expected_result=tc['expected_result'],
                                        test_data=tc['test_data'],
                                        is_positive=tc['expected_result'],
                                        technique="llm"
                                    )
                                    
                                    test_cases.append(test_case)
                
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Error parsing LLM response for test cases: {str(e)}")
            
            return test_cases
            
        except Exception as e:
            logger.error(f"Error generating test cases for rule {rule.id}: {str(e)}")
            self.last_error = str(e)
            return []

# Placeholder classes for validators
class ClinicalDomainValidator:
    def validate(self, formalized_rule, rule, specification):
        # Placeholder implementation
        class ValidationResult:
            def __init__(self):
                self.is_valid = True
                self.errors = []
        
        return ValidationResult()

class RuleSyntaxValidator:
    def validate(self, formalized_rule):
        # Placeholder implementation
        class ValidationResult:
            def __init__(self):
                self.is_valid = True
                self.errors = []
        
        return ValidationResult()
