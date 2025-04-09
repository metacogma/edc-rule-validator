"""
Web interface for the Edit Check Rule Validation System.

This module provides a Flask-based web interface for uploading files,
running validations, and viewing results.
"""

import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from ..workflow.workflow_orchestrator import WorkflowOrchestrator
from ..utils.logger import Logger

logger = Logger(__name__)

# Initialize Flask app
app = Flask(__name__, 
            static_folder='../web/static',
            template_folder='../web/templates')
CORS(app)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'uploads')
RESULTS_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'results')
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# In-memory storage for validation jobs
validation_jobs = {}

def allowed_file(filename):
    """Check if file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Handle file uploads."""
    # Check if both files are present
    if 'rules' not in request.files or 'spec' not in request.files:
        return jsonify({'error': 'Both rules and specification files are required'}), 400
    
    rules_file = request.files['rules']
    spec_file = request.files['spec']
    
    # Check if files are valid
    if rules_file.filename == '' or spec_file.filename == '':
        return jsonify({'error': 'No selected files'}), 400
    
    if not allowed_file(rules_file.filename) or not allowed_file(spec_file.filename):
        return jsonify({'error': 'Invalid file format. Only Excel files (.xlsx, .xls) are allowed'}), 400
    
    # Generate job ID and create directories
    job_id = str(uuid.uuid4())
    job_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
    job_results_dir = os.path.join(app.config['RESULTS_FOLDER'], job_id)
    
    os.makedirs(job_upload_dir, exist_ok=True)
    os.makedirs(job_results_dir, exist_ok=True)
    
    # Save files
    rules_filename = secure_filename(rules_file.filename)
    spec_filename = secure_filename(spec_file.filename)
    
    rules_path = os.path.join(job_upload_dir, rules_filename)
    spec_path = os.path.join(job_upload_dir, spec_filename)
    
    rules_file.save(rules_path)
    spec_file.save(spec_path)
    
    # Get configuration
    config = {
        "formalize_rules": request.form.get('formalize_rules', 'true').lower() == 'true',
        "verify_with_z3": request.form.get('verify_with_z3', 'true').lower() == 'true',
        "generate_tests": request.form.get('generate_tests', 'true').lower() == 'true',
        "test_cases_per_rule": int(request.form.get('test_cases_per_rule', '3'))
    }
    
    # Store job information
    validation_jobs[job_id] = {
        'id': job_id,
        'rules_file': rules_path,
        'spec_file': spec_path,
        'config': config,
        'status': 'uploaded',
        'created_at': datetime.now().isoformat(),
        'results_dir': job_results_dir
    }
    
    logger.info(f"Files uploaded for job {job_id}")
    
    return jsonify({
        'job_id': job_id,
        'status': 'uploaded',
        'message': 'Files uploaded successfully'
    })

