"""
Dynamics and Derivatives Utility for Eclaire Trials Edit Check Rule Validation System.

This module provides functionality for handling dynamic calculations and derivatives
in clinical trial data, including:
- Time-based calculations (e.g., days between visits)
- Change from baseline calculations
- Rate of change calculations
- Derived variables (e.g., BMI from height and weight)
"""

import re
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta

class DynamicsProcessor:
    """Processor for dynamics and derivatives in clinical trial data."""
    
    def __init__(self):
        """Initialize the dynamics processor."""
        # Register standard dynamic functions
        self.dynamic_functions = {
            # Time-based functions
            "DAYS_BETWEEN": self._days_between,
            "MONTHS_BETWEEN": self._months_between,
            "YEARS_BETWEEN": self._years_between,
            
            # Change calculations
            "CHANGE_FROM_BASELINE": self._change_from_baseline,
            "PERCENT_CHANGE_FROM_BASELINE": self._percent_change_from_baseline,
            "CHANGE_FROM_PREVIOUS": self._change_from_previous,
            
            # Rate calculations
            "RATE_OF_CHANGE": self._rate_of_change,
            "SLOPE": self._slope,
            
            # Common derivatives
            "BMI": self._calculate_bmi,
            "BSA": self._calculate_bsa,
            "EGFR": self._calculate_egfr,
            
            # Statistical functions
            "MEAN": self._mean,
            "MEDIAN": self._median,
            "STD_DEV": self._std_dev,
            "MIN": self._min,
            "MAX": self._max,
            
            # Temporal patterns
            "IS_INCREASING": self._is_increasing,
            "IS_DECREASING": self._is_decreasing,
            "HAS_DOUBLED": self._has_doubled,
            "HAS_HALVED": self._has_halved
        }
    
    def extract_dynamics(self, condition: str) -> List[Dict[str, Any]]:
        """
        Extract dynamic function calls from a condition string.
        
        Args:
            condition: The rule condition string
            
        Returns:
            List of dictionaries with function name and parameters
        """
        dynamics = []
        
        # Pattern to match function calls: FUNCTION_NAME(param1, param2, ...)
        pattern = r'([A-Z_]+)\(([^)]*)\)'
        matches = re.findall(pattern, condition)
        
        for func_name, params_str in matches:
            if func_name in self.dynamic_functions:
                # Parse parameters
                params = [p.strip() for p in params_str.split(',')]
                
                dynamics.append({
                    'function': func_name,
                    'parameters': params,
                    'original': f"{func_name}({params_str})"
                })
        
        return dynamics
    
    def process_dynamics(self, dynamics: List[Dict[str, Any]], data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process dynamic calculations based on the provided data.
        
        Args:
            dynamics: List of dynamic function specifications
            data: Dictionary of data values
            
        Returns:
            Dictionary of calculated dynamic values
        """
        results = {}
        
        for dynamic in dynamics:
            func_name = dynamic['function']
            params = dynamic['parameters']
            original = dynamic['original']
            
            if func_name in self.dynamic_functions:
                try:
                    # Extract parameter values from data
                    param_values = []
                    for param in params:
                        if param in data:
                            param_values.append(data[param])
                        elif self._is_numeric(param):
                            param_values.append(float(param))
                        elif self._is_date(param):
                            param_values.append(self._parse_date(param))
                        else:
                            param_values.append(param)
                    
                    # Call the dynamic function
                    result = self.dynamic_functions[func_name](*param_values)
                    results[original] = result
                except Exception as e:
                    results[original] = f"ERROR: {str(e)}"
        
        return results
    
    def expand_derivatives(self, spec, rules):
        """
        Expand the specification to include derived fields based on rule conditions.
        
        Args:
            spec: StudySpecification object
            rules: List of EditCheckRule objects
            
        Returns:
            Updated StudySpecification with derived fields
        """
        from ..models.data_models import Form, Field, FieldType
        
        # Create a form for derived variables if it doesn't exist
        if "Derivatives" not in spec.forms:
            derivatives_form = Form(
                name="Derivatives",
                label="Derived Variables"
            )
            spec.add_form(derivatives_form)
        
        # Extract dynamics from all rules
        all_dynamics = []
        for rule in rules:
            dynamics = self.extract_dynamics(rule.condition)
            all_dynamics.extend(dynamics)
        
        # Add derived fields to the Derivatives form
        for dynamic in all_dynamics:
            field_name = dynamic['original'].replace('(', '_').replace(')', '').replace(',', '_').replace(' ', '')
            
            # Check if field already exists
            if not any(field.name == field_name for field in spec.forms["Derivatives"].fields):
                field_type = self._infer_dynamic_type(dynamic['function'])
                
                field = Field(
                    name=field_name,
                    type=field_type,
                    label=dynamic['original'],
                    required=False
                )
                
                spec.forms["Derivatives"].fields.append(field)
        
        return spec
    
    def _infer_dynamic_type(self, function_name: str) -> str:
        """Infer the field type based on the dynamic function."""
        from ..models.data_models import FieldType
        
        time_functions = ["DAYS_BETWEEN", "MONTHS_BETWEEN", "YEARS_BETWEEN"]
        numeric_functions = ["CHANGE_FROM_BASELINE", "PERCENT_CHANGE_FROM_BASELINE", 
                             "CHANGE_FROM_PREVIOUS", "RATE_OF_CHANGE", "SLOPE", 
                             "BMI", "BSA", "EGFR", "MEAN", "MEDIAN", "STD_DEV", "MIN", "MAX"]
        boolean_functions = ["IS_INCREASING", "IS_DECREASING", "HAS_DOUBLED", "HAS_HALVED"]
        
        if function_name in time_functions:
            return FieldType.NUMBER
        elif function_name in numeric_functions:
            return FieldType.NUMBER
        elif function_name in boolean_functions:
            return FieldType.BOOLEAN
        else:
            return FieldType.TEXT
    
    # Time-based functions
    def _days_between(self, date1, date2):
        """Calculate days between two dates."""
        date1 = self._ensure_date(date1)
        date2 = self._ensure_date(date2)
        return (date2 - date1).days
    
    def _months_between(self, date1, date2):
        """Calculate months between two dates."""
        date1 = self._ensure_date(date1)
        date2 = self._ensure_date(date2)
        return (date2.year - date1.year) * 12 + date2.month - date1.month
    
    def _years_between(self, date1, date2):
        """Calculate years between two dates."""
        date1 = self._ensure_date(date1)
        date2 = self._ensure_date(date2)
        return date2.year - date1.year - ((date2.month, date2.day) < (date1.month, date1.day))
    
    # Change calculations
    def _change_from_baseline(self, current_value, baseline_value):
        """Calculate absolute change from baseline."""
        return float(current_value) - float(baseline_value)
    
    def _percent_change_from_baseline(self, current_value, baseline_value):
        """Calculate percent change from baseline."""
        current = float(current_value)
        baseline = float(baseline_value)
        if baseline == 0:
            return float('inf') if current > 0 else float('-inf') if current < 0 else 0
        return ((current - baseline) / baseline) * 100
    
    def _change_from_previous(self, current_value, previous_value):
        """Calculate change from previous value."""
        return float(current_value) - float(previous_value)
    
    # Rate calculations
    def _rate_of_change(self, value1, value2, time1, time2):
        """Calculate rate of change over time."""
        value_change = float(value2) - float(value1)
        time_change = self._days_between(time1, time2)
        if time_change == 0:
            return 0
        return value_change / time_change
    
    def _slope(self, values, times):
        """Calculate slope of a trend line."""
        if isinstance(values, str):
            values = [float(v.strip()) for v in values.split(',')]
        if isinstance(times, str):
            times = [self._ensure_date(t.strip()) for t in times.split(',')]
            
        if len(values) != len(times):
            raise ValueError("Number of values and times must be equal")
            
        if len(values) < 2:
            return 0
            
        # Convert times to days from first time point
        days = [(t - times[0]).days for t in times]
        
        # Calculate slope using numpy if available
        try:
            return np.polyfit(days, values, 1)[0]
        except:
            # Simple slope calculation if numpy is not available
            n = len(values)
            sum_x = sum(days)
            sum_y = sum(values)
            sum_xy = sum(x*y for x, y in zip(days, values))
            sum_xx = sum(x*x for x in days)
            
            return (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
    
    # Common derivatives
    def _calculate_bmi(self, weight_kg, height_cm):
        """Calculate BMI from weight (kg) and height (cm)."""
        weight = float(weight_kg)
        height_m = float(height_cm) / 100
        return weight / (height_m * height_m)
    
    def _calculate_bsa(self, weight_kg, height_cm):
        """Calculate Body Surface Area using the Mosteller formula."""
        weight = float(weight_kg)
        height = float(height_cm)
        return ((height * weight) / 3600) ** 0.5
    
    def _calculate_egfr(self, creatinine, age, gender, is_african_american=False, weight=None):
        """Calculate eGFR using the MDRD formula."""
        creatinine = float(creatinine)
        age = float(age)
        gender_factor = 0.742 if gender.lower() in ['female', 'f'] else 1.0
        race_factor = 1.212 if is_african_american else 1.0
        
        return 175 * (creatinine ** -1.154) * (age ** -0.203) * gender_factor * race_factor
    
    # Statistical functions
    def _mean(self, values):
        """Calculate mean of values."""
        if isinstance(values, str):
            values = [float(v.strip()) for v in values.split(',')]
        return sum(values) / len(values)
    
    def _median(self, values):
        """Calculate median of values."""
        if isinstance(values, str):
            values = [float(v.strip()) for v in values.split(',')]
        sorted_values = sorted(values)
        n = len(sorted_values)
        mid = n // 2
        if n % 2 == 0:
            return (sorted_values[mid-1] + sorted_values[mid]) / 2
        else:
            return sorted_values[mid]
    
    def _std_dev(self, values):
        """Calculate standard deviation of values."""
        if isinstance(values, str):
            values = [float(v.strip()) for v in values.split(',')]
        mean = self._mean(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def _min(self, values):
        """Find minimum value."""
        if isinstance(values, str):
            values = [float(v.strip()) for v in values.split(',')]
        return min(values)
    
    def _max(self, values):
        """Find maximum value."""
        if isinstance(values, str):
            values = [float(v.strip()) for v in values.split(',')]
        return max(values)
    
    # Temporal patterns
    def _is_increasing(self, values):
        """Check if values are strictly increasing."""
        if isinstance(values, str):
            values = [float(v.strip()) for v in values.split(',')]
        return all(values[i] < values[i+1] for i in range(len(values)-1))
    
    def _is_decreasing(self, values):
        """Check if values are strictly decreasing."""
        if isinstance(values, str):
            values = [float(v.strip()) for v in values.split(',')]
        return all(values[i] > values[i+1] for i in range(len(values)-1))
    
    def _has_doubled(self, current_value, reference_value):
        """Check if value has doubled from reference."""
        return float(current_value) >= 2 * float(reference_value)
    
    def _has_halved(self, current_value, reference_value):
        """Check if value has halved from reference."""
        return float(current_value) <= 0.5 * float(reference_value)
    
    # Helper methods
    def _is_numeric(self, value):
        """Check if a string value is numeric."""
        if not isinstance(value, str):
            return isinstance(value, (int, float))
        try:
            float(value)
            return True
        except:
            return False
    
    def _is_date(self, value):
        """Check if a string value is a date."""
        if isinstance(value, datetime):
            return True
        if not isinstance(value, str):
            return False
        try:
            self._parse_date(value)
            return True
        except:
            return False
    
    def _parse_date(self, date_str):
        """Parse a date string into a datetime object."""
        if isinstance(date_str, datetime):
            return date_str
        
        # Try common date formats
        formats = [
            '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y',
            '%Y-%m-%d %H:%M:%S', '%d-%m-%Y %H:%M:%S', 
            '%m/%d/%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        
        raise ValueError(f"Could not parse date: {date_str}")
    
    def _ensure_date(self, date_val):
        """Ensure value is a datetime object."""
        if isinstance(date_val, datetime):
            return date_val
        if isinstance(date_val, str):
            return self._parse_date(date_val)
        raise ValueError(f"Could not convert to date: {date_val}")
