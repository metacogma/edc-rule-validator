"""
Causal Inference module for Edit Check Rule Validation System.

This module implements causal inference techniques to generate test cases
that explore causal relationships between variables in clinical trial data.
"""

import re
import copy
import random
import networkx as nx
from typing import List, Dict, Any, Tuple, Set, Optional
import numpy as np
from datetime import datetime, timedelta

from ..models.data_models import EditCheckRule, StudySpecification, TestCase, FieldType
from ..utils.logger import Logger

logger = Logger(__name__)

class CausalInferenceGenerator:
    """Generate test cases using causal inference techniques."""
    
    def __init__(self):
        """Initialize the causal inference generator."""
        # Patterns for extracting field references
        self.field_pattern = re.compile(r'([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)')
        
        # Patterns for extracting comparisons
        self.comparison_pattern = re.compile(r'([A-Za-z0-9_.]+)\s*([<>=!]+)\s*([A-Za-z0-9_."\']+)')
    
    def generate_causal_tests(self, rule: EditCheckRule, specification: StudySpecification) -> List[TestCase]:
        """
        Generate test cases using causal inference.
        
        Args:
            rule: The rule to generate test cases for
            specification: The study specification
            
        Returns:
            List of test cases
        """
        test_cases = []
        
        # Use formalized condition if available, otherwise use original condition
        condition = rule.formalized_condition or rule.condition
        
        try:
            # Extract field references from the condition
            field_refs = self._extract_field_references(condition)
            
            # Build a causal graph
            causal_graph = self._build_causal_graph(rule, specification, field_refs)
            
            # Generate test cases based on causal interventions
            intervention_tests = self._generate_intervention_tests(rule, specification, causal_graph)
            test_cases.extend(intervention_tests)
            
            # Generate counterfactual test cases
            counterfactual_tests = self._generate_counterfactual_tests(rule, specification, causal_graph)
            test_cases.extend(counterfactual_tests)
            
            # Generate tests for confounding variables
            confounding_tests = self._generate_confounding_tests(rule, specification, causal_graph)
            test_cases.extend(confounding_tests)
        
        except Exception as e:
            logger.error(f"Error in causal inference test generation for rule {rule.id}: {str(e)}")
        
        logger.info(f"Generated {len(test_cases)} causal inference test cases for rule {rule.id}")
        return test_cases
    
    def _extract_field_references(self, condition: str) -> Set[str]:
        """
        Extract field references from a rule condition.
        
        Args:
            condition: Rule condition
            
        Returns:
            Set of field references
        """
        field_refs = set()
        
        # Extract field references
        for match in self.field_pattern.finditer(condition):
            form_name = match.group(1)
            field_name = match.group(2)
            field_refs.add(f"{form_name}.{field_name}")
        
        return field_refs
    
    def _build_causal_graph(
        self,
        rule: EditCheckRule,
        specification: StudySpecification,
        field_refs: Set[str]
    ) -> nx.DiGraph:
        """
        Build a causal graph for the rule.
        
        Args:
            rule: The rule to build a graph for
            specification: The study specification
            field_refs: Set of field references
            
        Returns:
            Causal graph
        """
        # Create a directed graph
        graph = nx.DiGraph()
        
        # Add nodes for each field reference
        for field_ref in field_refs:
            graph.add_node(field_ref)
        
        # Add causal relationships based on domain knowledge
        self._add_temporal_relationships(graph, specification, field_refs)
        self._add_form_relationships(graph, specification, field_refs)
        self._add_rule_specific_relationships(graph, rule, field_refs)
        
        return graph
    
    def _add_temporal_relationships(
        self,
        graph: nx.DiGraph,
        specification: StudySpecification,
        field_refs: Set[str]
    ):
        """
        Add temporal relationships to the causal graph.
        
        Args:
            graph: Causal graph
            specification: The study specification
            field_refs: Set of field references
        """
        # Identify date fields
        date_fields = set()
        for field_ref in field_refs:
            if '.' in field_ref:
                form_name, field_name = field_ref.split('.', 1)
                field_type = self._get_field_type(specification, form_name, field_name)
                if field_type == FieldType.DATE:
                    date_fields.add(field_ref)
        
        # Add edges for temporal relationships
        # In clinical trials, earlier dates often influence later dates
        date_field_list = list(date_fields)
        for i in range(len(date_field_list)):
            for j in range(i + 1, len(date_field_list)):
                # Add a directed edge from the earlier date to the later date
                # This is a simplification; in a real system, you would use domain knowledge
                graph.add_edge(date_field_list[i], date_field_list[j], relationship="temporal")
    
    def _add_form_relationships(
        self,
        graph: nx.DiGraph,
        specification: StudySpecification,
        field_refs: Set[str]
    ):
        """
        Add form-based relationships to the causal graph.
        
        Args:
            graph: Causal graph
            specification: The study specification
            field_refs: Set of field references
        """
        # Group fields by form
        form_fields = {}
        for field_ref in field_refs:
            if '.' in field_ref:
                form_name, field_name = field_ref.split('.', 1)
                if form_name not in form_fields:
                    form_fields[form_name] = []
                form_fields[form_name].append(field_ref)
        
        # Add edges for fields within the same form
        # Fields in the same form often have causal relationships
        for form_name, fields in form_fields.items():
            for i in range(len(fields)):
                for j in range(i + 1, len(fields)):
                    # Add a bidirectional edge between fields in the same form
                    graph.add_edge(fields[i], fields[j], relationship="form")
                    graph.add_edge(fields[j], fields[i], relationship="form")
    
    def _add_rule_specific_relationships(
        self,
        graph: nx.DiGraph,
        rule: EditCheckRule,
        field_refs: Set[str]
    ):
        """
        Add rule-specific relationships to the causal graph.
        
        Args:
            graph: Causal graph
            rule: The rule
            field_refs: Set of field references
        """
        # Use formalized condition if available, otherwise use original condition
        condition = rule.formalized_condition or rule.condition
        
        # Extract comparisons from the condition
        comparisons = []
        for match in self.comparison_pattern.finditer(condition):
            left = match.group(1)
            op = match.group(2)
            right = match.group(3)
            
            # Add to comparisons if both sides are field references
            if left in field_refs and right in field_refs:
                comparisons.append((left, op, right))
        
        # Add edges for direct comparisons
        for left, op, right in comparisons:
            # Add a bidirectional edge between compared fields
            graph.add_edge(left, right, relationship="comparison", operator=op)
            graph.add_edge(right, left, relationship="comparison", operator=self._invert_operator(op))
    
    def _invert_operator(self, op: str) -> str:
        """
        Invert a comparison operator.
        
        Args:
            op: Comparison operator
            
        Returns:
            Inverted operator
        """
        if op == '>':
            return '<'
        elif op == '>=':
            return '<='
        elif op == '<':
            return '>'
        elif op == '<=':
            return '>='
        elif op == '=':
            return '='
        elif op == '!=':
            return '!='
        return op
    
    def _generate_intervention_tests(
        self,
        rule: EditCheckRule,
        specification: StudySpecification,
        causal_graph: nx.DiGraph
    ) -> List[TestCase]:
        """
        Generate test cases based on causal interventions.
        
        Args:
            rule: The rule to generate test cases for
            specification: The study specification
            causal_graph: Causal graph
            
        Returns:
            List of test cases
        """
        test_cases = []
        
        # Identify key nodes in the causal graph
        # These are nodes with high centrality
        centrality = nx.degree_centrality(causal_graph)
        key_nodes = sorted(centrality, key=centrality.get, reverse=True)[:3]  # Top 3 nodes
        
        # For each key node, generate intervention tests
        for node in key_nodes:
            if '.' in node:
                form_name, field_name = node.split('.', 1)
                
                # Get field type
                field_type = self._get_field_type(specification, form_name, field_name)
                
                # Generate intervention values based on field type
                intervention_values = self._generate_intervention_values(field_type)
                
                # Create test cases for each intervention value
                for value in intervention_values:
                    # Create test data with the intervention
                    test_data = {form_name: {field_name: value}}
                    
                    # Add values for other fields based on causal relationships
                    self._propagate_intervention(test_data, node, value, causal_graph, specification)
                    
                    # Create the test case
                    test_case = TestCase(
                        rule_id=rule.id,
                        description=f"Causal intervention test for rule {rule.id} with {node}={value}",
                        expected_result=True,  # Assume the intervention satisfies the rule
                        test_data=test_data,
                        is_positive=True
                    )
                    
                    test_cases.append(test_case)
        
        return test_cases
    
    def _generate_intervention_values(self, field_type: FieldType) -> List[Any]:
        """
        Generate intervention values for a field.
        
        Args:
            field_type: Field type
            
        Returns:
            List of intervention values
        """
        if field_type == FieldType.NUMBER:
            return [0, 10, 100]
        elif field_type == FieldType.INTEGER:
            return [0, 1, 10]
        elif field_type == FieldType.DATE:
            base_date = datetime.now()
            return [
                base_date.strftime("%Y-%m-%d"),
                (base_date - timedelta(days=30)).strftime("%Y-%m-%d"),
                (base_date + timedelta(days=30)).strftime("%Y-%m-%d")
            ]
        elif field_type == FieldType.CATEGORICAL:
            return ["Category A", "Category B", "Other"]
        else:
            return ["Test Value", ""]
    
    def _propagate_intervention(
        self,
        test_data: Dict[str, Dict[str, Any]],
        intervention_node: str,
        intervention_value: Any,
        causal_graph: nx.DiGraph,
        specification: StudySpecification
    ):
        """
        Propagate an intervention through the causal graph.
        
        Args:
            test_data: Test data to update
            intervention_node: Node where the intervention is applied
            intervention_value: Intervention value
            causal_graph: Causal graph
            specification: Study specification
        """
        # Get descendants of the intervention node
        descendants = nx.descendants(causal_graph, intervention_node)
        
        # Update values for descendants based on causal relationships
        for descendant in descendants:
            if '.' in descendant:
                form_name, field_name = descendant.split('.', 1)
                
                # Initialize form in test data if not exists
                if form_name not in test_data:
                    test_data[form_name] = {}
                
                # Get field type
                field_type = self._get_field_type(specification, form_name, field_name)
                
                # Set field value based on causal relationship
                edge_data = causal_graph.get_edge_data(intervention_node, descendant)
                relationship = edge_data.get('relationship', 'unknown') if edge_data else 'unknown'
                
                if relationship == 'temporal':
                    # For temporal relationships, set a later date
                    if field_type == FieldType.DATE and isinstance(intervention_value, str):
                        try:
                            date = datetime.strptime(intervention_value, "%Y-%m-%d")
                            test_data[form_name][field_name] = (date + timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
                        except ValueError:
                            test_data[form_name][field_name] = datetime.now().strftime("%Y-%m-%d")
                
                elif relationship == 'form':
                    # For form relationships, set a related value
                    if field_type == FieldType.NUMBER and isinstance(intervention_value, (int, float)):
                        test_data[form_name][field_name] = intervention_value + random.uniform(-10, 10)
                    elif field_type == FieldType.INTEGER and isinstance(intervention_value, int):
                        test_data[form_name][field_name] = intervention_value + random.randint(-5, 5)
                    elif field_type == FieldType.CATEGORICAL:
                        test_data[form_name][field_name] = f"Related to {intervention_value}"
                    else:
                        test_data[form_name][field_name] = f"Related to {intervention_value}"
                
                elif relationship == 'comparison':
                    # For comparison relationships, set a value based on the operator
                    operator = edge_data.get('operator', '=') if edge_data else '='
                    
                    if field_type == FieldType.NUMBER and isinstance(intervention_value, (int, float)):
                        if operator == '>':
                            test_data[form_name][field_name] = intervention_value - random.uniform(1, 10)
                        elif operator == '>=':
                            test_data[form_name][field_name] = intervention_value - random.uniform(0, 10)
                        elif operator == '<':
                            test_data[form_name][field_name] = intervention_value + random.uniform(1, 10)
                        elif operator == '<=':
                            test_data[form_name][field_name] = intervention_value + random.uniform(0, 10)
                        elif operator == '=':
                            test_data[form_name][field_name] = intervention_value
                        elif operator == '!=':
                            test_data[form_name][field_name] = intervention_value + random.choice([-10, 10])
                    
                    elif field_type == FieldType.DATE and isinstance(intervention_value, str):
                        try:
                            date = datetime.strptime(intervention_value, "%Y-%m-%d")
                            if operator in ['>', '>=']:
                                test_data[form_name][field_name] = (date - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
                            elif operator in ['<', '<=']:
                                test_data[form_name][field_name] = (date + timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
                            elif operator == '=':
                                test_data[form_name][field_name] = intervention_value
                            elif operator == '!=':
                                test_data[form_name][field_name] = (date + timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
                        except ValueError:
                            test_data[form_name][field_name] = datetime.now().strftime("%Y-%m-%d")
                
                else:
                    # For unknown relationships, set a default value
                    if field_type == FieldType.NUMBER:
                        test_data[form_name][field_name] = random.uniform(0, 100)
                    elif field_type == FieldType.INTEGER:
                        test_data[form_name][field_name] = random.randint(0, 100)
                    elif field_type == FieldType.DATE:
                        test_data[form_name][field_name] = datetime.now().strftime("%Y-%m-%d")
                    elif field_type == FieldType.CATEGORICAL:
                        test_data[form_name][field_name] = "Category A"
                    else:
                        test_data[form_name][field_name] = "Test Value"
    
    def _generate_counterfactual_tests(
        self,
        rule: EditCheckRule,
        specification: StudySpecification,
        causal_graph: nx.DiGraph
    ) -> List[TestCase]:
        """
        Generate counterfactual test cases.
        
        Args:
            rule: The rule to generate test cases for
            specification: The study specification
            causal_graph: Causal graph
            
        Returns:
            List of test cases
        """
        test_cases = []
        
        # Identify key nodes in the causal graph
        # These are nodes with high centrality
        centrality = nx.degree_centrality(causal_graph)
        key_nodes = sorted(centrality, key=centrality.get, reverse=True)[:2]  # Top 2 nodes
        
        # For each key node, generate a counterfactual test
        for node in key_nodes:
            if '.' in node:
                form_name, field_name = node.split('.', 1)
                
                # Get field type
                field_type = self._get_field_type(specification, form_name, field_name)
                
                # Generate a base value
                base_value = self._generate_base_value(field_type)
                
                # Create base test data
                base_test_data = {form_name: {field_name: base_value}}
                
                # Propagate the base value through the causal graph
                self._propagate_intervention(base_test_data, node, base_value, causal_graph, specification)
                
                # Create a counterfactual value
                counterfactual_value = self._generate_counterfactual_value(field_type, base_value)
                
                # Create counterfactual test data
                counterfactual_test_data = copy.deepcopy(base_test_data)
                counterfactual_test_data[form_name][field_name] = counterfactual_value
                
                # Create the counterfactual test case
                counterfactual_test = TestCase(
                    rule_id=rule.id,
                    description=f"Counterfactual test for rule {rule.id} with {node}={counterfactual_value}",
                    expected_result=False,  # Assume the counterfactual violates the rule
                    test_data=counterfactual_test_data,
                    is_positive=False
                )
                
                test_cases.append(counterfactual_test)
        
        return test_cases
    
    def _generate_base_value(self, field_type: FieldType) -> Any:
        """
        Generate a base value for a field.
        
        Args:
            field_type: Field type
            
        Returns:
            Base value
        """
        if field_type == FieldType.NUMBER:
            return random.uniform(10, 50)
        elif field_type == FieldType.INTEGER:
            return random.randint(10, 50)
        elif field_type == FieldType.DATE:
            return datetime.now().strftime("%Y-%m-%d")
        elif field_type == FieldType.CATEGORICAL:
            return "Category A"
        else:
            return "Base Value"
    
    def _generate_counterfactual_value(self, field_type: FieldType, base_value: Any) -> Any:
        """
        Generate a counterfactual value for a field.
        
        Args:
            field_type: Field type
            base_value: Base value
            
        Returns:
            Counterfactual value
        """
        if field_type == FieldType.NUMBER and isinstance(base_value, (int, float)):
            return base_value * -1  # Opposite sign
        elif field_type == FieldType.INTEGER and isinstance(base_value, int):
            return base_value * -1  # Opposite sign
        elif field_type == FieldType.DATE and isinstance(base_value, str):
            try:
                date = datetime.strptime(base_value, "%Y-%m-%d")
                return (date + timedelta(days=180)).strftime("%Y-%m-%d")  # 6 months later
            except ValueError:
                return datetime.now().strftime("%Y-%m-%d")
        elif field_type == FieldType.CATEGORICAL:
            if base_value == "Category A":
                return "Category B"
            else:
                return "Category A"
        else:
            return "Counterfactual Value"
    
    def _generate_confounding_tests(
        self,
        rule: EditCheckRule,
        specification: StudySpecification,
        causal_graph: nx.DiGraph
    ) -> List[TestCase]:
        """
        Generate tests for confounding variables.
        
        Args:
            rule: The rule to generate test cases for
            specification: The study specification
            causal_graph: Causal graph
            
        Returns:
            List of test cases
        """
        test_cases = []
        
        # Identify potential confounding variables
        # These are nodes that have multiple outgoing edges
        confounders = [node for node, degree in causal_graph.out_degree() if degree > 1]
        
        # For each confounder, generate a test
        for confounder in confounders:
            if '.' in confounder:
                form_name, field_name = confounder.split('.', 1)
                
                # Get field type
                field_type = self._get_field_type(specification, form_name, field_name)
                
                # Generate a confounder value
                confounder_value = self._generate_base_value(field_type)
                
                # Create test data with the confounder
                test_data = {form_name: {field_name: confounder_value}}
                
                # Get descendants of the confounder
                descendants = list(nx.descendants(causal_graph, confounder))
                
                # Randomly select two descendants
                if len(descendants) >= 2:
                    selected_descendants = random.sample(descendants, 2)
                    
                    # Set values for the selected descendants
                    for descendant in selected_descendants:
                        if '.' in descendant:
                            desc_form, desc_field = descendant.split('.', 1)
                            
                            # Initialize form in test data if not exists
                            if desc_form not in test_data:
                                test_data[desc_form] = {}
                            
                            # Get descendant field type
                            desc_field_type = self._get_field_type(specification, desc_form, desc_field)
                            
                            # Set a value influenced by the confounder
                            if desc_field_type == FieldType.NUMBER:
                                test_data[desc_form][desc_field] = random.uniform(0, 100)
                            elif desc_field_type == FieldType.INTEGER:
                                test_data[desc_form][desc_field] = random.randint(0, 100)
                            elif desc_field_type == FieldType.DATE:
                                test_data[desc_form][desc_field] = datetime.now().strftime("%Y-%m-%d")
                            elif desc_field_type == FieldType.CATEGORICAL:
                                test_data[desc_form][desc_field] = "Category A"
                            else:
                                test_data[desc_form][desc_field] = "Test Value"
                    
                    # Create the test case
                    test_case = TestCase(
                        rule_id=rule.id,
                        description=f"Confounding test for rule {rule.id} with {confounder}={confounder_value}",
                        expected_result=True,  # Assume the test satisfies the rule
                        test_data=test_data,
                        is_positive=True
                    )
                    
                    test_cases.append(test_case)
        
        return test_cases
    
    def _get_field_type(self, specification: StudySpecification, form_name: str, field_name: str) -> FieldType:
        """
        Get the type of a field from the specification.
        
        Args:
            specification: Study specification
            form_name: Form name
            field_name: Field name
            
        Returns:
            Field type
        """
        field = specification.get_field(form_name, field_name)
        if field:
            return field.type
        return FieldType.TEXT
