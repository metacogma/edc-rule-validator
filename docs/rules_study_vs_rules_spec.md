# Relationship Between rules_study.xlsx and rules_spec.xlsx

## 1. File Structure & Content


## 2. Interpretation in Clinical Trials Context
### a) rules_study.xlsx
- **Purpose:** Defines the study design matrix—what forms are collected at which visits or events.
- **Role:** Source of truth for the study’s data collection plan.
- **Use Case:** Used by clinical trials data managers to ensure all protocol-required data points are scheduled and forms are mapped correctly to visits/events.

### b) rules_spec.xlsx
- **Purpose:** Specifies the technical implementation or mapping of the study design for the EDC system (e.g., Veeva).
- **Role:** Specification file for the EDC developer/study builder.
- **Use Case:** Used by EDC developers to build the EDC database, configure visit scheduling, form triggers, and ensure the system matches protocol requirements.

## 3. Relationship Between the Two Files
- **rules_study.xlsx:** Study design (what the protocol says should happen)
- **rules_spec.xlsx:** EDC implementation specification (how the system is built to make it happen)

**Workflow:**
1. Data manager creates/approves study design in rules_study.xlsx.
2. EDC developer uses rules_spec.xlsx to configure the EDC system.


## 4. Why This Matters
- **Data Managers:** Ensures all protocol-required data is captured, and the EDC system is set up to reflect the clinical trial schedule and requirements.
- **EDC Developers/Study Builders:** Provides clear, unambiguous instructions for system configuration.

## 5. Summary Table
| Role                              | File             | Main Focus              | Key Actions                                           |
|------------------------------------|------------------|-------------------------|-------------------------------------------------------|
| Clinical Trials Data Manager (JHU) | rules_study.xlsx | Protocol compliance     | Define/validate study design, ensure all forms/events |
| Veeva EDC Developer/Study Builder  | rules_spec.xlsx  | System implementation   | Build/configure EDC, ensure system matches study design |
