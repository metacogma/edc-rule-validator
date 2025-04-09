# Edit Check Rule Validation System: Advanced Techniques

This document provides a comprehensive overview of the advanced validation, formalization, and test generation techniques implemented in the Edit Check Rule Validation System.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Rule Validation Process](#rule-validation-process)
3. [Rule Formalization Process](#rule-formalization-process)
4. [Advanced Test Generation](#advanced-test-generation)
5. [Workflow Orchestration](#workflow-orchestration)
6. [Configuration Options](#configuration-options)

## System Architecture

The Edit Check Rule Validation System follows a modular architecture with the following key components:

```
src/
├── models/            # Data models for rules, specifications, and test cases
├── parsers/           # Parsers for rule files and study specifications
├── validators/        # Rule validators and verifiers
├── llm/               # LLM integration for rule formalization
├── test_generation/   # Advanced test generation techniques
└── workflow/          # Workflow orchestration
```

## Rule Validation Process

The rule validation process is handled by the `RuleValidator` class and involves several layers of validation:

### 1. Field and Form Validation

```python
# Extract forms and fields from the rule condition
forms_fields = self._extract_forms_fields(rule.condition)

# Validate forms and fields against specification
for form_name, field_name in forms_fields:
    # Check if form exists
    if form_name not in specification.forms:
        result.add_error('invalid_form', f"Form '{form_name}' referenced in rule {rule.id} does not exist")
        continue
    
    # Check if field exists in form
    form = specification.forms.get(form_name)
    field_exists = False
    
    for field in form.fields:
        if field.name == field_name:
            field_exists = True
            break
    
    if not field_exists:
        result.add_error('invalid_field', f"Field '{field_name}' in form '{form_name}' does not exist")
```

This ensures all referenced forms and fields actually exist in the study specification.

### 2. Syntax Validation

```python
def _validate_rule_syntax(self, condition: str):
    errors = []
    
    # Check for balanced parentheses
    if condition.count('(') != condition.count(')'):
        errors.append(('unbalanced_parentheses', f"Unbalanced parentheses in condition"))
    
    # Check for invalid comparison operators
    words = re.findall(r'\b\w+\b', condition)
    for word in words:
        if word.upper() in ['EQUAL', 'EQUALS', 'EQUAL TO']:
            errors.append(('invalid_operator', f"Invalid operator '{word}'. Use '=' instead."))
    
    # Check for missing logical operators
    if ' AND' not in condition.upper() and ' OR' not in condition.upper() and ',' in condition:
        errors.append(('missing_logical_operator', f"Possible missing logical operator (AND/OR)"))
    
    return errors
```

This checks for common syntax issues like unbalanced parentheses, invalid operators, and missing logical connectors.

### 3. Semantic Validation

```python
def _validate_rule_semantics(self, condition: str, specification: StudySpecification):
    errors = []
    
    # Extract form.field references
    form_field_refs = self.form_field_pattern.findall(condition)
    
    for form_name, field_name in form_field_refs:
        # Get the field
        field = specification.get_field(form_name, field_name)
        if not field:
            continue
        
        # Check for type compatibility in comparisons
        if field.type.value in ['number', 'date', 'datetime', 'time']:
            # Check for string comparisons with numeric fields
            if f"{form_name}.{field_name}" in condition and '"' in condition and '=' in condition:
                errors.append(('type_mismatch', f"Possible type mismatch: comparing {field.type.value} with string"))
```

This validates semantic correctness, such as ensuring type compatibility in comparisons (e.g., not comparing a number field with a string).

## Rule Formalization Process

Rule formalization uses the LLM orchestrator to convert natural language or semi-structured rules into a formal, executable representation:

### 1. Context Preparation

```python
def _prepare_specification_context(self, specification: StudySpecification, rule: EditCheckRule):
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
```

This extracts relevant context from the study specification to help the LLM understand the domain.

### 2. Few-Shot Examples

The system provides few-shot examples to guide the LLM:

```python
def _get_formalization_examples(self):
    return [
        {
            "rule": "If DEMOGRAPHICS.AGE < 18, then DEMOGRAPHICS.CONSENT_GUARDIAN must be 'YES'",
            "formalized": "(DEMOGRAPHICS.AGE < 18) -> (DEMOGRAPHICS.CONSENT_GUARDIAN == 'YES')"
        },
        {
            "rule": "VITALS.TEMPERATURE must be between 36.0 and 38.0",
            "formalized": "(VITALS.TEMPERATURE >= 36.0) and (VITALS.TEMPERATURE <= 38.0)"
        }
    ]
```

These examples demonstrate the expected format for formalized rules.

### 3. Chain-of-Thought Prompting

```python
def _construct_formalization_prompt(self, rule, context, examples):
    prompt = f"""
    # Task: Formalize the following clinical trial edit check rule
    
    ## Rule Information
    - Rule ID: {rule.id}
    - Description: {rule.description}
    - Condition: {rule.condition}
    
    ## Study Specification Context
    {json.dumps(context, indent=2)}
    
    ## Examples of Rule Formalization
    {self._format_examples(examples)}
    
    ## Instructions
    1. Analyze the rule condition
    2. Identify all variables, operators, and logical connections
    3. Translate to a formal logical expression using Python-like syntax
    4. Use proper operators: ==, !=, <, <=, >, >=, and, or, not, in, etc.
    5. Explain your reasoning step by step
    6. Provide the final formalized rule in the format: FORMALIZED_RULE: (expression)
    
    ## Your Formalization Process:
    """
```

This structured prompt guides the LLM through a step-by-step reasoning process.

### 4. Response Extraction

```python
def _extract_formalized_rule(self, response_text):
    # Look for the formalized rule marker
    marker = "FORMALIZED_RULE:"
    if marker in response_text:
        # Extract the line with the formalized rule
        lines = response_text.split('\n')
        for line in lines:
            if marker in line:
                # Extract the formalized rule
                formalized_rule = line.split(marker)[1].strip()
                # Clean up any extra quotes or formatting
                formalized_rule = formalized_rule.strip('"\'')
                return formalized_rule
```

This extracts the formalized rule from the LLM's response.

## Advanced Test Generation

The system implements several advanced techniques for generating test cases:

### 1. Metamorphic Testing

Generates test cases based on metamorphic relations between inputs and outputs.

```python
class MetamorphicTester:
    def generate_metamorphic_tests(self, rule, specification):
        # Generate base test
        base_test = self._generate_base_test(rule, specification)
        
        # Generate follow-up tests using metamorphic relations
        follow_up_tests = []
        for relation in self.metamorphic_relations:
            follow_up_test = self._apply_metamorphic_relation(base_test, relation, rule, specification)
            follow_up_tests.append(follow_up_test)
            
        return [base_test] + follow_up_tests
```

### 2. Symbolic Execution

Uses symbolic execution to systematically explore execution paths.

```python
class SymbolicExecutor:
    def generate_symbolic_tests(self, rule, specification):
        # Create symbolic variables
        symbolic_vars = self._create_symbolic_variables(rule, specification)
        
        # Parse condition into Z3 constraints
        constraints = self._parse_condition_to_constraints(rule.formalized_condition, symbolic_vars)
        
        # Generate test cases from constraints
        test_cases = self._generate_test_cases_from_constraints(constraints, symbolic_vars, rule)
        
        return test_cases
```

### 3. Adversarial Testing

Creates adversarial test cases using counterfactual reasoning.

```python
class AdversarialTestGenerator:
    def generate_adversarial_tests(self, rule, specification):
        strategies = [
            self._generate_boundary_tests,
            self._generate_missing_value_tests,
            self._generate_type_confusion_tests,
            self._generate_logical_inversion_tests,
            self._generate_special_value_tests
        ]
        
        all_tests = []
        for strategy in strategies:
            tests = strategy(rule, specification)
            all_tests.extend(tests)
            
        return all_tests
```

### 4. Causal Inference

Generates test cases exploring causal relationships between variables.

```python
class CausalInferenceGenerator:
    def generate_causal_tests(self, rule, specification):
        # Build causal graph
        causal_graph = self._build_causal_graph(rule, specification)
        
        # Generate intervention tests
        intervention_tests = self._generate_intervention_tests(causal_graph, rule)
        
        # Generate counterfactual tests
        counterfactual_tests = self._generate_counterfactual_tests(causal_graph, rule)
        
        return intervention_tests + counterfactual_tests
```

## Workflow Orchestration

The workflow orchestrator manages the entire process from parsing to test generation:

```python
def _build_workflow(self):
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
    
    # More conditional edges...
    
    return workflow
```

### Why Validation and Formalization Are Optional

#### Validation Is Conditionally Optional

Validation always happens, but what happens next depends on configuration. If rules fail validation, they're excluded from later steps, but the workflow continues with valid rules.

#### Formalization Is Truly Optional

```python
def _should_formalize_rules(self, state: WorkflowState) -> bool:
    return state.config.get("formalize_rules", True)
```

Formalization can be skipped if:

1. **Pre-formalized Rules**: If rules are already in a formal format, formalization is redundant.
2. **No LLM Access**: In environments without LLM access or API keys.
3. **Cost/Time Constraints**: To save API costs or processing time.
4. **Basic Validation Only**: If you're only interested in basic validation.

### Benefits of Making These Steps Optional

1. **Flexibility**: Adapts to different environments and requirements
2. **Efficiency**: Skips unnecessary steps for pre-processed rules
3. **Fallback Options**: Works even without LLM access
4. **Cost Management**: Reduces API calls when not needed

## Configuration Options

The system provides various configuration options to customize the workflow:

```python
config = {
    "formalize_rules": True,       # Whether to formalize rules using LLM
    "verify_with_z3": True,        # Whether to verify rules using Z3
    "generate_tests": True,        # Whether to generate test cases
    "test_techniques": [           # Test generation techniques to use
        "metamorphic", 
        "symbolic", 
        "adversarial", 
        "causal"
    ],
    "test_cases_per_rule": 5,      # Target number of test cases per rule
    "parallel_test_generation": True,  # Whether to generate tests in parallel
    "max_retries": 3               # Maximum number of retries for LLM calls
}
```

These options allow users to tailor the system to their specific needs, available resources, and time constraints.
