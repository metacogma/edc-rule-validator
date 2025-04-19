# Eclaire Trials Integrated Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  ECLAIRE TRIALS EDIT CHECK RULE VALIDATION SYSTEM            │
│                         INTEGRATED WORKFLOW ARCHITECTURE                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               INPUT LAYER                                    │
│                                                                             │
│  ┌───────────────────────┐           ┌───────────────────────┐             │
│  │ run_integrated_workflow.py │◄────►│ Excel Files           │             │
│  │ (Blue #0074D9)        │           │ (Orange #FF9500)      │             │
│  └───────────────────────┘           └───────────────────────┘             │
│                                      │                                      │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CORE PROCESSING LAYER                             │
│                                                                             │
│  ┌───────────────────────┐                                                  │
│  │ CustomParser          │                                                  │
│  │ (Purple #7F4FBF)      │                                                  │
│  └───────────────────────┘                                                  │
│           │                                                                 │
│           ├─────────────────┬─────────────────┐                             │
│           │                 │                 │                             │
│           ▼                 ▼                 ▼                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐           │
│  │ Rule Parsing  │  │ Spec Parsing  │  │ DynamicsProcessor     │           │
│  └───────────────┘  └───────────────┘  │ (Purple #7F4FBF)      │           │
│           │                 │          └───────────────────────┘           │
│           │                 │                   │                           │
│           │                 │          ┌────────┴─────────┐                │
│           │                 │          │                  │                │
│           ▼                 ▼          ▼                  ▼                │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ EditCheckRule │  │ Study         │  │ Extract      │  │ Expand       │  │
│  │ Model         │  │ Specification │  │ Dynamics     │  │ Derivatives  │  │
│  └───────────────┘  └───────────────┘  └──────────────┘  └──────────────┘  │
│           │                 │                 │                 │           │
│           │                 │                 │                 │           │
│           └─────────────────┼─────────────────┼─────────────────┘           │
│                             │                 │                             │
│                             ▼                 ▼                             │
│                      ┌───────────────────────────────┐                      │
│                      │ RuleValidator                 │                      │
│                      │ (Purple #7F4FBF)              │                      │
│                      └───────────────────────────────┘                      │
│                                     │                                       │
│                                     ▼                                       │
│                      ┌───────────────────────────────┐                      │
│                      │ DynamicsValidator             │                      │
│                      │ (Purple #7F4FBF)              │                      │
│                      └───────────────────────────────┘                      │
│                                     │                                       │
│                                     ▼                                       │
│                      ┌───────────────────────────────┐                      │
│                      │ ValidationResult              │                      │
│                      └───────────────────────────────┘                      │
│                                     │                                       │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TEST GENERATION LAYER                              │
│                                                                             │
│                      ┌───────────────────────────────┐                      │
│                      │ WorkflowOrchestrator          │                      │
│                      │ (Purple #7F4FBF)              │                      │
│                      └───────────────────────────────┘                      │
│                                     │                                       │
│                                     ▼                                       │
│        ┌────────────────────────────────────────────────────────┐          │
│        │                   Test Generation                       │          │
│        │                                                         │          │
│        │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │          │
│        │  │ Metamorphic │ │ Symbolic    │ │ Adversarial     │   │          │
│        │  │ Testing     │ │ Testing     │ │ Testing         │   │          │
│        │  └─────────────┘ └─────────────┘ └─────────────────┘   │          │
│        │                                                         │          │
│        │  ┌─────────────┐ ┌─────────────────────────────────┐   │          │
│        │  │ Causal      │ │ Dynamic Function Test Cases      │   │          │
│        │  │ Testing     │ │ (New in Integrated Workflow)     │   │          │
│        │  └─────────────┘ └─────────────────────────────────┘   │          │
│        └────────────────────────────────────────────────────────┘          │
│                                     │                                       │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               OUTPUT LAYER                                   │
│                                                                             │
│  ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐│
│  │ JSON Validation     │   │ JSON Test Cases     │   │ HTML Report         ││
│  │ Results             │   │                     │   │                     ││
│  │ (Blue #0074D9)      │   │ (Blue #0074D9)      │   │ (Blue #0074D9)      ││
│  └─────────────────────┘   └─────────────────────┘   └─────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Color Scheme (Eclaire Trials Brand Colors)

- **Blue (#0074D9)**: Primary color - Used for entry points and outputs
- **Orange (#FF9500)**: Secondary color - Used for data sources
- **Purple (#7F4FBF)**: Accent color - Used for core processing components

## Architecture Flow

1. **Input Layer**: The workflow begins with `run_integrated_workflow.py` reading Excel files
2. **Core Processing Layer**: 
   - `CustomParser` processes Excel files and extracts rules, specifications
   - `DynamicsProcessor` identifies dynamic functions and expands the specification with derivatives
   - `RuleValidator` and `DynamicsValidator` validate rules against the specification
3. **Test Generation Layer**:
   - `WorkflowOrchestrator` manages the test generation process
   - Multiple testing techniques are applied (Metamorphic, Symbolic, Adversarial, Causal)
   - Dynamic function test cases are generated (new in the integrated workflow)
4. **Output Layer**:
   - Results are output as JSON validation results, JSON test cases, and a branded HTML report

## Key Improvements in the Integrated Workflow

1. **Combined Functionality**: Merges dynamics processing with test case generation
2. **Enhanced Test Coverage**: Generates test cases specifically for dynamic functions
3. **Comprehensive Reporting**: Produces detailed reports with validation results and test cases
4. **Enterprise-Grade Implementation**: Follows Eclaire Trials' production standards with proper error handling and branding

This enterprise-grade architecture supports the clinical trial intelligence platform's needs for robust rule validation with dynamics and test case generation capabilities.
