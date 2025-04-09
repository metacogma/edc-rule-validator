/**
 * Eclaire Trials Edit Check Rule Validator
 * Main JavaScript for the web interface
 */

document.addEventListener('DOMContentLoaded', function() {
    // Form submission handling
    const uploadForm = document.getElementById('upload-form');
    const jobStatus = document.getElementById('job-status');
    const statusMessage = document.getElementById('status-message');
    const resultsContainer = document.getElementById('results-container');
    const noResults = document.getElementById('no-results');
    
    // Current job tracking
    let currentJobId = null;
    let statusCheckInterval = null;
    
    // Form submission
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Show loading state
        jobStatus.classList.remove('d-none');
        jobStatus.classList.remove('alert-success', 'alert-danger');
        jobStatus.classList.add('alert-info');
        statusMessage.textContent = 'Uploading files...';
        
        // Hide results and no results message
        resultsContainer.classList.add('d-none');
        noResults.classList.add('d-none');
        
        // Get form data
        const formData = new FormData(uploadForm);
        
        // Add boolean values for switches
        formData.set('formalize_rules', document.getElementById('formalize-rules').checked);
        formData.set('verify_with_z3', document.getElementById('verify-rules').checked);
        formData.set('generate_tests', document.getElementById('generate-tests').checked);
        
        // Upload files
        fetch('/api/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showError(data.error);
                return;
            }
            
            // Store job ID
            currentJobId = data.job_id;
            
            // Update status
            statusMessage.textContent = 'Files uploaded successfully. Starting validation...';
            
            // Start validation
            startValidation(currentJobId);
        })
        .catch(error => {
            showError('Error uploading files: ' + error.message);
        });
    });
    
    // Start validation process
    function startValidation(jobId) {
        fetch(`/api/validate/${jobId}`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showError(data.error);
                return;
            }
            
            // Start checking status
            checkJobStatus(jobId);
        })
        .catch(error => {
            showError('Error starting validation: ' + error.message);
        });
    }
    
    // Check job status
    function checkJobStatus(jobId) {
        // Clear any existing interval
        if (statusCheckInterval) {
            clearInterval(statusCheckInterval);
        }
        
        // Set up interval to check status
        statusCheckInterval = setInterval(() => {
            fetch(`/api/jobs/${jobId}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    clearInterval(statusCheckInterval);
                    showError(data.error);
                    return;
                }
                
                // Update status message
                updateStatusMessage(data.status);
                
                // If job is complete, load results
                if (['completed', 'completed_with_warnings', 'failed'].includes(data.status)) {
                    clearInterval(statusCheckInterval);
                    loadResults(jobId);
                }
            })
            .catch(error => {
                clearInterval(statusCheckInterval);
                showError('Error checking job status: ' + error.message);
            });
        }, 2000); // Check every 2 seconds
    }
    
    // Update status message
    function updateStatusMessage(status) {
        switch (status) {
            case 'uploaded':
                statusMessage.textContent = 'Files uploaded. Waiting to start validation...';
                break;
            case 'running':
                statusMessage.textContent = 'Validation in progress...';
                break;
            case 'completed':
                statusMessage.textContent = 'Validation completed successfully!';
                jobStatus.classList.remove('alert-info', 'alert-danger');
                jobStatus.classList.add('alert-success');
                break;
            case 'completed_with_warnings':
                statusMessage.textContent = 'Validation completed with warnings.';
                jobStatus.classList.remove('alert-info', 'alert-danger');
                jobStatus.classList.add('alert-warning');
                break;
            case 'failed':
                statusMessage.textContent = 'Validation failed.';
                jobStatus.classList.remove('alert-info', 'alert-success');
                jobStatus.classList.add('alert-danger');
                break;
            default:
                statusMessage.textContent = `Status: ${status}`;
        }
    }
    
    // Show error message
    function showError(message) {
        jobStatus.classList.remove('d-none', 'alert-info', 'alert-success');
        jobStatus.classList.add('alert-danger');
        statusMessage.textContent = message;
        noResults.classList.remove('d-none');
    }
    
    // Load results
    function loadResults(jobId) {
        // Show results container
        resultsContainer.classList.remove('d-none');
        noResults.classList.add('d-none');
        
        // Load summary
        fetch(`/api/jobs/${jobId}`)
        .then(response => response.json())
        .then(data => {
            if (data.summary) {
                document.getElementById('total-rules').textContent = data.summary.total_rules;
                document.getElementById('valid-rules').textContent = data.summary.valid_rules;
                document.getElementById('rules-with-warnings').textContent = data.summary.rules_with_warnings;
                document.getElementById('total-test-cases').textContent = data.summary.total_test_cases;
            }
        })
        .catch(error => {
            console.error('Error loading summary:', error);
        });
        
        // Load validation results
        fetch(`/api/results/${jobId}/validation_results`)
        .then(response => response.json())
        .then(data => {
            renderValidationResults(data);
        })
        .catch(error => {
            console.error('Error loading validation results:', error);
            document.getElementById('validation-results').innerHTML = '<div class="alert alert-danger">Error loading validation results</div>';
        });
        
        // Load formalized rules
        fetch(`/api/results/${jobId}/formalized_rules`)
        .then(response => response.json())
        .then(data => {
            renderFormalizedRules(data);
        })
        .catch(error => {
            console.error('Error loading formalized rules:', error);
            document.getElementById('formalized-rules').innerHTML = '<div class="alert alert-danger">Error loading formalized rules</div>';
        });
        
        // Load test cases
        fetch(`/api/results/${jobId}/test_cases`)
        .then(response => response.json())
        .then(data => {
            renderTestCases(data);
        })
        .catch(error => {
            console.error('Error loading test cases:', error);
            document.getElementById('test-cases').innerHTML = '<div class="alert alert-danger">Error loading test cases</div>';
        });
    }
    
    // Render validation results
    function renderValidationResults(results) {
        const container = document.getElementById('validation-results');
        
        if (!results || results.length === 0) {
            container.innerHTML = '<div class="alert alert-info">No validation results available</div>';
            return;
        }
        
        let html = '';
        
        results.forEach(result => {
            const statusClass = result.is_valid ? 'success' : 'danger';
            const statusText = result.is_valid ? 'Valid' : 'Invalid';
            
            html += `
                <div class="rule-card">
                    <div class="rule-header">
                        <span class="rule-id">Rule ${result.rule_id}</span>
                        <span class="status-badge ${statusClass}">${statusText}</span>
                    </div>
            `;
            
            if (result.errors && result.errors.length > 0) {
                html += '<div class="error-list">';
                result.errors.forEach(error => {
                    html += `<div class="error-item">${error.message}</div>`;
                });
                html += '</div>';
            }
            
            if (result.warnings && result.warnings.length > 0) {
                html += '<div class="warning-list">';
                result.warnings.forEach(warning => {
                    html += `<div class="warning-item">${warning.message}</div>`;
                });
                html += '</div>';
            }
            
            html += '</div>';
        });
        
        container.innerHTML = html;
    }
    
    // Render formalized rules
    function renderFormalizedRules(rules) {
        const container = document.getElementById('formalized-rules');
        
        if (!rules || rules.length === 0) {
            container.innerHTML = '<div class="alert alert-info">No formalized rules available</div>';
            return;
        }
        
        let html = '';
        
        rules.forEach(rule => {
            html += `
                <div class="rule-card">
                    <div class="rule-header">
                        <span class="rule-id">Rule ${rule.id}</span>
                        <span class="status-badge ${rule.formalized_condition ? 'success' : 'warning'}">${rule.formalized_condition ? 'Formalized' : 'Not Formalized'}</span>
                    </div>
                    
                    <div class="rule-condition">Original: ${escapeHtml(rule.condition)}</div>
            `;
            
            if (rule.formalized_condition) {
                html += `<div class="rule-formalized">Formalized: ${escapeHtml(rule.formalized_condition)}</div>`;
            }
            
            if (rule.message) {
                html += `<div class="rule-message">Message: ${escapeHtml(rule.message)}</div>`;
            }
            
            html += '</div>';
        });
        
        container.innerHTML = html;
    }
    
    // Render test cases
    function renderTestCases(testCases) {
        const container = document.getElementById('test-cases');
        
        if (!testCases || testCases.length === 0) {
            container.innerHTML = '<div class="alert alert-info">No test cases available</div>';
            return;
        }
        
        let html = '';
        
        // Group test cases by rule
        const groupedTestCases = {};
        testCases.forEach(testCase => {
            if (!groupedTestCases[testCase.rule_id]) {
                groupedTestCases[testCase.rule_id] = [];
            }
            groupedTestCases[testCase.rule_id].push(testCase);
        });
        
        // Render each group
        for (const ruleId in groupedTestCases) {
            html += `<h5 class="mt-3 mb-2">Rule ${ruleId}</h5>`;
            
            groupedTestCases[ruleId].forEach(testCase => {
                const typeClass = testCase.is_positive ? 'success' : 'danger';
                const typeText = testCase.is_positive ? 'Positive' : 'Negative';
                
                html += `
                    <div class="test-case-card">
                        <div class="test-case-header">
                            <span class="test-case-description">${escapeHtml(testCase.description)}</span>
                            <span class="status-badge ${typeClass}">${typeText} Test</span>
                        </div>
                        
                        <div class="test-data">${JSON.stringify(testCase.test_data, null, 2)}</div>
                        <div class="mt-2">
                            <small>Expected Result: <strong>${testCase.expected_result ? 'Pass' : 'Fail'}</strong></small>
                        </div>
                    </div>
                `;
            });
        }
        
        container.innerHTML = html;
    }
    
    // Helper function to escape HTML
    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
