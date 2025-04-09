"""
Symbolic Execution module for Edit Check Rule Validation System.

This module implements symbolic execution techniques to generate test cases
by systematically exploring execution paths through rules.
"""

import re
import z3
from typing import List, Dict, Any, Tuple, Set, Optional, Union
from datetime import datetime, timedelta

from ..models.data_models import EditCheckRule, StudySpecification, TestCase, FieldType
from ..utils.logger import Logger

logger = Logger(__name__)

class SymbolicExecutor:
    """Generate test cases using symbolic execution techniques."""
    
    def __init__(self):
        """Initialize the symbolic executor."""
        # Patterns for extracting comparisons
        self.comparison_pattern = re.compile(r'([A-Za-z0-9_.]+)\s*([<>=!]+)\s*([A-Za-z0-9_."\']+)')
        self.logical_op_pattern = re.compile(r'\b(AND|OR|NOT)\b', re.IGNORECASE)
        
        # Z3 solver
        self.solver = z3.Solver()
        
        # Mapping of field types to Z3 types
        self.z3_type_mapping = {
            FieldType.NUMBER: 'Real',
            FieldType.DATE: 'Int',  # Dates represented as days since epoch
            FieldType.DATETIME: 'Int',  # Datetime represented as seconds since epoch
            FieldType.TEXT: 'String',
            FieldType.CATEGORICAL: 'String',
            FieldType.BOOLEAN: 'Bool',
            FieldType.TIME: 'Int'  # Time represented as seconds since midnight
        }
    
    def generate_symbolic_tests(self, rule: EditCheckRule, specification: StudySpecification) -> List[TestCase]:
        """
        Generate test cases using symbolic execution.
        
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
            # Create symbolic variables for fields in the rule
            symbolic_vars, field_info = self._create_symbolic_variables(rule, specification)
            
            # Parse the rule condition into Z3 constraints
            constraint = self._parse_condition_to_z3(condition, symbolic_vars)
            
            if constraint is not None:
                # Generate positive test cases (satisfying the constraint)
                self.solver.reset()
                self.solver.add(constraint)
                if self.solver.check() == z3.sat:
                    model = self.solver.model()
                    positive_test = self._create_test_from_model(rule, model, field_info, True)
                    if positive_test:
                        test_cases.append(positive_test)
                
                # Generate negative test cases (violating the constraint)
                self.solver.reset()
                self.solver.add(z3.Not(constraint))
                if self.solver.check() == z3.sat:
                    model = self.solver.model()
                    negative_test = self._create_test_from_model(rule, model, field_info, False)
                    if negative_test:
                        test_cases.append(negative_test)
                
                # Generate boundary test cases
                boundary_tests = self._generate_boundary_tests(rule, constraint, symbolic_vars, field_info)
                test_cases.extend(boundary_tests)
        
        except Exception as e:
            logger.error(f"Error in symbolic execution for rule {rule.id}: {str(e)}")
        
        logger.info(f"Generated {len(test_cases)} symbolic test cases for rule {rule.id}")
        return test_cases
    
    def _create_symbolic_variables(
        self, rule: EditCheckRule, specification: StudySpecification
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """
        Create symbolic variables for fields in the rule.
        
        Args:
            rule: The rule to create variables for
            specification: The study specification
            
        Returns:
            Tuple of (symbolic variables dict, field info dict)
        """
        symbolic_vars = {}
        field_info = {}
        
        # Use formalized condition if available, otherwise use original condition
        condition = rule.formalized_condition or rule.condition
        
        # Extract field references from the condition
        field_refs = set()
        for match in self.comparison_pattern.finditer(condition):
            field_name = match.group(1)
            if not field_name.replace('.', '').isdigit() and not field_name.startswith('"'):
                field_refs.add(field_name)
        
        # Create symbolic variables for each field
        for field_ref in field_refs:
            if '.' in field_ref:
                form_name, field_name = field_ref.split('.', 1)
                
                # Get field type from specification
                field_type = FieldType.TEXT  # Default
                field = specification.get_field(form_name, field_name)
                if field:
                    field_type = field.type
                
                # Initialize form in field info if not exists
                if form_name not in field_info:
                    field_info[form_name] = {}
                
                # Store field info
                field_info[form_name][field_name] = {
                    'type': field_type,
                    'valid_values': self._get_valid_values(specification, form_name, field_name)
                }
                
                # Create symbolic variable based on field type
                if field_type == FieldType.NUMBER:
                    symbolic_vars[field_ref] = z3.Real(field_ref)
                elif field_type == FieldType.INTEGER:
                    symbolic_vars[field_ref] = z3.Int(field_ref)
                elif field_type == FieldType.DATE:
                    # Represent dates as integers (days since epoch)
                    symbolic_vars[field_ref] = z3.Int(field_ref)
                elif field_type == FieldType.CATEGORICAL:
                    # For categorical fields, use string theory
                    symbolic_vars[field_ref] = z3.String(field_ref)
                else:
                    # Default to string for text and other types
                    symbolic_vars[field_ref] = z3.String(field_ref)
        
        return symbolic_vars, field_info
    
    def _parse_condition_to_z3(self, condition: str, symbolic_vars: Dict[str, Any]) -> Optional[z3.BoolRef]:
        """
        Parse a rule condition into Z3 constraints.
        
        Args:
            condition: The rule condition
            symbolic_vars: Dictionary of symbolic variables
            
        Returns:
            Z3 constraint or None if parsing fails
        """
        try:
            # Replace logical operators with Python equivalents
            condition = re.sub(r'\bAND\b', 'and', condition, flags=re.IGNORECASE)
            condition = re.sub(r'\bOR\b', 'or', condition, flags=re.IGNORECASE)
            condition = re.sub(r'\bNOT\b', 'not', condition, flags=re.IGNORECASE)
            
            # Parse comparisons
            constraints = []
            for match in self.comparison_pattern.finditer(condition):
                left = match.group(1)
                op = match.group(2)
                right = match.group(3)
                
                # Check if left side is a field reference
                if left in symbolic_vars:
                    left_var = symbolic_vars[left]
                    
                    # Parse right side
                    if right in symbolic_vars:
                        # Right side is also a field reference
                        right_var = symbolic_vars[right]
                        constraint = self._create_comparison(left_var, op, right_var)
                    else:
                        # Right side is a literal
                        constraint = self._create_comparison_with_literal(left_var, op, right)
                    
                    if constraint is not None:
                        constraints.append(constraint)
            
            # Combine constraints based on logical operators
            if constraints:
                if len(constraints) == 1:
                    return constraints[0]
                else:
                    # For simplicity, we'll combine with AND
                    # In a real implementation, you'd need to parse the logical structure
                    return z3.And(*constraints)
            
            return None
        
        except Exception as e:
            logger.error(f"Error parsing condition to Z3: {str(e)}")
            return None
    
    def _create_comparison(self, left: Any, op: str, right: Any) -> Optional[z3.BoolRef]:
        """
        Create a Z3 comparison between two symbolic variables.
        
        Args:
            left: Left side variable
            op: Comparison operator
            right: Right side variable
            
        Returns:
            Z3 constraint or None if invalid
        """
        if op == '=':
            return left == right
        elif op == '!=':
            return left != right
        elif op == '>':
            return left > right
        elif op == '>=':
            return left >= right
        elif op == '<':
            return left < right
        elif op == '<=':
            return left <= right
        else:
            return None
    
    def _create_comparison_with_literal(self, var: Any, op: str, literal: str) -> Optional[z3.BoolRef]:
        """
        Create a Z3 comparison between a symbolic variable and a literal.
        
        Args:
            var: Symbolic variable
            op: Comparison operator
            literal: Literal value as string
            
        Returns:
            Z3 constraint or None if invalid
        """
        try:
            # Check if the variable is numeric
            if isinstance(var, z3.ArithRef):
                # Try to convert literal to number
                try:
                    if '.' in literal:
                        literal_val = float(literal)
                    else:
                        literal_val = int(literal)
                    
                    if op == '=':
                        return var == literal_val
                    elif op == '!=':
                        return var != literal_val
                    elif op == '>':
                        return var > literal_val
                    elif op == '>=':
                        return var >= literal_val
                    elif op == '<':
                        return var < literal_val
                    elif op == '<=':
                        return var <= literal_val
                except ValueError:
                    # Not a numeric literal
                    return None
            
            # Check if the variable is a string
            elif isinstance(var, z3.SeqRef):
                # Remove quotes if present
                if (literal.startswith('"') and literal.endswith('"')) or \
                   (literal.startswith("'") and literal.endswith("'")):
                    literal = literal[1:-1]
                
                if op == '=':
                    return var == literal
                elif op == '!=':
                    return var != literal
                else:
                    # String comparison for other operators not supported
                    return None
            
            return None
        
        except Exception as e:
            logger.error(f"Error creating comparison with literal: {str(e)}")
            return None
    
    def _create_test_from_model(
        self, 
        rule: EditCheckRule,
        model: z3.ModelRef,
        field_info: Dict[str, Dict[str, Any]],
        is_positive: bool
    ) -> Optional[TestCase]:
        """
        Create a test case from a Z3 model.
        
        Args:
            rule: The rule to create a test for
            model: Z3 model
            field_info: Field information
            is_positive: Whether this is a positive test
            
        Returns:
            Test case or None if creation fails
        """
        try:
            test_data = {}
            
            # Process each field in the model
            for var in model:
                var_name = str(var)
                if '.' in var_name:
                    form_name, field_name = var_name.split('.', 1)
                    
                    # Initialize form in test data if not exists
                    if form_name not in test_data:
                        test_data[form_name] = {}
                    
                    # Get field type
                    field_type = FieldType.TEXT  # Default
                    if form_name in field_info and field_name in field_info[form_name]:
                        field_type = field_info[form_name]['type']
                    
                    # Convert model value to appropriate type
                    value = model[var]
                    if field_type == FieldType.NUMBER:
                        # Convert rational to float
                        if z3.is_rational_value(value):
                            num = float(value.numerator_as_long())
                            den = float(value.denominator_as_long())
                            test_data[form_name][field_name] = num / den
                        else:
                            test_data[form_name][field_name] = float(str(value))
                    elif field_type == FieldType.INTEGER:
                        test_data[form_name][field_name] = value.as_long()
                    elif field_type == FieldType.DATE:
                        # Convert days since epoch to date string
                        days = value.as_long()
                        date = datetime(1970, 1, 1) + timedelta(days=days)
                        test_data[form_name][field_name] = date.strftime("%Y-%m-%d")
                    else:
                        # For string and categorical, convert to string
                        test_data[form_name][field_name] = str(value)
            
            # Create the test case
            return TestCase(
                rule_id=rule.id,
                description=f"{'Positive' if is_positive else 'Negative'} symbolic test for rule {rule.id}",
                expected_result=is_positive,
                test_data=test_data,
                is_positive=is_positive
            )
        
        except Exception as e:
            logger.error(f"Error creating test from model: {str(e)}")
            return None
    
    def _generate_boundary_tests(
        self,
        rule: EditCheckRule,
        constraint: z3.BoolRef,
        symbolic_vars: Dict[str, Any],
        field_info: Dict[str, Dict[str, Any]]
    ) -> List[TestCase]:
        """
        Generate boundary test cases.
        
        Args:
            rule: The rule to generate tests for
            constraint: Z3 constraint
            symbolic_vars: Dictionary of symbolic variables
            field_info: Field information
            
        Returns:
            List of boundary test cases
        """
        boundary_tests = []
        
        # For each numeric variable, generate tests at the boundaries
        for var_name, var in symbolic_vars.items():
            if isinstance(var, z3.ArithRef):
                if '.' in var_name:
                    form_name, field_name = var_name.split('.', 1)
                    
                    # Try to find upper and lower bounds
                    for boundary_value, is_positive in self._find_boundaries(constraint, var):
                        # Create a test case with the boundary value
                        test_data = {}
                        
                        # Initialize form in test data
                        if form_name not in test_data:
                            test_data[form_name] = {}
                        
                        # Set the boundary value
                        test_data[form_name][field_name] = boundary_value
                        
                        # Create the test case
                        boundary_test = TestCase(
                            rule_id=rule.id,
                            description=f"Boundary test for rule {rule.id} with {form_name}.{field_name}={boundary_value}",
                            expected_result=is_positive,
                            test_data=test_data,
                            is_positive=is_positive
                        )
                        
                        boundary_tests.append(boundary_test)
        
        return boundary_tests
    
    def _find_boundaries(self, constraint: z3.BoolRef, var: z3.ArithRef) -> List[Tuple[float, bool]]:
        """
        Find boundary values for a variable.
        
        Args:
            constraint: Z3 constraint
            var: Variable to find boundaries for
            
        Returns:
            List of (boundary value, is positive) tuples
        """
        boundaries = []
        
        # Use binary search to find the boundary
        lower_bound = -1000.0  # Arbitrary lower bound
        upper_bound = 1000.0   # Arbitrary upper bound
        
        # Check if lower bound satisfies the constraint
        self.solver.reset()
        self.solver.add(constraint)
        self.solver.add(var == lower_bound)
        lower_satisfies = self.solver.check() == z3.sat
        
        # Check if upper bound satisfies the constraint
        self.solver.reset()
        self.solver.add(constraint)
        self.solver.add(var == upper_bound)
        upper_satisfies = self.solver.check() == z3.sat
        
        # If both satisfy or both don't satisfy, no boundary exists
        if lower_satisfies == upper_satisfies:
            return boundaries
        
        # Binary search for the boundary
        for _ in range(10):  # Limit iterations
            mid = (lower_bound + upper_bound) / 2
            
            self.solver.reset()
            self.solver.add(constraint)
            self.solver.add(var == mid)
            mid_satisfies = self.solver.check() == z3.sat
            
            if mid_satisfies == lower_satisfies:
                lower_bound = mid
            else:
                upper_bound = mid
        
        # Add boundary values
        boundary = (lower_bound + upper_bound) / 2
        boundaries.append((boundary - 0.001, lower_satisfies))
        boundaries.append((boundary + 0.001, upper_satisfies))
        
        return boundaries
    
    def _get_valid_values(self, specification: StudySpecification, form_name: str, field_name: str) -> List[str]:
        """
        Get valid values for a categorical field.
        
        Args:
            specification: Study specification
            form_name: Form name
            field_name: Field name
            
        Returns:
            List of valid values
        """
        field = specification.get_field(form_name, field_name)
        if field and field.valid_values:
            return [v.strip() for v in field.valid_values.split(',')]
        return []
