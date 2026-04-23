# Requirements Document

## Introduction

The V2X Decision Support Simulator is a two-stage simulation system that evaluates the effectiveness of Vehicle-to-Everything (V2X) energy technologies (V2B, V2H) under varying structural conditions. The system consists of a Base Effect Simulator that precomputes relative V2X effects offline across categorical scenario dimensions, and a Regional Evaluation Engine that aggregates those effects online using regional characteristics. The simulator produces interpretable, range-based results without generating region-specific demand time-series, adhering strictly to normalized and clustered demand representations. This project is separate from the existing V2B_simulation and V2C_Simulation codebases but may reference their demand clustering outputs.

## Glossary

- **Base_Effect_Simulator**: The offline precomputation module that solves a unified optimization model across all categorical scenario combinations and stores relative V2X effectiveness metrics in the Base Effect Table.
- **Regional_Evaluation_Engine**: The online aggregation module that maps regional characteristics to Base Effect Table entries and produces weighted expected effects and dispersion estimates.
- **Base_Effect_Table**: A multi-dimensional lookup table indexed by categorical dimensions (BuildingType, DemandCluster, EVUsageType, EVEffectiveCapacityCategory, PVUpperLimitCategory, PricingRegime) storing relative V2X effect metrics per scenario.
- **Optimization_Model**: The shared linear/convex optimization model with decision variables (PV capacity, EV charge/discharge time-series, Grid import) that minimizes total electricity cost under normalized demand, solved with different constraint switches per scenario.
- **Scenario**: One of three constraint configurations applied to the Optimization_Model: PV-only, PV+EV-no-V2X, or PV+V2X.
- **Normalized_Demand_Profile**: A demand time-series normalized to dimensionless form (e.g., divided by peak or annual total), used as input to the Optimization_Model. Not region-specific.
- **DemandCluster**: A categorical label (Cluster_1, Cluster_2, Cluster_3) assigned to a Normalized_Demand_Profile via time-series clustering of real building demand data.
- **BuildingType**: A categorical classification of building usage: Commercial or Residential.
- **EVUsageType**: A categorical classification of electric vehicle usage pattern: Private, Commuting, or Fleet.
- **EVEffectiveCapacityCategory**: A categorical classification (Low, Medium, High) of usable EV storage capacity relative to annual demand.
- **PVUpperLimitCategory**: A categorical upper bound on PV capacity as a fraction of annual demand: 0%, 20%, 50%, or 80%.
- **PricingRegime**: A categorical classification of electricity tariff structure: EnergyDominant, Mixed, or CapacityDominant.
- **Relative_Effect_Metric**: A dimensionless ratio (e.g., cost reduction ratio, peak reduction ratio) expressing V2X effectiveness without absolute units (no kWh, kW, or currency).
- **Incremental_Effect**: The marginal change in a Relative_Effect_Metric when moving from one Scenario to the next (e.g., PV-only → PV+EV, PV+EV → PV+V2X).
- **Validation_Mode**: A consistency-checking procedure that compares Base_Effect_Simulator outputs against detailed simulation results from existing V2B/V2C simulators for representative cases.
- **AnnualElectricityDemand**: The sole scalable regional input, expressed in kWh, used by the Regional_Evaluation_Engine to convert relative effects to absolute estimates.
- **Effect_Distribution**: A range or probability distribution of expected V2X effects produced by the Regional_Evaluation_Engine, reflecting uncertainty from categorical distribution weights.

## Requirements

### Requirement 1: Design Principle Enforcement — No Region-Specific Demand Time-Series

**User Story:** As a simulation engineer, I want the system to enforce that no region-specific demand time-series are generated, so that all analyses remain structurally generalizable and free from regional bias.

#### Acceptance Criteria

1. THE Base_Effect_Simulator SHALL use only Normalized_Demand_Profiles indexed by DemandCluster as demand inputs to the Optimization_Model.
2. THE Regional_Evaluation_Engine SHALL accept only AnnualElectricityDemand as a scalable numeric input and categorical distributions as non-scalable inputs.
3. IF a caller provides maximum demand, PV capacity in absolute units, or EV capacity in absolute units as input, THEN THE Regional_Evaluation_Engine SHALL reject the input and return a descriptive error identifying the disallowed parameter.
4. THE Base_Effect_Simulator SHALL store all output metrics as Relative_Effect_Metrics without absolute units (no kWh, kW, or currency values).

### Requirement 2: Base Effect Table Index Structure

**User Story:** As a simulation engineer, I want the Base Effect Table to be indexed by well-defined categorical dimensions, so that every scenario combination is enumerable and reproducible.

#### Acceptance Criteria

