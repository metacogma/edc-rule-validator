"""
HTML Report Generator for Eclaire Trials Edit Check Rule Validation System.

This module provides functionality to generate HTML reports with Eclaire Trials branding.
"""

import os
import json
from typing import Dict, Any, List
from datetime import datetime


def generate_html_report(data: Dict[str, Any], output_file: str) -> None:
    """
    Generate an HTML report with Eclaire Trials branding.
    
    Args:
        data: Dictionary containing report data
        output_file: Path to save the HTML report
    """
    # Extract branding colors
    branding = data.get('branding', {})
    primary_color = branding.get('primary_color', '#0074D9')  # Blue
    secondary_color = branding.get('secondary_color', '#FF9500')  # Orange
    accent_color = branding.get('accent_color', '#7F4FBF')  # Purple
    
    # Extract summary data
    summary = data.get('summary', {})
    total_rules = summary.get('total_rules', 0)
    valid_rules = summary.get('valid_rules', 0)
    invalid_rules = summary.get('invalid_rules', 0)
    dynamics_count = summary.get('dynamics_count', 0)
    test_cases_count = summary.get('test_cases_count', 0)
    
    # Calculate percentages for progress bars
    valid_percent = (valid_rules / total_rules * 100) if total_rules > 0 else 0
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data.get('title', 'Eclaire Trials Report')}</title>
    <style>
        :root {{
            --primary-color: {primary_color};
            --secondary-color: {secondary_color};
            --accent-color: {accent_color};
            --light-bg: #f8f9fa;
            --dark-text: #343a40;
            --light-text: #f8f9fa;
            --border-radius: 8px;
            --box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: var(--dark-text);
            background-color: var(--light-bg);
            margin: 0;
            padding: 0;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            background-color: var(--primary-color);
            color: var(--light-text);
            padding: 20px;
            border-radius: var(--border-radius);
            margin-bottom: 20px;
            box-shadow: var(--box-shadow);
        }}
        
        h1, h2, h3, h4 {{
            margin-top: 0;
        }}
        
        .card {{
            background-color: white;
            border-radius: var(--border-radius);
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: var(--box-shadow);
        }}
        
        .summary-stats {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 20px;
        }}
        
        .stat-card {{
            flex: 1;
            min-width: 200px;
            background-color: white;
            border-radius: var(--border-radius);
            padding: 20px;
            box-shadow: var(--box-shadow);
            text-align: center;
        }}
        
        .stat-card.primary {{
            border-top: 4px solid var(--primary-color);
        }}
        
        .stat-card.secondary {{
            border-top: 4px solid var(--secondary-color);
        }}
        
        .stat-card.accent {{
            border-top: 4px solid var(--accent-color);
        }}
        
        .stat-value {{
            font-size: 2.5rem;
            font-weight: bold;
            margin: 10px 0;
        }}
        
        .progress-container {{
            background-color: #e9ecef;
            border-radius: 4px;
            height: 8px;
            margin: 15px 0;
        }}
        
        .progress-bar {{
            height: 100%;
            border-radius: 4px;
            background-color: var(--primary-color);
        }}
        
        .rule-card {{
            border-left: 4px solid var(--primary-color);
            margin-bottom: 15px;
        }}
        
        .rule-card.invalid {{
            border-left-color: var(--secondary-color);
        }}
        
        .rule-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 15px;
            background-color: rgba(0, 0, 0, 0.03);
            cursor: pointer;
        }}
        
        .rule-content {{
            padding: 15px;
            display: none;
        }}
        
        .rule-content.active {{
            display: block;
        }}
        
        .badge {{
            display: inline-block;
            padding: 5px 10px;
            border-radius: 50px;
            font-size: 0.8rem;
            font-weight: bold;
        }}
        
        .badge-success {{
            background-color: #28a745;
            color: white;
        }}
        
        .badge-danger {{
            background-color: #dc3545;
            color: white;
        }}
        
        .badge-warning {{
            background-color: var(--secondary-color);
            color: white;
        }}
        
        .badge-info {{
            background-color: var(--accent-color);
            color: white;
        }}
        
        .error-list, .warning-list {{
            padding-left: 20px;
            color: #dc3545;
        }}
        
        .warning-list {{
            color: var(--secondary-color);
        }}
        
        .test-case {{
            background-color: rgba(0, 0, 0, 0.02);
            border-radius: var(--border-radius);
            padding: 15px;
            margin-top: 10px;
        }}
        
        .test-case h4 {{
            margin-top: 0;
            color: var(--accent-color);
        }}
        
        .dynamics-section {{
            margin-top: 30px;
        }}
        
        .dynamic-function {{
            background-color: rgba(127, 79, 191, 0.1);
            border-radius: var(--border-radius);
            padding: 15px;
            margin-bottom: 10px;
        }}
        
        footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #6c757d;
            font-size: 0.9rem;
        }}
        
        pre {{
            background-color: #f8f9fa;
            border-radius: 4px;
            padding: 10px;
            overflow-x: auto;
        }}
        
        .toggle-icon {{
            transition: transform 0.3s;
        }}
        
        .toggle-icon.active {{
            transform: rotate(180deg);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{data.get('title', 'Eclaire Trials Report')}</h1>
            <p>Generated on {data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}</p>
        </header>
        
        <div class="card">
            <h2>Summary</h2>
            <div class="summary-stats">
                <div class="stat-card primary">
                    <h3>Rules</h3>
                    <div class="stat-value">{total_rules}</div>
                    <div class="progress-container">
                        <div class="progress-bar" style="width: {valid_percent}%;"></div>
                    </div>
                    <p>{valid_rules} valid ({valid_percent:.1f}%)</p>
                </div>
                
                <div class="stat-card secondary">
                    <h3>Dynamic Functions</h3>
                    <div class="stat-value">{dynamics_count}</div>
                    <p>Across all rules</p>
                </div>
                
                <div class="stat-card accent">
                    <h3>Test Cases</h3>
                    <div class="stat-value">{test_cases_count}</div>
                    <p>Generated for validation</p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Rules</h2>
"""
    
    # Add each rule
    for rule in data.get('rules', []):
        rule_id = rule.get('id', 'Unknown')
        is_valid = rule.get('is_valid', False)
        errors = rule.get('errors', [])
        warnings = rule.get('warnings', [])
        test_cases = rule.get('test_cases', [])
        
        html += f"""
            <div class="rule-card {'invalid' if not is_valid else ''}">
                <div class="rule-header" onclick="toggleRule('{rule_id}')">
                    <h3>{rule_id}: {rule.get('description', 'No description')}</h3>
                    <div>
                        <span class="badge {'badge-success' if is_valid else 'badge-danger'}">{
                            'Valid' if is_valid else 'Invalid'}</span>
                        {f'<span class="badge badge-warning">{len(errors)} Errors</span>' if errors else ''}
                        {f'<span class="badge badge-info">{len(test_cases)} Tests</span>' if test_cases else ''}
                        <span class="toggle-icon">▼</span>
                    </div>
                </div>
                <div id="rule-{rule_id}" class="rule-content">
                    <p><strong>Condition:</strong> {rule.get('condition', 'No condition')}</p>
                    
                    {f'<h4>Errors ({len(errors)})</h4><ul class="error-list">' + ''.join([f'<li>{error}</li>' for error in errors]) + '</ul>' if errors else ''}
                    
                    {f'<h4>Warnings ({len(warnings)})</h4><ul class="warning-list">' + ''.join([f'<li>{warning}</li>' for warning in warnings]) + '</ul>' if warnings else ''}
                    
                    {f'<h4>Test Cases ({len(test_cases)})</h4>' if test_cases else ''}
"""
        
        # Add test cases for this rule
        for i, test in enumerate(test_cases):
            technique = test.get('technique', 'unknown')
            description = test.get('description', 'No description')
            test_data = test.get('test_data', {})
            expected_result = test.get('expected_result', 'Unknown')
            
            html += f"""
                    <div class="test-case">
                        <h4>Test {i+1}: {technique.capitalize()}</h4>
                        <p>{description}</p>
                        <p><strong>Test Data:</strong></p>
                        <pre>{json.dumps(test_data, indent=2)}</pre>
                        <p><strong>Expected Result:</strong> {expected_result}</p>
                    </div>
"""
        
        html += """
                </div>
            </div>
"""
    
    html += """
        </div>
"""
    
    # Add dynamics section if there are dynamics
    dynamics = data.get('dynamics', [])
    if dynamics:
        html += f"""
        <div class="card dynamics-section">
            <h2>Dynamic Functions ({len(dynamics)})</h2>
"""
        
        for dynamic in dynamics:
            function_name = dynamic.get('function', 'Unknown')
            expression = dynamic.get('expression', 'Unknown')
            
            html += f"""
            <div class="dynamic-function">
                <h3>{function_name}</h3>
                <p><strong>Expression:</strong> {expression}</p>
            </div>
"""
        
        html += """
        </div>
"""
    
    # Close the HTML
    html += """
        <footer>
            <p>Eclaire Trials Edit Check Rule Validation System</p>
            <p>© 2025 Eclaire Trials. All rights reserved.</p>
        </footer>
    </div>
    
    <script>
        function toggleRule(ruleId) {
            const content = document.getElementById(`rule-${ruleId}`);
            const header = content.previousElementSibling;
            const icon = header.querySelector('.toggle-icon');
            
            content.classList.toggle('active');
            icon.classList.toggle('active');
        }
    </script>
</body>
</html>
"""
    
    # Write to file
    with open(output_file, 'w') as f:
        f.write(html)
