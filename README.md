# Edit Check Rule Validation System

An enterprise-grade system for validating edit check rules in clinical trials, developed for Eclaire Trials.

## Overview

The Edit Check Rule Validation System is a comprehensive solution that integrates study specifications and edit check rules to ensure consistency, correctness, and completeness in clinical trial data validation. The system leverages LangGraph for workflow orchestration and Azure OpenAI for intelligent rule formalization.

## Key Features

- **Unified Parser**: Flexible parsing of study specifications and edit check rules from Excel files
- **Advanced Rule Validation**: Formal verification using Z3 theorem prover for logical consistency
- **AI-Powered Rule Formalization**: Converting natural language rules to structured format using Azure OpenAI
- **Advanced Test Generation**: Multiple techniques for comprehensive test coverage:
  - **Metamorphic Testing**: Generates related test cases based on input transformations
  - **Symbolic Execution**: Systematically explores execution paths through rules
  - **Adversarial Testing**: Creates test cases designed to find weaknesses
  - **Causal Inference**: Explores causal relationships between variables
- **Multi-Modal Verification**: Combines multiple approaches to verify test cases
- **Enterprise-Grade Workflow**: LangGraph orchestration with robust error recovery

## Production Readiness

The system has been assessed for production readiness with the following considerations:

### Strengths
- Modular architecture with clear separation of concerns
- Configurable workflow with conditional paths
- Robust fallback mechanisms for graceful degradation
- Comprehensive test generation techniques

### Areas for Enhancement
- Security: Data sanitization, access controls, audit logging
- Reliability: Circuit breakers, caching, error recovery
- Scalability: Batch processing, resource limits, optimization
- Operations: Monitoring, health checks, enhanced logging

See [Production Readiness Assessment](docs/production_readiness.md) for a detailed review.

## Documentation

- [Advanced Test Generation](docs/advanced_test_generation.md): Details on test generation techniques
- [Advanced Validation & Formalization](docs/advanced_validation_formalization.md): Deep dive into validation and formalization
- [Production Readiness](docs/production_readiness.md): End-to-end assessment

## Color Scheme

The system follows Eclaire Trials' design system:
- Primary: Blue (#0074D9)
- Secondary: Orange (#FF9500)
- Accent: Purple (#7F4FBF)

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