1. THE Base_Effect_Table SHALL be indexed by exactly six categorical dimensions: BuildingType, DemandCluster, EVUsageType, EVEffectiveCapacityCategory, PVUpperLimitCategory, and PricingRegime.
2. THE Base_Effect_Table SHALL contain entries for all valid combinations of: BuildingType ∈ {Commercial, Residential}, DemandCluster ∈ {Cluster_1, Cluster_2, Cluster_3}, EVUsageType ∈ {Private, Commuting, Fleet}, EVEffectiveCapacityCategory ∈ {Low, Medium, High}, PVUpperLimitCategory ∈ {0%, 20%, 50%, 80%}, and PricingRegime ∈ {EnergyDominant, Mixed, CapacityDominant}.
3. WHEN a Base_Effect_Table entry is queried by a valid combination of the six categorical indices, THE Base_Effect_Table SHALL return exactly one entry containing all stored Relative_Effect_Metrics for that combination.

### Requirement 3: Unified Optimization Model Structure

**User Story:** As a simulation engineer, I want a single optimization model with switchable constraints, so that all scenarios are solved consistently and differences arise only from constraint configuration.

#### Acceptance Criteria

1. THE Optimization_Model SHALL define decision variables for: PV capacity (continuous, bounded by PVUpperLimitCategory), EV charge schedule (time-series, non-negative), EV discharge schedule (time-series, non-negative or zero depending on Scenario), and Grid import (time-series).
2. THE Optimization_Model SHALL minimize total electricity cost under the Normalized_Demand_Profile subject to: power balance, EV state-of-charge bounds, EV availability constraints, PV generation constraints, and PV upper bound constraint.
3. THE Optimization_Model SHALL re-optimize PV capacity independently in each Scenario rather than fixing PV capacity from a prior Scenario.

### Requirement 4: Scenario Constraint Switching

**User Story:** As a simulation engineer, I want each scenario to differ only by which constraints are active, so that incremental V2X effects are isolated cleanly.

#### Acceptance Criteria

1. WHEN Scenario is PV-only, THE Optimization_Model SHALL set EV charge to zero and EV discharge to zero for all time steps.
2. WHEN Scenario is PV+EV-no-V2X, THE Optimization_Model SHALL allow EV charge to be non-negative and set EV discharge to zero for all time steps.
3. WHEN Scenario is PV+V2X, THE Optimization_Model SHALL allow EV charge to be non-negative, allow EV discharge up to the permitted limit, and enable demand-side control.
4. THE Base_Effect_Simulator SHALL solve the Optimization_Model exactly three times per Base_Effect_Table entry, once for each Scenario (PV-only, PV+EV-no-V2X, PV+V2X).

### Requirement 5: Base Effect Table Output Metrics

**User Story:** As a simulation engineer, I want each Base Effect Table entry to store relative metrics per scenario and incremental effects, so that downstream aggregation operates on dimensionless quantities.

#### Acceptance Criteria

1. THE Base_Effect_Simulator SHALL store for each Scenario within a Base_Effect_Table entry: optimal PV capacity relative to annual demand, total cost reduction ratio as a percentage, and peak reduction ratio as a percentage.
2. THE Base_Effect_Simulator SHALL compute and store Incremental_Effects for transitions: PV-only to PV+EV-no-V2X, and PV+EV-no-V2X to PV+V2X.
3. IF a computed metric has absolute units (kWh, kW, or currency), THEN THE Base_Effect_Simulator SHALL reject the metric and raise a validation error before storing.

### Requirement 6: Regional Input Classification and Validation

**User Story:** As a simulation engineer, I want the Regional Evaluation Engine to enforce strict input classification, so that only structurally valid inputs are accepted.

#### Acceptance Criteria

1. THE Regional_Evaluation_Engine SHALL accept AnnualElectricityDemand in kWh as the sole scalable numeric input.
2. THE Regional_Evaluation_Engine SHALL accept BuildingTypeMix, DemandClusterDistribution, EVUsageTypeDistribution, and PricingRegime as categorical inputs.
3. THE Regional_Evaluation_Engine SHALL accept PVUpperLimitCategory and EVEffectiveCapacityCategory as constraint-selection inputs.
4. IF a caller provides maximum demand, PV capacity, or EV capacity as a direct numeric input, THEN THE Regional_Evaluation_Engine SHALL reject the request and return an error message specifying which disallowed input was provided.
5. THE Regional_Evaluation_Engine SHALL validate that all categorical distribution inputs (BuildingTypeMix, DemandClusterDistribution, EVUsageTypeDistribution) have weights that sum to 1.0 within a tolerance of 0.001.

### Requirement 7: Regional Aggregation Procedure

**User Story:** As a simulation engineer, I want the Regional Evaluation Engine to compute weighted expected effects from the Base Effect Table, so that regional estimates reflect the distribution of local conditions.

#### Acceptance Criteria

