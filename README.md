# Eclaire Trials Edit Check Rule Validation System

An enterprise-grade system for validating edit check rules in clinical trials, developed for Eclaire Trials' clinical trial intelligence platform.

## Overview

The Eclaire Trials Edit Check Rule Validation System is a comprehensive solution that integrates study specifications and edit check rules to ensure consistency, correctness, and completeness in clinical trial data validation. The system provides both a LangGraph-based workflow and a custom workflow implementation, with a production-ready API for seamless integration into enterprise environments.

## Key Features

- **Unified Parser**: Flexible parsing of study specifications and edit check rules from Excel files
- **Advanced Rule Validation**: Formal verification using Z3 theorem prover for logical consistency
- **AI-Powered Rule Formalization**: Converting natural language rules to structured format using OpenAI
- **Advanced Test Generation**: Multiple techniques for comprehensive test coverage:
  - **Metamorphic Testing**: Generates related test cases based on input transformations
  - **Symbolic Execution**: Systematically explores execution paths through rules
  - **Adversarial Testing**: Creates test cases designed to find weaknesses
  - **Causal Inference**: Explores causal relationships between variables
- **Multi-Modal Verification**: Combines multiple approaches to verify test cases
- **Enterprise-Grade Workflow**: Both LangGraph orchestration and custom workflow with robust error recovery
- **Production-Ready API**: RESTful API with comprehensive documentation and client SDKs
- **Containerized Deployment**: Docker and Kubernetes support for scalable deployment

## Production Readiness

The system is production-ready with the following enterprise-grade features:

### API Layer
- **RESTful API**: Comprehensive FastAPI-based API for all system functionality
- **Async Processing**: Background task processing for long-running operations
- **Job Management**: Tracking and management of validation jobs
- **Swagger Documentation**: Interactive API documentation with OpenAPI

### Deployment
- **Docker Containers**: Containerized deployment for consistency across environments
- **Docker Compose**: Multi-container orchestration for development and testing
- **Kubernetes Support**: Production deployment with scaling, monitoring, and high availability
- **NGINX Integration**: Secure reverse proxy with SSL termination

### Security
- **HTTPS Encryption**: All API traffic secured with TLS 1.2+
- **Input Validation**: Comprehensive validation of all API inputs
- **Rate Limiting**: Protection against abuse and DoS attacks
- **Authentication**: JWT-based authentication for secure access

### Monitoring & Reliability
- **Health Checks**: Comprehensive system health monitoring
- **Prometheus Metrics**: Real-time performance metrics
- **Logging**: Structured JSON logging for easy integration with ELK/Splunk
- **Error Handling**: Graceful degradation and comprehensive error reporting

See [Production Readiness Assessment](docs/production_readiness.md) for a detailed review.

## Documentation

- [API Reference](docs/api_reference.md): Comprehensive API documentation
- [Deployment Guide](docs/deployment_guide.md): Instructions for deploying in various environments
- [Advanced Test Generation](docs/advanced_test_generation.md): Details on test generation techniques
- [Advanced Validation & Formalization](docs/advanced_validation_formalization.md): Deep dive into validation and formalization
- [Production Readiness](docs/production_readiness.md): End-to-end assessment

## Quick Start

### API Usage

```bash
# Start the API server
docker-compose up -d

# Access the API documentation
open http://localhost/docs
```

### Validate Rules via API

```python
import requests

# Upload files for validation
files = {
    'rules_file': open('path/to/rules.xlsx', 'rb'),
    'spec_file': open('path/to/specification.xlsx', 'rb')
}

# Submit validation job
response = requests.post('https://validator.eclairetrials.com/api/v1/validate', files=files)
job_id = response.json()['job_id']

# Check job status
status_response = requests.get(f'https://validator.eclairetrials.com/api/v1/jobs/{job_id}')
print(status_response.json())

# Get results when job is completed
if status_response.json()['status'] == 'completed':
    results = requests.get(f'https://validator.eclairetrials.com/api/v1/results/{job_id}')
    print(results.json())
```

## Color Scheme

The system follows Eclaire Trials' enterprise design system:
- Primary: Blue (#0074D9) - Used for primary actions, headers, and key UI elements
- Secondary: Orange (#FF9500) - Used for secondary actions, highlights, and notifications
- Accent: Purple (#7F4FBF) - Used for tertiary elements, selected states, and decorative elements

All API responses, documentation, and UI components maintain this consistent branding to align with Eclaire Trials' enterprise clinical trial intelligence platform.

## Getting Started

### Installation

```bash
# Clone the repository
git clone https://github.com/eclaire-trials/edc-rule-validator.git
cd edc-rule-validator

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your Azure OpenAI credentials
```

### Usage

```bash
# Run the validation workflow
python -m src.run_validation --rules path/to/rules.xlsx --spec path/to/spec.xlsx

# Start the web interface
python -m src.api.app
```

## Architecture

The system follows a modular architecture with the following components:

- **Parsers**: Extract data from Excel files
- **Validators**: Ensure rule consistency and completeness
- **LLM Integration**: Formalize rules using Azure OpenAI
- **Test Generation**: Create comprehensive test cases
- **Workflow**: Orchestrate the validation process

## License

Copyright © 2025 Eclaire Trials. All rights reserved.
