"""
JSON Rule Parser for the Edit Check Rule Validation System.

This module provides functionality to parse rules from JSON files.
"""

import json
from typing import List, Dict, Any
from ..models.data_models import EditCheckRule
from ..utils.logger import Logger

logger = Logger(__name__)

class JSONRuleParser:
    """Parse rules from JSON files."""
    
    def parse(self, file_path: str) -> List[EditCheckRule]:
        """
        Parse rules from a JSON file.
        
        Args:
            file_path: Path to the JSON file containing rules
            
        Returns:
            List of parsed rules
        """
        logger.info(f"Parsing rules from JSON file: {file_path}")
        
        try:
            # Read JSON file
            with open(file_path, 'r') as f:
                rules_data = json.load(f)
            
            # Parse rules
            rules = []
            for rule_data in rules_data:
                rule = self._parse_rule(rule_data)
                rules.append(rule)
            
            logger.info(f"Successfully parsed {len(rules)} rules from JSON file")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing rules from JSON file: {str(e)}")
            raise
    
    def _parse_rule(self, rule_data: Dict[str, Any]) -> EditCheckRule:
        """
        Parse a single rule from JSON data.
        
        Args:
            rule_data: Dictionary containing rule data
            
        Returns:
            Parsed rule
        """
        # Create rule object
        rule = EditCheckRule(
            id=rule_data.get('id', ''),
            condition=rule_data.get('condition', '')
        )
        
        # Add optional attributes
        if 'forms' in rule_data:
            setattr(rule, 'forms', rule_data['forms'])
        
        if 'fields' in rule_data:
            setattr(rule, 'fields', rule_data['fields'])
        
        if 'severity' in rule_data:
            setattr(rule, 'severity', rule_data['severity'])
        
        if 'description' in rule_data:
            setattr(rule, 'description', rule_data['description'])
        else:
            # Use condition as description if not provided
            setattr(rule, 'description', rule_data.get('condition', ''))
        
        return rule
