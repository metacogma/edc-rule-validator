# Eclaire Trials Edit Check Rule Validation System - Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  ECLAIRE TRIALS EDIT CHECK RULE VALIDATION SYSTEM            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               INPUT LAYER                                    │
│                                                                             │
│  ┌───────────────────────┐           ┌───────────────────────┐             │
│  │ run_dynamics_workflow.py │◄────────►│ Excel Files           │             │
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
│                      │ ValidationResult              │                      │
│                      └───────────────────────────────┘                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               OUTPUT LAYER                                   │
│                                                                             │
│                 ┌─────────────────────┐   ┌─────────────────────┐           │
│                 │ JSON Results        │   │ HTML Report         │           │
│                 │ (Blue #0074D9)      │   │ (Blue #0074D9)      │           │
│                 └─────────────────────┘   └─────────────────────┘           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Color Scheme (Eclaire Trials Brand Colors)

- **Blue (#0074D9)**: Primary color - Used for entry points and outputs
- **Orange (#FF9500)**: Secondary color - Used for data sources
- **Purple (#7F4FBF)**: Accent color - Used for core processing components

## Architecture Flow

1. The workflow begins with `run_dynamics_workflow.py` reading Excel files from `data/excel`
2. `CustomParser` processes these files and extracts rules, specifications, and dynamics
3. `DynamicsProcessor` identifies dynamic functions and expands the specification with derivatives
4. `RuleValidator` validates rules against the specification with dynamics support
5. Results are output as JSON and a branded HTML report with Eclaire Trials colors

This enterprise-grade architecture supports the clinical trial intelligence platform's needs for robust rule validation with dynamics and derivatives capabilities.