@app.route('/api/validate/<job_id>', methods=['POST'])
def validate(job_id):
    """Run validation for a job."""
    if job_id not in validation_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = validation_jobs[job_id]
    
    # Update job status
    job['status'] = 'running'
    job['started_at'] = datetime.now().isoformat()
    
    try:
        # Initialize the workflow orchestrator
        orchestrator = WorkflowOrchestrator(job['config'])
        
        # Run the validation workflow
        logger.info(f"Starting validation workflow for job {job_id}")
        state = orchestrator.run(job['rules_file'], job['spec_file'])
        
        # Save results
        save_results(state, job['results_dir'])
        
        # Update job status
        job['status'] = state.status
        job['completed_at'] = datetime.now().isoformat()
        job['summary'] = {
            'total_rules': len(state.rules),
            'valid_rules': sum(1 for r in state.validation_results if r.is_valid),
            'rules_with_errors': sum(1 for r in state.validation_results if not r.is_valid),
            'rules_with_warnings': sum(1 for r in state.validation_results if r.warnings),
            'total_test_cases': len(state.test_cases)
        }
        
        logger.info(f"Validation completed for job {job_id} with status {state.status}")
        
        return jsonify({
            'job_id': job_id,
            'status': state.status,
            'summary': job['summary']
        })
        
    except Exception as e:
        # Update job status
        job['status'] = 'failed'
        job['completed_at'] = datetime.now().isoformat()
        job['error'] = str(e)
        
        logger.error(f"Validation failed for job {job_id}: {str(e)}")
        
        return jsonify({
            'job_id': job_id,
            'status': 'failed',
            'error': str(e)
        }), 500

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all validation jobs."""
    jobs_list = []
    
    for job_id, job in validation_jobs.items():
        jobs_list.append({
            'id': job_id,
            'status': job['status'],
            'created_at': job['created_at'],
            'started_at': job.get('started_at'),
            'completed_at': job.get('completed_at'),
            'summary': job.get('summary')
        })
    
    # Sort by created_at (newest first)
    jobs_list.sort(key=lambda x: x['created_at'], reverse=True)
    
    return jsonify(jobs_list)

@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    """Get information about a specific job."""
    if job_id not in validation_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = validation_jobs[job_id]
    
    return jsonify({
        'id': job_id,
        'status': job['status'],
        'created_at': job['created_at'],
        'started_at': job.get('started_at'),
        'completed_at': job.get('completed_at'),
        'summary': job.get('summary'),
        'error': job.get('error')
    })

@app.route('/api/results/<job_id>/<result_type>', methods=['GET'])
def get_results(job_id, result_type):
    """Get validation results for a job."""
    if job_id not in validation_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = validation_jobs[job_id]
    
    if job['status'] not in ['completed', 'completed_with_warnings', 'failed']:
        return jsonify({'error': 'Results not available yet'}), 400
    
    result_file = f"{result_type}.json"
    result_path = os.path.join(job['results_dir'], result_file)
    
    if not os.path.exists(result_path):
        return jsonify({'error': f'Result type {result_type} not found'}), 404
    
    try:
        with open(result_path, 'r') as f:
            results = json.load(f)
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': f'Error reading results: {str(e)}'}), 500

def save_results(state, output_dir: str) -> None:
    """
    Save validation results to files.
    
    Args:
        state: Workflow state with results
        output_dir: Output directory
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Save validation results
    validation_results = []
    for result in state.validation_results:
        validation_results.append({
            "rule_id": result.rule_id,
            "is_valid": result.is_valid,
            "errors": result.errors,
            "warnings": result.warnings
        })
    
    with open(os.path.join(output_dir, "validation_results.json"), 'w') as f:
        json.dump(validation_results, f, indent=2)
    
    # Save test cases
    test_cases = []
    for test_case in state.test_cases:
        test_cases.append({
            "rule_id": test_case.rule_id,
            "description": test_case.description,
            "expected_result": test_case.expected_result,
            "test_data": test_case.test_data,
            "is_positive": test_case.is_positive
        })
    
    with open(os.path.join(output_dir, "test_cases.json"), 'w') as f:
        json.dump(test_cases, f, indent=2)
    
    # Save formalized rules
    formalized_rules = []
    for rule in state.rules:
        formalized_rules.append({
            "id": rule.id,
            "condition": rule.condition,
            "formalized_condition": rule.formalized_condition,
            "message": rule.message,
            "severity": rule.severity.value if hasattr(rule.severity, 'value') else rule.severity
        })
    
    with open(os.path.join(output_dir, "formalized_rules.json"), 'w') as f:
        json.dump(formalized_rules, f, indent=2)
    
    # Save summary
    summary = {
        "status": state.status,
        "total_rules": len(state.rules),
        "valid_rules": sum(1 for r in state.validation_results if r.is_valid),
        "rules_with_errors": sum(1 for r in state.validation_results if not r.is_valid),
        "rules_with_warnings": sum(1 for r in state.validation_results if r.warnings),
        "total_test_cases": len(state.test_cases),
        "errors": state.errors
    }
    
    with open(os.path.join(output_dir, "summary.json"), 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Results saved to {output_dir}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
