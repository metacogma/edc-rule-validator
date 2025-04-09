"""
Rule Parser for the Edit Check Rule Validation System.

This module provides functionality to parse rules from Excel files.
"""

import pandas as pd
from typing import List, Dict, Any
from ..models.data_models import EditCheckRule
from ..utils.logger import Logger

logger = Logger(__name__)

class RuleParser:
    """Parse rules from Excel files."""
    
    def parse(self, file_path: str) -> List[EditCheckRule]:
        """
        Parse rules from an Excel file.
        
        Args:
            file_path: Path to the Excel file containing rules
            
        Returns:
            List of parsed rules
        """
        logger.info(f"Parsing rules from Excel file: {file_path}")
        
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Parse rules
            rules = []
            for _, row in df.iterrows():
                rule = self._parse_rule(row)
                if rule:
                    rules.append(rule)
            
            logger.info(f"Successfully parsed {len(rules)} rules from Excel file")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing rules from Excel file: {str(e)}")
            raise
    
    def _parse_rule(self, row: pd.Series) -> EditCheckRule:
        """
        Parse a single rule from an Excel row.
        
        Args:
            row: DataFrame row containing rule data
            
        Returns:
            Parsed rule or None if row is invalid
        """
        try:
            # Extract required fields
            rule_id = str(row.get('RuleID', ''))
            condition = str(row.get('Condition', ''))
            
            # Skip empty rows
            if not rule_id or not condition:
                return None
            
            # Create rule object
            rule = EditCheckRule(
                id=rule_id,
                condition=condition
            )
            
            # Add optional attributes if present in the Excel
            if 'Description' in row:
                setattr(rule, 'description', str(row['Description']))
            else:
                # Use condition as description if not provided
                setattr(rule, 'description', condition)
            
            if 'Forms' in row and pd.notna(row['Forms']):
                forms = str(row['Forms']).split(',')
                forms = [form.strip() for form in forms]
                setattr(rule, 'forms', forms)
            
            if 'Fields' in row and pd.notna(row['Fields']):
                fields = str(row['Fields']).split(',')
                fields = [field.strip() for field in fields]
                setattr(rule, 'fields', fields)
            
            if 'Severity' in row and pd.notna(row['Severity']):
                setattr(rule, 'severity', str(row['Severity']))
            
            return rule
            
        except Exception as e:
            logger.error(f"Error parsing rule row: {str(e)}")
            return None
