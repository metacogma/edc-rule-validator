"""
Unified parser for study specifications and edit check rules.

This module provides a flexible parser that can handle both study specifications
and edit check rules with configurable column mappings.
"""

import os
import pandas as pd
from typing import Tuple, List, Dict, Optional, Union, Any

from ..models.data_models import StudySpecification, EditCheckRule, Form, Field
from ..utils.logger import Logger

logger = Logger(__name__)

class UnifiedParser:
    """Parse both study specifications and edit check rules with flexible mapping."""
    
    def __init__(self, custom_mappings: Optional[Dict[str, List[str]]] = None):
        """
        Initialize parser with flexible column mappings.
        
        Args:
            custom_mappings: Optional custom column mappings to extend the default mappings
        """
        # Default column mappings
        self.column_mappings = {
            # Rule file mappings
            'check_id': ['rule_id', 'id', 'check_number', 'rule_number'],
            'condition': ['check_condition', 'rule_condition', 'expression', 'rule_expression'],
            'message': ['error_message', 'warning_message', 'notification', 'rule_message'],
            'severity': ['error_type', 'warning_type', 'type', 'rule_type'],
            'forms': ['form', 'crf', 'form_name', 'crf_name'],
            'fields': ['field', 'variable', 'item', 'question', 'field_name'],
            
            # Specification file mappings
            'form_name': ['form', 'form_id', 'formname', 'crf', 'crf_name'],
            'form_label': ['form_description', 'form_title', 'crf_label', 'crf_title'],
            'field_name': ['field', 'field_id', 'fieldname', 'variable', 'item', 'question'],
            'field_type': ['type', 'data_type', 'datatype', 'variable_type'],
            'field_label': ['label', 'question_text', 'display_text', 'description'],
            'valid_values': ['values', 'allowed_values', 'code_list', 'valid_range'],
            'required': ['mandatory', 'is_required', 'is_mandatory'],
            'min_value': ['minimum', 'min', 'lower_bound'],
            'max_value': ['maximum', 'max', 'upper_bound']
        }
        
        # Add custom mappings if provided
        if custom_mappings:
            for key, values in custom_mappings.items():
                if key in self.column_mappings:
                    self.column_mappings[key].extend(values)
                else:
                    self.column_mappings[key] = values
    
    def parse_file(self, file_path: str, file_type: str) -> Tuple[Union[List[Dict], StudySpecification, None], List[Dict]]:
        """
        Parse Excel file based on type (specification or rules).
        
        Args:
            file_path: Path to the Excel file
            file_type: Type of file ('specification' or 'rules')
            
        Returns:
            Tuple containing:
            - Parsed data (list of rules, specification object, or None if error)
            - List of errors encountered during parsing
        """
        errors = []
        
        # Check if file exists
        if not os.path.exists(file_path):
            error = {
                'error_type': 'file_not_found',
                'message': f"File not found: {file_path}",
                'file': file_path
            }
            errors.append(error)
            logger.error(f"File not found: {file_path}")
            return None, errors
            
        try:
            # Parse based on file type
            if file_type.lower() == "specification":
                return self._parse_specification(file_path)
            elif file_type.lower() == "rules":
                return self._parse_rules(file_path)
            else:
                error = {
                    'error_type': 'invalid_file_type',
                    'message': f"Invalid file type: {file_type}. Must be 'specification' or 'rules'.",
                    'file': file_path
                }
                errors.append(error)
                logger.error(f"Invalid file type: {file_type}")
                return None, errors
        except Exception as e:
            error = {
                'error_type': 'parsing_error',
                'message': f"Error parsing file: {str(e)}",
                'file': file_path,
                'exception': str(e)
            }
            errors.append(error)
            logger.error(f"Error parsing file {file_path}: {str(e)}")
            return None, errors
    
    def _parse_specification(self, file_path: str) -> Tuple[Optional[StudySpecification], List[Dict]]:
        """
        Parse study specification file.
        
        Args:
            file_path: Path to the specification Excel file
            
        Returns:
            Tuple containing:
            - StudySpecification object or None if error
            - List of errors encountered during parsing
        """
        errors = []
        
        try:
            # Get available sheet names
            xls = pd.ExcelFile(file_path)
            sheet_names = xls.sheet_names
            
            # Try to identify form and field sheets
            forms_sheet = self._identify_sheet(sheet_names, ['forms', 'form', 'crf', 'crfs'])
            fields_sheet = self._identify_sheet(sheet_names, ['fields', 'field', 'variables', 'items', 'questions'])
            
            logger.info(f"Identified sheets - Forms: {forms_sheet}, Fields: {fields_sheet}")
            
            # Read forms sheet if available
            forms_df = pd.DataFrame()
            if forms_sheet:
                try:
                    forms_df = pd.read_excel(file_path, sheet_name=forms_sheet)
                    logger.info(f"Successfully read forms sheet with {len(forms_df)} rows")
                    
                    # Map columns using alternative names
                    forms_df = self._map_columns(forms_df, ['form_name', 'form_label'])
                    
                except Exception as e:
                    error = {
                        'error_type': 'forms_sheet_error',
                        'message': f"Error reading forms sheet: {str(e)}",
                        'sheet': forms_sheet,
                        'exception': str(e)
                    }
                    errors.append(error)
                    logger.error(f"Error reading forms sheet: {str(e)}")
            
            # Read fields sheet
            if not fields_sheet:
                error = {
                    'error_type': 'missing_fields_sheet',
                    'message': "Fields sheet not found in study spec file",
                    'available_sheets': sheet_names,
                    'file': file_path
                }
                errors.append(error)
                logger.error(f"Fields sheet not found in study spec file. Available sheets: {sheet_names}")
                return None, errors
                
            try:
                fields_df = pd.read_excel(file_path, sheet_name=fields_sheet)
                logger.info(f"Successfully read fields sheet with {len(fields_df)} rows")
                
                # Map columns using alternative names
                required_field_cols = ['form_name', 'field_name', 'field_type']
                fields_df = self._map_columns(fields_df, required_field_cols)
                
                # Check if we still have missing columns
                missing_cols = [col for col in required_field_cols if col not in fields_df.columns]
                if missing_cols:
                    error = {
                        'error_type': 'missing_field_columns',
                        'message': f"Required field columns missing: {missing_cols}",
                        'available_columns': list(fields_df.columns),
                        'sheet': fields_sheet
                    }
                    errors.append(error)
                    logger.error(f"Missing field columns: {missing_cols}")
                    return None, errors
                
                # Map optional columns
                optional_field_cols = ['field_label', 'valid_values', 'required', 'min_value', 'max_value']
                fields_df = self._map_columns(fields_df, optional_field_cols)
                
                # Create study specification
                spec = StudySpecification.from_dataframes(forms_df, fields_df)
                
                # Validate we have some forms and fields
                if not spec.forms:
                    error = {
                        'error_type': 'empty_specification',
                        'message': "Study specification contains no form fields",
                        'file': file_path
                    }
                    errors.append(error)
                    logger.error("Study specification contains no form fields")
                    return None, errors
                
                return spec, errors
                
            except Exception as e:
                error = {
                    'error_type': 'fields_sheet_error',
                    'message': f"Error reading fields sheet: {str(e)}",
                    'sheet': fields_sheet,
                    'exception': str(e)
                }
                errors.append(error)
                logger.error(f"Error reading fields sheet: {str(e)}")
                return None, errors
                
        except Exception as e:
            error = {
                'error_type': 'file_processing',
                'message': f"Error processing study spec file: {str(e)}",
                'file': file_path,
                'exception': str(e)
            }
            errors.append(error)
            logger.error(f"Error processing study spec file: {str(e)}")
            return None, errors
    
    def _parse_rules(self, file_path: str) -> Tuple[List[EditCheckRule], List[Dict]]:
        """
        Parse edit check rules file.
        
        Args:
            file_path: Path to the rules Excel file
            
        Returns:
            Tuple containing:
            - List of EditCheckRule objects
            - List of errors encountered during parsing
        """
        rules = []
        errors = []
        
        try:
            # Try to identify the rules sheet
            xls = pd.ExcelFile(file_path)
            sheet_names = xls.sheet_names
            
            rules_sheet = self._identify_sheet(
                sheet_names, 
                ['rules', 'edit checks', 'edit_checks', 'checks', 'validations']
            )
            
            if not rules_sheet:
                # If no specific sheet is identified, use the first sheet
                rules_sheet = sheet_names[0]
                logger.info(f"No specific rules sheet identified, using first sheet: {rules_sheet}")
            else:
                logger.info(f"Identified rules sheet: {rules_sheet}")
            
            # Read the rules sheet
            df = pd.read_excel(file_path, sheet_name=rules_sheet)
            
            # Validate required columns
            required_columns = ['check_id', 'condition']
            
            # Try to map columns if exact names not found
            df = self._map_columns(df, required_columns)
            
            # Check if we have all required columns
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                error = {
                    'error_type': 'missing_columns',
                    'message': f"Required columns missing: {missing_columns}",
                    'file': file_path,
                    'available_columns': list(df.columns)
                }
                errors.append(error)
                logger.error(f"Missing columns in rule file: {missing_columns}")
                return [], errors
            
            # Map optional columns
            optional_columns = ['message', 'severity', 'forms', 'fields']
            df = self._map_columns(df, optional_columns)
            
            # Process each row with validation
            for idx, row in df.iterrows():
                try:
                    rule_data = {
                        'id': str(row['check_id']),
                        'condition': str(row['condition'])
                    }
                    
                    # Add optional fields if present
                    for col in optional_columns:
                        if col in df.columns and not pd.isna(row[col]):
                            rule_data[col] = row[col]
                    
                    # Extract forms and fields from the condition if not explicitly provided
                    if 'forms' not in rule_data or not rule_data['forms']:
                        rule_data['forms'] = self._extract_forms_from_condition(rule_data['condition'])
                    
                    if 'fields' not in rule_data or not rule_data['fields']:
                        rule_data['fields'] = self._extract_fields_from_condition(rule_data['condition'])
                    
                    # Convert forms and fields to lists if they're strings
                    for field in ['forms', 'fields']:
                        if field in rule_data and isinstance(rule_data[field], str):
                            rule_data[field] = [item.strip() for item in rule_data[field].split(',')]
                    
                    # Create the rule object
                    rule = EditCheckRule.from_dict(rule_data)
                    rules.append(rule)
                    
                except Exception as e:
                    error = {
                        'error_type': 'row_processing',
                        'message': f"Error processing row {idx}: {str(e)}",
                        'row': idx,
                        'exception': str(e)
                    }
                    errors.append(error)
                    logger.error(f"Error processing row {idx}: {str(e)}")
            
            # Log success
            logger.info(f"Successfully parsed {len(rules)} rules from {file_path}")
            
            return rules, errors
            
        except Exception as e:
            error = {
                'error_type': 'file_processing',
                'message': f"Error processing file: {str(e)}",
                'file': file_path,
                'exception': str(e)
            }
            errors.append(error)
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return [], errors
    
    def _identify_sheet(self, sheet_names: List[str], patterns: List[str]) -> Optional[str]:
        """
        Identify a sheet based on name patterns.
        
        Args:
            sheet_names: List of sheet names
            patterns: List of patterns to match
            
        Returns:
            Matched sheet name or None if no match
        """
        # Try exact matches first
        for pattern in patterns:
            pattern_capitalized = pattern.capitalize()
            if pattern_capitalized in sheet_names:
                return pattern_capitalized
        
        # Try case-insensitive partial matches
        for sheet in sheet_names:
            for pattern in patterns:
                if pattern.lower() in sheet.lower():
                    return sheet
        
        return None
    
    def _map_columns(self, df: pd.DataFrame, required_columns: List[str]) -> pd.DataFrame:
        """
        Map DataFrame columns using alternative names.
        
        Args:
            df: DataFrame to map columns for
            required_columns: List of required column names
            
        Returns:
            DataFrame with mapped columns
        """
        column_mapping = {}
        
        for req_col in required_columns:
            if req_col in df.columns:
                continue
                
            # Try alternative names
            for alt_col in self.column_mappings.get(req_col, []):
                if alt_col in df.columns:
                    column_mapping[alt_col] = req_col
                    break
        
        # Apply column mapping if needed
        if column_mapping:
            df = df.rename(columns=column_mapping)
            
        return df
    
    def _extract_forms_from_condition(self, condition: str) -> List[str]:
        """
        Extract form names from a rule condition.
        This is a simple heuristic and may need to be enhanced with LLM assistance.
        
        Args:
            condition: Rule condition text
            
        Returns:
            List of form names
        """
        # This is a placeholder implementation
        # In a real system, we would use more sophisticated NLP or pattern matching
        return []
    
    def _extract_fields_from_condition(self, condition: str) -> List[str]:
        """
        Extract field names from a rule condition.
        This is a simple heuristic and may need to be enhanced with LLM assistance.
        
        Args:
            condition: Rule condition text
            
        Returns:
            List of field names
        """
        # This is a placeholder implementation
        # In a real system, we would use more sophisticated NLP or pattern matching
        return []
