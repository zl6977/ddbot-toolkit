# Signal intent checklist

Use this checklist to help a user describe a drilling signal well enough to model it as DWIS CONFIG.
It is a dialogue guide, not a questionnaire to present in full and not a post-generation validation
list.

## Dialogue method

Maintain a working intent sketch throughout the conversation. For each field, track one of:
`known`, `assumed`, `not_applicable`, or `unknown`.

1. Extract everything already stated or available in an existing CONFIG.
2. Identify unknowns that could change the graph or ontology grounding.
3. Ask one coherent group of high-impact questions per turn, normally no more than three.
4. Update the sketch after every answer and do not repeat resolved questions.
5. Stop eliciting when the core description is complete and every applicable conditional section is
   either known, accepted as an assumption, or explicitly not applicable.

Ask in plain engineering language. The user does not need to know DWIS classes or predicates.

## Core description

Establish these fields for every signal:

- **Identity and purpose**: What is the signal called, what does it represent, and how will it be
  used?
- **Quantity or state**: What physical quantity, operational state, command, limit, or other concept
  does its value express?
- **Value role**: Is it an observed value, set point, command, limit, status, or another role?
- **Value behavior**: Is it dynamic or static? If relevant, is it continuous, discrete, Boolean, or
  categorical?
- **Origin**: Is it measured, estimated, calculated, transformed, manually entered, or supplied by
  another system?
- **Context**: Where or for what equipment/process does it apply? Mark location as not applicable
  when the concept is genuinely location-independent.

The engineering purpose may resolve several fields at once. Do not ask the user to restate them
separately.

## Conditional details

Ask only the sections triggered by the core description.

### Quantity and unit

- What measurable quantity is intended?
- Is a unit required, and which unit should be represented?
- Is the value absolute, differential, relative, normalized, or otherwise referenced?

### Measured signal

- What device or sensor measures it?
- Where is the measurement taken?
- Does the acquisition clock, timestamp, or sampling context matter?

### Estimated or calculated signal

- What computation or estimation method produces it?
- Which input signals or parameters does it depend on?
- At what physical, mechanical, or hydraulic location is the estimate valid?

### Transformed signal

- What transformation is applied?
- Which signal or signals are its inputs?
- Is this signal the transformation output, and must the original signal also be represented?

### Location and reference

- Is the relevant context physical, mechanical, hydraulic, or more than one of these?
- What component, logical element, well position, or reference location identifies it?
- Does it require a reference frame, datum, or direction?

### Data flow and timing

- Who or what provides the signal, and who consumes it?
- Is it transmitted through a telemetry or communication system?
- Does source time, acquisition time, clock, delay, or synchronization need representation?

### Uncertainty and quality

- Must uncertainty be represented?
- Is it Gaussian, sensor accuracy/precision, full-scale error, or another model?
- Are uncertainty values carried by this signal or by separate signals?

### Control, limits, and procedures

- Is the signal used by a controller, advisor, objective, limit, incident, or procedure?
- Is it enabling, allowing, recommending, comparing, or triggering an action?
- Which related function, objective, incident, phase, action, or task must be represented?

## Clarification priority

Ask first about unknowns that select different graph structures:

1. what the value means and its role;
2. measured versus estimated/calculated/transformed origin;
3. required location and reference semantics;
4. dependencies, provider/consumer flow, and control relationships;
5. uncertainty, timing, and optional descriptive detail.

Do not block generation on a field that is irrelevant to the requested signal. Do block when two
plausible answers would require different entities or relations and the user has not authorized an
assumption.

## Intent sketch

Use this shape as a guide and omit fields that are not applicable. Preserve user terminology until
ontology grounding begins.

```yaml
operation: create | modify | repair
signal:
  name: null
  purpose: null
  quantity_or_state: null
  value_role: null
  value_behavior: null
  unit: null
origin:
  kind: measured | estimated | calculated | transformed | manual | external | unknown
  source_or_device: null
  method_or_transformation: null
  inputs: []
context:
  physical_location: null
  mechanical_location: null
  hydraulic_location: null
  reference_frame_or_datum: null
timing:
  clock_or_time_reference: null
  delay_or_synchronization: null
data_flow:
  provider: null
  consumer: null
  telemetry: null
uncertainty:
  model: null
  parameters_or_signals: []
control_context:
  function_or_advisor: null
  objective_limit_incident_or_procedure: null
assumptions: []
missing_information: []
clarification_requirements: []
```

The sketch is complete when `clarification_requirements` is empty and the known information is
sufficient to distinguish the intended entities and relations. `missing_information` may retain
non-blocking details that the user chose not to model.
