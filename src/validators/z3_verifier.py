"""
Z3 Verifier for the Edit Check Rule Validation System.

This module provides functionality to verify the logical consistency and completeness
of edit check rules using the Z3 theorem prover.
"""

import re
from typing import List, Dict, Any, Optional, Tuple, Set
from z3 import *

from ..models.data_models import EditCheckRule, StudySpecification, ValidationResult, FieldType
from ..utils.logger import Logger

logger = Logger(__name__)

class Z3Verifier:
    """Verify edit check rules using the Z3 theorem prover."""
    
    def __init__(self):
        """Initialize the Z3 verifier."""
        self.solver = Solver()
        self.variables = {}
        self.field_types = {}
    
    def verify_rules(self, rules: List[EditCheckRule], specification: StudySpecification) -> List[ValidationResult]:
        """
        Verify a list of rules for logical consistency and completeness.
        
        Args:
            rules: List of rules to verify
            specification: Study specification for context
            
        Returns:
            List of validation results
        """
        results = []
        
        # Reset solver and variables for a new verification session
        self.solver = Solver()
        self.variables = {}
        self.field_types = {}
        
        # Extract all form.field references from all rules
        all_form_fields = set()
        for rule in rules:
            form_fields = self._extract_form_fields(rule.formalized_condition or rule.condition)
            all_form_fields.update(form_fields)
        
        # Create Z3 variables for all form.field references
        for form_name, field_name in all_form_fields:
            field = specification.get_field(form_name, field_name)
            if field:
                var_name = f"{form_name}.{field_name}"
                self._create_z3_variable(var_name, field.type.value)
        
        # Verify each rule individually
        for rule in rules:
            result = self.verify_rule(rule, specification)
            results.append(result)
        
        # Verify rule set consistency
        self._verify_rule_set_consistency(rules, results)
        
        return results
    
    def verify_rule(self, rule: EditCheckRule, specification: StudySpecification) -> ValidationResult:
        """
        Verify a single rule for logical consistency.
        
        Args:
            rule: Rule to verify
            specification: Study specification for context
            
        Returns:
            Validation result
        """
        result = ValidationResult(rule_id=rule.id, is_valid=True)
        
        # Skip verification if rule doesn't have a formalized condition
        if not rule.formalized_condition and not rule.condition:
            result.add_error(
                'missing_condition',
                f"Rule {rule.id} is missing a condition for verification"
            )
            return result
        
        condition = rule.formalized_condition or rule.condition
        
        try:
            # Parse the rule condition into Z3 formula
            z3_formula = self._parse_condition_to_z3(condition, specification)
            
            if z3_formula is None:
                result.add_error(
                    'parsing_error',
                    f"Could not parse rule {rule.id} condition to Z3 formula",
                    {'condition': condition}
                )
                return result
            
            # Check if the rule is satisfiable (has at least one solution)
            self.solver.push()
            self.solver.add(z3_formula)
            sat_check = self.solver.check()
            self.solver.pop()
            
            if sat_check == unsat:
                result.add_error(
                    'unsatisfiable_rule',
                    f"Rule {rule.id} is unsatisfiable (always false)",
                    {'condition': condition}
                )
            
            # Check if the rule is a tautology (always true)
            self.solver.push()
            self.solver.add(Not(z3_formula))
            taut_check = self.solver.check()
            self.solver.pop()
            
            if taut_check == unsat:
                result.add_warning(
                    'tautology',
                    f"Rule {rule.id} is a tautology (always true)",
                    {'condition': condition}
                )
            
            # Check for logical redundancy (e.g., x > 5 AND x > 3)
            redundancy = self._check_for_redundancy(z3_formula)
            if redundancy:
                result.add_warning(
                    'redundant_condition',
                    f"Rule {rule.id} contains redundant conditions: {redundancy}",
                    {'condition': condition, 'redundancy': redundancy}
                )
            
            logger.info(f"Successfully verified rule {rule.id}")
            
        except Exception as e:
            result.add_error(
                'verification_error',
                f"Error verifying rule {rule.id}: {str(e)}",
                {'condition': condition, 'exception': str(e)}
            )
            logger.error(f"Error verifying rule {rule.id}: {str(e)}")
        
        return result
    
    def _verify_rule_set_consistency(self, rules: List[EditCheckRule], results: List[ValidationResult]) -> None:
        """
        Verify the consistency of the entire rule set.
        
        Args:
            rules: List of rules to verify
            results: List of validation results to update
        """
        # Check for contradictory rules
        for i, rule1 in enumerate(rules):
            if not rule1.formalized_condition and not rule1.condition:
                continue
                
            condition1 = rule1.formalized_condition or rule1.condition
            z3_formula1 = self._parse_condition_to_z3(condition1, None)
            
            if z3_formula1 is None:
                continue
            
            for j, rule2 in enumerate(rules[i+1:], i+1):
                if not rule2.formalized_condition and not rule2.condition:
                    continue
                    
                condition2 = rule2.formalized_condition or rule2.condition
                z3_formula2 = self._parse_condition_to_z3(condition2, None)
                
                if z3_formula2 is None:
                    continue
                
                # Check if rules are contradictory
                self.solver.push()
                self.solver.add(z3_formula1)
                self.solver.add(z3_formula2)
                contradiction_check = self.solver.check()
                self.solver.pop()
                
                if contradiction_check == unsat:
                    # Rules are contradictory
                    for result in results:
                        if result.rule_id == rule1.id or result.rule_id == rule2.id:
                            result.add_error(
                                'contradictory_rules',
                                f"Rules {rule1.id} and {rule2.id} are contradictory",
                                {'rule1': rule1.id, 'rule2': rule2.id}
                            )
                
                # Check if one rule implies the other
                self.solver.push()
                self.solver.add(z3_formula1)
                self.solver.add(Not(z3_formula2))
                implication_check1 = self.solver.check()
                self.solver.pop()
                
                if implication_check1 == unsat:
                    # rule1 implies rule2
                    for result in results:
                        if result.rule_id == rule2.id:
                            result.add_warning(
                                'implied_rule',
                                f"Rule {rule2.id} is implied by rule {rule1.id}",
                                {'implying_rule': rule1.id}
                            )
                
                self.solver.push()
                self.solver.add(z3_formula2)
                self.solver.add(Not(z3_formula1))
                implication_check2 = self.solver.check()
                self.solver.pop()
                
                if implication_check2 == unsat:
                    # rule2 implies rule1
                    for result in results:
                        if result.rule_id == rule1.id:
                            result.add_warning(
                                'implied_rule',
                                f"Rule {rule1.id} is implied by rule {rule2.id}",
                                {'implying_rule': rule2.id}
                            )
    
    def _create_z3_variable(self, var_name: str, field_type: str) -> None:
        """
        Create a Z3 variable for a form.field reference.
        
        Args:
            var_name: Variable name (form.field)
            field_type: Field type
        """
        if var_name in self.variables:
            return
        
        # Create variable based on field type
        if field_type in ['number', 'integer', 'float', 'double']:
            self.variables[var_name] = Real(var_name)
            self.field_types[var_name] = 'numeric'
        elif field_type in ['date', 'datetime', 'time']:
            # Represent dates as reals for simplicity
            self.variables[var_name] = Real(var_name)
            self.field_types[var_name] = 'date'
        elif field_type in ['boolean']:
            self.variables[var_name] = Bool(var_name)
            self.field_types[var_name] = 'boolean'
        else:
            # For categorical, text, etc., use string theory
            # But since Z3's string theory is limited, we'll use integers and constraints
            self.variables[var_name] = Int(var_name)
            self.field_types[var_name] = 'categorical'
    
    def _extract_form_fields(self, condition: str) -> Set[Tuple[str, str]]:
        """
        Extract form.field references from a rule condition.
        
        Args:
            condition: Rule condition
            
        Returns:
            Set of (form_name, field_name) tuples
        """
        if not condition:
            return set()
            
        # Pattern to match form.field references
        pattern = re.compile(r'([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)')
        matches = pattern.findall(condition)
        
        return set(matches)
    
    def _parse_condition_to_z3(self, condition: str, specification: Optional[StudySpecification]) -> Optional[z3.ExprRef]:
        """
        Parse a rule condition into a Z3 formula.
        
        Args:
            condition: Rule condition
            specification: Study specification for context
            
        Returns:
            Z3 formula or None if parsing failed
        """
        try:
            # Handle IF-THEN conditions
            if_then_match = re.search(r'IF\s+(.+?)\s+THEN\s+(.+?)\s+(MUST\s+BE|SHOULD\s+BE|MUST\s+NOT\s+BE|SHOULD\s+NOT\s+BE)\s+(.+)', condition, re.IGNORECASE)
            if if_then_match:
                if_part = if_then_match.group(1)
                then_field = if_then_match.group(2)
                operator = if_then_match.group(3)
                value = if_then_match.group(4)
                
                z3_if = self._parse_simple_condition(if_part)
                
                # Parse the THEN part based on the operator
                if operator.upper() in ['MUST BE', 'SHOULD BE']:
                    z3_then = self._parse_simple_condition(f"{then_field} = {value}")
                elif operator.upper() in ['MUST NOT BE', 'SHOULD NOT BE']:
                    z3_then = self._parse_simple_condition(f"{then_field} != {value}")
                else:
                    z3_then = self._parse_simple_condition(f"{then_field} {value}")
                
                if z3_if is not None and z3_then is not None:
                    return Implies(z3_if, z3_then)
                return None
            
            # Handle simple conditions and AND/OR combinations
            return self._parse_simple_condition(condition)
            
        except Exception as e:
            logger.error(f"Error parsing condition to Z3: {str(e)}")
            return None
    
    def _parse_simple_condition(self, condition: str) -> Optional[z3.ExprRef]:
        """
        Parse a simple condition into a Z3 formula.
        
        Args:
            condition: Simple condition
            
        Returns:
            Z3 formula or None if parsing failed
        """
        try:
            # Handle AND conditions
            if ' AND ' in condition:
                parts = condition.split(' AND ')
                z3_parts = [self._parse_simple_condition(part.strip()) for part in parts]
                return And(*[p for p in z3_parts if p is not None])
            
            # Handle OR conditions
            if ' OR ' in condition:
                parts = condition.split(' OR ')
                z3_parts = [self._parse_simple_condition(part.strip()) for part in parts]
                return Or(*[p for p in z3_parts if p is not None])
            
            # Handle NOT conditions
            if condition.strip().startswith('NOT '):
                part = condition.strip()[4:]
                z3_part = self._parse_simple_condition(part)
                return Not(z3_part) if z3_part is not None else None
            
            # Handle comparison conditions
            for op in ['<=', '>=', '!=', '=', '<', '>']:
                if op in condition:
                    left, right = condition.split(op, 1)
                    left = left.strip()
                    right = right.strip()
                    
                    # Check if left side is a form.field reference
                    form_field_match = re.match(r'([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)', left)
                    if form_field_match:
                        var_name = left
                        if var_name not in self.variables:
                            # If we don't have this variable, create it as a Real
                            self._create_z3_variable(var_name, 'number')
                        
                        var = self.variables[var_name]
                        var_type = self.field_types[var_name]
                        
                        # Parse right side based on variable type
                        if var_type == 'numeric':
                            try:
                                # Try to convert to float
                                right_val = float(right)
                                
                                # Create comparison
                                if op == '=':
                                    return var == right_val
                                elif op == '!=':
                                    return var != right_val
                                elif op == '<':
                                    return var < right_val
                                elif op == '<=':
                                    return var <= right_val
                                elif op == '>':
                                    return var > right_val
                                elif op == '>=':
                                    return var >= right_val
                            except ValueError:
                                # Not a number, might be another variable
                                if right in self.variables:
                                    right_var = self.variables[right]
                                    
                                    # Create comparison
                                    if op == '=':
                                        return var == right_var
                                    elif op == '!=':
                                        return var != right_var
                                    elif op == '<':
                                        return var < right_var
                                    elif op == '<=':
                                        return var <= right_var
                                    elif op == '>':
                                        return var > right_var
                                    elif op == '>=':
                                        return var >= right_var
                        
                        elif var_type in ['categorical', 'boolean']:
                            # For categorical variables, we compare with string literals
                            # Remove quotes if present
                            if right.startswith('"') and right.endswith('"'):
                                right = right[1:-1]
                            elif right.startswith("'") and right.endswith("'"):
                                right = right[1:-1]
                            
                            # Create a unique integer for this string value
                            right_val = hash(right) % 10000  # Simple hash to int
                            
                            # Create comparison
                            if op == '=':
                                return var == right_val
                            elif op == '!=':
                                return var != right_val
                            # Other comparisons don't make sense for categorical
            
            # If we couldn't parse the condition, return None
            return None
            
        except Exception as e:
            logger.error(f"Error parsing simple condition: {str(e)}")
            return None
    
    def _check_for_redundancy(self, formula: z3.ExprRef) -> Optional[str]:
        """
        Check for logical redundancy in a Z3 formula.
        
        Args:
            formula: Z3 formula to check
            
        Returns:
            Description of redundancy or None if no redundancy found
        """
        # This is a placeholder implementation
        # In a real system, we would analyze the formula structure
        return None
