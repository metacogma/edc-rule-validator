import re
from typing import List, Dict, Any, Optional, Tuple, Set
from z3 import *

from ..models.data_models import EditCheckRule, StudySpecification, ValidationResult, FieldType
from ..utils.logger import Logger

logger = Logger(__name__)
class EnhancedZ3Verifier:
    """Enhanced Z3 verifier for clinical validation rules using formal methods."""
    
    def __init__(self):
        """Initialize the enhanced Z3 verifier."""
        self.solver = Solver()
        self.variables = {}
        self.variable_types = {}
        self.last_error = None
    
    def verify_rule(self, rule: EditCheckRule, specification: StudySpecification) -> ValidationResult:
        """
        Verify a rule using Z3 formal verification.
        
        Args:
            rule: The rule to verify
            specification: The study specification
            
        Returns:
            Validation result with verification outcome
        """
        result = ValidationResult(rule_id=rule.id, is_valid=True)
        
        # Check if rule has formalized condition
        if not rule.formalized_condition:
            result.add_error(
                'missing_formalized_condition',
                f"Rule {rule.id} does not have a formalized condition for verification"
            )
            return result
        
        try:
            # Reset solver and variables
            self.solver = Solver()
            self.variables = {}
            self.variable_types = {}
            
            # Parse rule into Z3 formula
            z3_formula = self._parse_to_z3(rule.formalized_condition, specification)
            
            if z3_formula is None:
                result.add_error(
                    'parsing_error',
                    f"Could not parse formalized condition to Z3 formula: {rule.formalized_condition}"
                )
                return result
            
            # Perform verification tests
            
            # 1. Satisfiability check: Is the rule satisfiable (at least one solution)?
            self.solver.push()
            self.solver.add(z3_formula)
            sat_check = self.solver.check()
            
            if sat_check == unsat:
                result.add_error(
                    'unsatisfiable_rule',
                    f"Rule {rule.id} is unsatisfiable (always false)",
                    {'condition': rule.formalized_condition}
                )
            elif sat_check == sat:
                # Log a model (example of satisfying assignment)
                model = self.solver.model()
                satisfying_assignment = self._extract_model_values(model)
                result.add_info = {
                    'satisfiable': True,
                    'example_values': satisfying_assignment
                }
            self.solver.pop()
            
            # 2. Tautology check: Is the rule a tautology (always true)?
            self.solver.push()
            self.solver.add(Not(z3_formula))
            taut_check = self.solver.check()
            
            if taut_check == unsat:
                result.add_warning(
                    'tautology',
                    f"Rule {rule.id} is a tautology (always true)",
                    {'condition': rule.formalized_condition}
                )
            self.solver.pop()
            
            # 3. Redundancy detection: Check if rule has redundant parts
            redundancy = self._detect_redundancies(z3_formula)
            if redundancy:
                result.add_warning(
                    'redundant_condition',
                    f"Rule {rule.id} contains potentially redundant conditions: {redundancy}",
                    {'condition': rule.formalized_condition, 'redundancy': redundancy}
                )
            
            # 4. Edge case testing: Check behavior on edge cases
            edge_case_issues = self._test_edge_cases(z3_formula, specification)
            for issue_type, message, details in edge_case_issues:
                result.add_warning(issue_type, message, details)
            
            return result
            
        except Exception as e:
            self.last_error = str(e)
            result.add_error(
                'verification_error',
                f"Error verifying rule {rule.id}: {str(e)}",
                {'condition': rule.formalized_condition, 'exception': str(e)}
            )
            return result
    
    def _parse_to_z3(self, formalized_condition: str, specification: StudySpecification) -> Optional[z3.ExprRef]:
        """
        Parse formalized condition to Z3 formula with clinical domain awareness.
        
        Args:
            formalized_condition: The formalized rule condition
            specification: The study specification
            
        Returns:
            Z3 formula or None if parsing failed
        """
        try:
            # Handle IF-THEN-ELSE structure
            if_then_match = re.match(r'IF\s+(.+?)\s+THEN\s+(.+?)(?:\s+ELSE\s+(.+))?$', formalized_condition, re.IGNORECASE)
            
            if if_then_match:
                if_part = if_then_match.group(1).strip()
                then_part = if_then_match.group(2).strip()
                else_part = if_then_match.group(3).strip() if if_then_match.group(3) else None
                
                # Parse the IF and THEN parts
                z3_if = self._parse_expression(if_part, specification)
                z3_then = self._parse_expression(then_part, specification)
                
                if z3_if is None or z3_then is None:
                    return None
                
                # If ELSE part exists, parse it too
                if else_part:
                    z3_else = self._parse_expression(else_part, specification)
                    if z3_else is None:
                        return None
                    
                    # Return IF-THEN-ELSE as z3 If expression
                    return If(z3_if, z3_then, z3_else)
                else:
                    # Return IF-THEN as implication
                    return Implies(z3_if, z3_then)
            
            # If not IF-THEN, parse as regular expression
            return self._parse_expression(formalized_condition, specification)
            
        except Exception as e:
            self.last_error = str(e)
            return None
    
    def _parse_expression(self, expression: str, specification: StudySpecification) -> Optional[z3.ExprRef]:
        """
        Parse a logical expression into Z3 formula.
        
        Args:
            expression: The logical expression to parse
            specification: The study specification
            
        Returns:
            Z3 formula or None if parsing failed
        """
        # Handle parenthesized expressions
        if expression.startswith('(') and expression.endswith(')'):
            inner_expr = expression[1:-1].strip()
            return self._parse_expression(inner_expr, specification)
        
        # Handle logical operators: AND, OR, NOT
        if ' AND ' in expression:
            parts = [p.strip() for p in expression.split(' AND ')]
            z3_parts = [self._parse_expression(part, specification) for part in parts]
            
            # Filter out None values
            z3_parts = [p for p in z3_parts if p is not None]
            
            if not z3_parts:
                return None
                
            return And(*z3_parts)
            
        if ' OR ' in expression:
            parts = [p.strip() for p in expression.split(' OR ')]
            z3_parts = [self._parse_expression(part, specification) for part in parts]
            
            # Filter out None values
            z3_parts = [p for p in z3_parts if p is not None]
            
            if not z3_parts:
                return None
                
            return Or(*z3_parts)
            
        if expression.strip().startswith('NOT '):
            inner_expr = expression.strip()[4:].strip()
            z3_inner = self._parse_expression(inner_expr, specification)
            
            if z3_inner is None:
                return None
                
            return Not(z3_inner)
        
        # Handle comparison operators: =, !=, <, >, <=, >=, IN, NOT IN, BETWEEN
        for op in ['<=', '>=', '!=', '=', '<', '>', ' IN ', ' NOT IN ', ' BETWEEN ']:
            if op in expression:
                # Split the expression at the operator
                parts = expression.split(op, 1)
                left = parts[0].strip()
                right = parts[1].strip()
                
                # Parse left and right sides
                z3_left = self._parse_operand(left, specification)
                
                if z3_left is None:
                    return None
                
                # Handle special operators
                if op == ' IN ':
                    return self._parse_in_expression(z3_left, right, specification)
                elif op == ' NOT IN ':
                    in_expr = self._parse_in_expression(z3_left, right, specification)
                    return Not(in_expr) if in_expr is not None else None
                elif op == ' BETWEEN ':
                    return self._parse_between_expression(z3_left, right, specification)
                else:
                    # Regular comparison operator
                    z3_right = self._parse_operand(right, specification)
                    
                    if z3_right is None:
                        return None
                    
                    # Create comparison based on operator
                    if op == '=':
                        return z3_left == z3_right
                    elif op == '!=':
                        return z3_left != z3_right
                    elif op == '<':
                        return z3_left < z3_right
                    elif op == '<=':
                        return z3_left <= z3_right
                    elif op == '>':
                        return z3_left > z3_right
                    elif op == '>=':
                        return z3_left >= z3_right
        
        # Handle IS NULL and IS NOT NULL
        if ' IS NULL' in expression:
            field = expression.split(' IS NULL')[0].strip()
            z3_field = self._parse_operand(field, specification)
            
            if z3_field is None:
                return None
                
            # Create IS NULL condition (we'll represent NULL as a special value)
            if field in self.variables:
                var_type = self.variable_types.get(field, 'unknown')
                if var_type == 'numeric':
                    # For numeric, use a special value (e.g., -9999)
                    return z3_field == -9999
                elif var_type == 'string':
                    # For string, use a special string ID
                    return z3_field == -1
                elif var_type == 'boolean':
                    # For boolean, this doesn't make much sense, but we'll use a special case
                    return And(z3_field, Not(z3_field))  # This is a contradiction, representing NULL
            
            return None
            
        if ' IS NOT NULL' in expression:
            field = expression.split(' IS NOT NULL')[0].strip()
            z3_field = self._parse_operand(field, specification)
            
            if z3_field is None:
                return None
                
            # Create IS NOT NULL condition
            if field in self.variables:
                var_type = self.variable_types.get(field, 'unknown')
                if var_type == 'numeric':
                    return z3_field != -9999
                elif var_type == 'string':
                    return z3_field != -1
                elif var_type == 'boolean':
                    return Or(z3_field, Not(z3_field))  # This is a tautology, representing NOT NULL
            
            return None
        
        # Handle simple boolean field reference
        field_match = re.match(r'([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)', expression)
        if field_match:
            form_name, field_name = field_match.groups()
            field_key = f"{form_name}.{field_name}"
            
            # Check if field exists in specification
            field = specification.get_field(form_name, field_name)
            
            if field and field.type.value == 'boolean':
                # Create Z3 variable if it doesn't exist
                if field_key not in self.variables:
                    self.variables[field_key] = Bool(field_key)
                    self.variable_types[field_key] = 'boolean'
                
                return self.variables[field_key]
        
        # If we can't parse the expression, return None
        return None
    
    def _parse_operand(self, operand: str, specification: StudySpecification) -> Optional[z3.ExprRef]:
        """
        Parse an operand (left or right side of comparison) into Z3.
        
        Args:
            operand: The operand to parse
            specification: The study specification
            
        Returns:
            Z3 expression or None if parsing failed
        """
        # Check if operand is a field reference
        field_match = re.match(r'([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)', operand)
        if field_match:
            form_name, field_name = field_match.groups()
            field_key = f"{form_name}.{field_name}"
            
            # Check if field exists in specification
            field = specification.get_field(form_name, field_name)
            
            if not field:
                return None
            
            # Create Z3 variable if it doesn't exist
            if field_key not in self.variables:
                if field.type.value in ['number']:
                    self.variables[field_key] = Real(field_key)
                    self.variable_types[field_key] = 'numeric'
                elif field.type.value in ['date', 'datetime', 'time']:
                    # Represent dates as numeric (days since epoch)
                    self.variables[field_key] = Real(field_key)
                    self.variable_types[field_key] = 'date'
                elif field.type.value == 'boolean':
                    self.variables[field_key] = Bool(field_key)
                    self.variable_types[field_key] = 'boolean'
                else:
                    # For categorical or text, use integers with constraints
                    self.variables[field_key] = Int(field_key)
                    self.variable_types[field_key] = 'string'
            
            return self.variables[field_key]
        
        # Check if operand is a numeric literal
        if re.match(r'^-?\d+(\.\d+)?$', operand):
            return RealVal(float(operand))
        
        # Check if operand is a string literal
        if (operand.startswith('"') and operand.endswith('"')) or (operand.startswith("'") and operand.endswith("'")):
            # Remove quotes
            string_value = operand[1:-1]
            
            # Convert to a unique integer ID for Z3
            string_id = hash(string_value) % 10000
            return IntVal(string_id)
        
        # Check if operand is a date literal
        date_match = re.match(r'(\d{4})-(\d{2})-(\d{2})', operand)
        if date_match:
            year, month, day = map(int, date_match.groups())
            
            # Convert to days since epoch (simple approximation)
            days = (year - 1970) * 365 + (month - 1) * 30 + day
            return RealVal(days)
        
        # Check if operand is a boolean literal
        if operand.upper() in ['TRUE', 'FALSE']:
            return BoolVal(operand.upper() == 'TRUE')
        
        # If we can't parse the operand, return None
        return None
    
    def _parse_in_expression(self, z3_left: z3.ExprRef, right: str, specification: StudySpecification) -> Optional[z3.ExprRef]:
        """
        Parse an IN expression.
        
        Args:
            z3_left: Z3 expression for left side
            right: Right side string (list of values)
            specification: The study specification
            
        Returns:
            Z3 expression for IN condition
        """
        # Remove list brackets
        if right.startswith('[') and right.endswith(']'):
            right = right[1:-1]
        
        # Split values
        values = [v.strip() for v in right.split(',')]
        
        # Parse each value
        z3_values = []
        for value in values:
            z3_value = self._parse_operand(value, specification)
            if z3_value is not None:
                z3_values.append(z3_value)
        
        # Create OR conditions for each value
        if not z3_values:
            return None
            
        return Or(*[z3_left == value for value in z3_values])
    
    def _parse_between_expression(self, z3_left: z3.ExprRef, right: str, specification: StudySpecification) -> Optional[z3.ExprRef]:
        """
        Parse a BETWEEN expression.
        
        Args:
            z3_left: Z3 expression for left side
            right: Right side string (min and max values)
            specification: The study specification
            
        Returns:
            Z3 expression for BETWEEN condition
        """
        # Split into min and max values
        parts = right.split('AND')
        if len(parts) != 2:
            return None
            
        min_val = parts[0].strip()
        max_val = parts[1].strip()
        
        # Parse min and max values
        z3_min = self._parse_operand(min_val, specification)
        z3_max = self._parse_operand(max_val, specification)
        
        if z3_min is None or z3_max is None:
            return None
            
        # Create BETWEEN condition
        return And(z3_left >= z3_min, z3_left <= z3_max)
    
    def _extract_model_values(self, model):
        """
        Extract values from a Z3 model for reporting.
        
        Args:
            model: Z3 model
            
        Returns:
            Dictionary of variable values
        """
        values = {}
        
        for var in model:
            name = str(var)
            value = model[var]
            
            # Convert Z3 values to Python values
            if is_bool(value):
                values[name] = bool(value)
            elif is_int(value):
                values[name] = int(value.as_long())
            elif is_real(value):
                values[name] = float(value.as_decimal(10))
            else:
                values[name] = str(value)
        
        return values
    
    def _detect_redundancies(self, formula: z3.ExprRef) -> Optional[str]:
        """
        Detect redundancies in a Z3 formula.
        
        Args:
            formula: Z3 formula
            
        Returns:
            Description of redundancy or None
        """
        redundancies = []
        
        # This is a simplified approach to redundancy detection
        # In a full implementation, we would analyze the formula structure more deeply
        
        # Check for obvious redundancies in AND expressions
        if is_and(formula):
            children = formula.children()
            
            # Check for duplicate clauses
            seen_clauses = set()
            for child in children:
                child_str = str(child)
                if child_str in seen_clauses:
                    redundancies.append(f"Duplicate clause: {child_str}")
                seen_clauses.add(child_str)
            
            # Check for contradictions among children
            for i, child1 in enumerate(children):
                for child2 in children[i+1:]:
                    if str(child2) == str(Not(child1)):
                        redundancies.append(f"Contradictory clauses: {child1} AND NOT({child1})")
        
        # Check for obvious redundancies in OR expressions
        if is_or(formula):
            children = formula.children()
            
            # Check for duplicate clauses
            seen_clauses = set()
            for child in children:
                child_str = str(child)
                if child_str in seen_clauses:
                    redundancies.append(f"Duplicate clause: {child_str}")
                seen_clauses.add(child_str)
            
            # Check for tautologies among children
            for i, child1 in enumerate(children):
                for child2 in children[i+1:]:
                    if str(child2) == str(Not(child1)):
                        redundancies.append(f"Tautological clauses: {child1} OR NOT({child1})")
        
        return "; ".join(redundancies) if redundancies else None
    
    def _test_edge_cases(self, formula: z3.ExprRef, specification: StudySpecification) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        Test formula behavior on clinical edge cases.
        
        Args:
            formula: Z3 formula
            specification: Study specification
            
        Returns:
            List of (issue_type, message, details) tuples
        """
        issues = []
        
        # Test with all NULL values
        self.solver.push()
        
        # Add NULL constraints for all variables
        null_constraints = []
        for var_name, var in self.variables.items():
            var_type = self.variable_types.get(var_name, 'unknown')
            
            if var_type == 'numeric':
                null_constraints.append(var == -9999)
            elif var_type == 'string':
                null_constraints.append(var == -1)
            elif var_type == 'boolean':
                # Skip boolean variables for NULL test
                pass
        
        if null_constraints:
            self.solver.add(And(*null_constraints))
            self.solver.add(formula)
            
            null_check = self.solver.check()
            if null_check == sat:
                issues.append(
                    ('null_values_satisfy_rule',
                     "Rule is satisfied when all fields are NULL, which may not be intended",
                     {'null_test': 'all fields NULL'}
                    )
                )
        
        self.solver.pop()
        
        # Test with extreme values for numeric fields
        for var_name, var in self.variables.items():
            var_type = self.variable_types.get(var_name, 'unknown')
            
            if var_type == 'numeric':
                # Test with extremely large value
                self.solver.push()
                self.solver.add(var == 1e6)  # 1 million
                self.solver.add(formula)
                
                extreme_check = self.solver.check()
                if extreme_check == sat:
                    issues.append(
                        ('extreme_value_satisfies_rule',
                         f"Rule is satisfied with extreme value (1000000) for {var_name}, check if this is intended",
                         {'field': var_name, 'extreme_value': 1000000}
                        )
                    )
                
                self.solver.pop()
                
                # Test with extremely small value
                self.solver.push()
                self.solver.add(var == -1e6)  # -1 million
                self.solver.add(formula)
                
                extreme_check = self.solver.check()
                if extreme_check == sat:
                    issues.append(
                        ('extreme_value_satisfies_rule',
                         f"Rule is satisfied with extreme value (-1000000) for {var_name}, check if this is intended",
                         {'field': var_name, 'extreme_value': -1000000}
                        )
                    )
                
                self.solver.pop()
        
        return issues