#!/usr/bin/env python
"""
Display all rows in the Excel files for the Edit Check Rule Validation System.
"""

import pandas as pd
import os

def display_excel_file(file_path, title):
    """Display all rows in an Excel file."""
    print("\n" + "=" * 80)
    print(f"{title} - {os.path.basename(file_path)}")
    print("=" * 80)
    
    try:
        # For multi-sheet Excel files
        excel_file = pd.ExcelFile(file_path)
        
        # Display total sheets
        print(f"Total sheets: {len(excel_file.sheet_names)}")
        
        # Process each sheet
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            print(f"\nSHEET: {sheet_name}")
            print(f"Total rows: {len(df)}")
            print(f"Columns: {df.columns.tolist()}")
            
            # Display all rows
            for i, row in df.iterrows():
                print(f"\nROW {i+1}:")
                for col in df.columns:
                    print(f"  {col}: {row[col]}")
    
    except Exception as e:
        print(f"Error reading Excel file: {str(e)}")

# Display rules file
display_excel_file("tests/data/sample_rules.xlsx", "RULES FILE")

# Display specification file
display_excel_file("tests/data/sample_specification.xlsx", "SPECIFICATION FILE")

print("\n" + "=" * 80)
print("END OF DATA DISPLAY")
print("=" * 80)