1. WHEN regional categorical distributions are provided, THE Regional_Evaluation_Engine SHALL identify all applicable Base_Effect_Table entries matching the constraint-selection inputs (PVUpperLimitCategory, EVEffectiveCapacityCategory).
2. THE Regional_Evaluation_Engine SHALL compute weights for each applicable Base_Effect_Table entry as the product of the corresponding categorical distribution probabilities (BuildingTypeMix × DemandClusterDistribution × EVUsageTypeDistribution).
3. THE Regional_Evaluation_Engine SHALL compute ExpectedEffect as the weighted sum: Σ(weight_i × effect_i) over all applicable entries.
4. THE Regional_Evaluation_Engine SHALL scale the ExpectedEffect by AnnualElectricityDemand only when converting relative results to absolute estimates for the user.

### Requirement 8: Regional Output Format

**User Story:** As a simulation engineer, I want the Regional Evaluation Engine to return range-based results with explanations, so that users understand both the expected outcome and its uncertainty.

#### Acceptance Criteria

1. THE Regional_Evaluation_Engine SHALL return expected cost reduction as a range (minimum, expected, maximum) rather than a single point estimate.
2. THE Regional_Evaluation_Engine SHALL return expected peak reduction as a range (minimum, expected, maximum) rather than a single point estimate.
3. THE Regional_Evaluation_Engine SHALL return a ranking of V2X options ordered by expected effectiveness.
4. THE Regional_Evaluation_Engine SHALL return a textual explanation identifying which categorical conditions (BuildingType, DemandCluster, EVUsageType, PricingRegime) most strongly influenced the result.

### Requirement 9: Validation Mode — Consistency with Existing Simulators

**User Story:** As a simulation engineer, I want a validation mode that checks Base Effect Table outputs against detailed V2B/V2C simulation results, so that I can confirm structural consistency.

#### Acceptance Criteria

1. WHEN Validation_Mode is invoked with a representative detailed simulation case, THE Validation_Mode SHALL map the case parameters to the corresponding Base_Effect_Table categorical indices.
2. THE Validation_Mode SHALL compare the sign of each effect (positive or negative) between the Base_Effect_Table entry and the detailed simulation result.
3. THE Validation_Mode SHALL compare the order of magnitude of each effect between the Base_Effect_Table entry and the detailed simulation result.
4. THE Validation_Mode SHALL compare sensitivity trends (which parameter changes cause the largest effect changes) between the Base_Effect_Table and the detailed simulation.
5. THE Validation_Mode SHALL report pass or fail for each comparison criterion (sign, order of magnitude, sensitivity trend) independently, without requiring exact numerical equality.

### Requirement 10: Trust and Interpretability — Result Explanation

**User Story:** As a simulation engineer, I want every result to include a structural explanation of the driving factors, so that the system is never a black box.

#### Acceptance Criteria

1. THE Regional_Evaluation_Engine SHALL include in every output an explanation of which assumptions (DemandCluster shape, EVUsageType pattern, PricingRegime) determined the result.
2. THE Regional_Evaluation_Engine SHALL identify and report which constraints (PVUpperLimitCategory, EVEffectiveCapacityCategory) limited the V2X effect in the result.
3. WHEN multiple V2X options are ranked, THE Regional_Evaluation_Engine SHALL explain why the top-ranked option dominates the others by referencing specific categorical conditions.
4. IF a result shows minimal V2X benefit, THEN THE Regional_Evaluation_Engine SHALL explain which structural condition is the primary limiting factor.

### Requirement 11: Project Separation and Workspace Integration

**User Story:** As a simulation engineer, I want the V2X Decision Support Simulator to be a separate project from V2B_simulation and V2C_Simulation, so that codebases remain independent while coexisting in the same workspace.

#### Acceptance Criteria

1. THE V2X Decision Support Simulator SHALL reside in a dedicated top-level directory separate from V2B_simulation and V2C_Simulation.
2. THE V2X Decision Support Simulator SHALL not modify any files within the V2B_simulation or V2C_Simulation directories.
3. WHERE the V2X Decision Support Simulator references demand clustering outputs from V2B_simulation, THE V2X Decision Support Simulator SHALL import or copy the data rather than depending on V2B_simulation source code at runtime.

### Requirement 12: Base Effect Table Serialization

**User Story:** As a simulation engineer, I want the Base Effect Table to be serializable to and from a structured file format, so that precomputed results can be stored, versioned, and reloaded without re-running the optimization.

#### Acceptance Criteria

1. THE Base_Effect_Simulator SHALL serialize the complete Base_Effect_Table to a structured file format (JSON or CSV).
2. WHEN a serialized Base_Effect_Table file is loaded, THE Base_Effect_Simulator SHALL parse the file and reconstruct the Base_Effect_Table with all categorical indices and Relative_Effect_Metrics intact.
3. FOR ALL valid Base_Effect_Table instances, serializing then deserializing SHALL produce a Base_Effect_Table equivalent to the original (round-trip property).
4. IF a serialized file is malformed or missing required fields, THEN THE Base_Effect_Simulator SHALL return a descriptive error identifying the structural problem.
