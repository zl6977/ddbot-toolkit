# DWIS intent clarification guide

Use this guide to understand a DWIS configuration well enough to model it. It covers signals and
data points, limits, procedures, advice, functions, fluids, and hydraulic or mechanical structures.
It is a dialogue guide, not a questionnaire to present in full and not a post-generation validation
list.

## Mode boundary

Follow the operating mode already selected by `SKILL.md`.

- In `interactive` mode, clarify only unresolved choices that can change the graph or ontology
  grounding.
- In `non-interactive` mode, never turn this guide into questions or pause for confirmation. Extract
  the strongest supported intent, omit unsupported optional structure, record useful missing
  information, and make only indispensable conservative assumptions before continuing to generation
  and validation.

## Dialogue method

Maintain a working intent sketch throughout the conversation. For each field, track one of:
`known`, `assumed`, `not_applicable`, or `unknown`.

1. Extract everything already stated or available in an existing CONFIG.
2. Identify what the user is building. A request may activate more than one branch below.
3. Ask core identity questions first: meaning, value, location, hierarchy, or topology. Ask context
   questions such as origin, state, provider, or instrument afterward.
4. When an answer activates a dependent detail, follow that branch. For example, a measured signal
   may require its instrument, while an uncertainty model may require its parameters.
5. Ask one coherent group of high-impact questions per turn, normally no more than three. Update the
   sketch after every answer and never repeat a resolved question.
6. Stop eliciting when every graph-changing choice is known, accepted as an assumption, or explicitly
   not applicable.

The labels below express clarification priority, not validation severity:

- **Direct**: ask plainly when the item is applicable, unresolved, and needed to choose entities or
  relations.
- **Light**: mention briefly when the detail is likely relevant, but do not block on it unless the
  user's stated goal requires it.

Ask in plain engineering language. When a fixed candidate set is useful, present readable choices
rather than expecting the user to know ontology identifiers. Preserve the selected meaning in the
intent sketch; resolve the exact identifier during ontology grounding.

## Non-interactive interpretation

When `SKILL.md` selects non-interactive mode, classify the supplied description once and continue:

- Record an explicitly stated fact as `known`.
- Record an absent optional detail as `unknown` and add it to `missing_information` only when useful.
- Omit optional entities and relations that the description does not support.
- When a missing detail is indispensable, select the most conservative interpretation supported by
  the description, ontology, and retrieved examples, then record it as `assumed` and in
  `assumptions`.
- Do not leave `clarification_requirements` as blockers and do not ask the user questions.

## What is being modelled?

Route the request through every relevant branch:

- signal or data point;
- limit or threshold;
- procedure or step;
- advice or recommendation;
- function or controller;
- fluid or drilling mud;
- hydraulic network;
- mechanical system or drill string.

For an existing CONFIG, infer the active branches from the file and ask only about the requested
change or ambiguous existing semantics.

## Signal or data point

- **Quantity — Direct:** What measurable quantity, operational state, command, status, or other
  concept does the value represent?
- **Value — Direct:** What concrete or dynamic value does it carry? Is a unit required? Is it
  continuous, discrete, Boolean, categorical, static, or dynamic?
- **Location — Direct when location-dependent:** Where is it physically, mechanically, or
  hydraulically located, and what depth, position, pressure, temperature, frame, or datum is it
  referenced to?
- **Hydraulic placement — Direct when hydraulic:** Which hydraulic element contains it? Capture both
  the hydraulic location and the represented quantity when those are part of the intent.
- **Origin — Direct:** Is it measured, estimated, calculated, transformed, manually entered, or
  provided by another system? If transformed or calculated, which inputs and method produce it?
- **Provider — Direct when externally provided:** What kind of organization or internal service
  provides it? Useful candidates include drilling contractor, instrumentation company, operating
  company, service company, data-analysis service, and DWIS internal service.
- **Uncertainty — Light unless requested:** Is uncertainty part of the model? Useful model families
  are Gaussian, sensor accuracy/precision, and full-scale/proportion error. When selected, establish
  its required parameters or parameter signals.
- **Instrument — Direct when measured:** Which sensor or device measures it, and does its placement
  or network connection need representation?
- **Data flow and timing — Light:** Who consumes it, how is it transmitted, and do source time,
  acquisition time, sampling, delay, clock, or synchronization matter?

## Limit or threshold

- **Comparison — Direct when it is a comparison limit:** What is compared with the limit, and is the
  intended comparison greater than, smaller than, greater-or-equal, smaller-or-equal, equal,
  different, strictly greater, or strictly smaller? Also establish the represented quantity and
  value when they are part of the intended limit.
- **Incident — Direct when protective:** Which drilling incident or undesired condition does the
  limit guard against?
- **Function — Direct when used for control:** Which controller, advisor, or function consumes or
  implements it?
- **Control-limit type — Direct:** Which kind of limit is intended: annulus pressure, axial load,
  axial velocity, differential pressure, flow rate, pressure, ROP, rotational velocity, string
  pressure, torque, or WOB?
- **Hierarchy — Direct when nested:** Is it a minimum, maximum, recommendation, or another child of a
  broader drilling limit, and what is the parent or controlled subject?
- **Provenance — Light:** Does the limit value come from a measurement, computation, or provider that
  must be represented?

## Procedure or step

- **Hierarchy — Direct:** Is it a procedure, phase, action, task, or implementing procedure
  function? Establish the required parent-child placement.
- **Value — Direct when the step carries data:** What static or dynamic value does the step carry,
  and what does that value mean?
- **State and transition — Direct when relevant:** What activates, completes, permits, or follows the
  step?

## Advice or recommendation

- **Target function — Light:** Which activable function is the advice for?
- **Routing — Direct:** Is it delivered to a DWIS internal service, an ADCS interface, or both?
- **Producer — Direct:** Which advisor or computation unit recommends or produces it?
- **Management context — Light:** Which management feature, objective, constraint, or operating
  concern does it account for?

## Function or controller

- **Objective — Direct, phrased lightly when uncertain:** Which drilling-control objective does it
  implement?
- **Tuning — Direct when modelled:** Does it use PID tuning or calibration parameters, and which
  function owns them?
- **Set point — Direct when controlled:** What set value is routed to the control system?
- **State — Direct:** Which computed state describes the function or procedure?
- **Enablement — Direct when present:** Are allowing and enabling signals paired with their intended
  static values and provider?
- **State signals — Direct when present:** Are armed or alarm signals discrete, and do activated,
  idling, or safe-mode signals describe the intended computed state?

## Fluid or drilling mud

- **Fluid type — Direct:** What kind of fluid is being modelled? If rheological properties are
  required, establish the intended drilling-liquid type.
- **Component — Direct when applicable:** Which fluid component does the property concern?
- **Location — Direct:** At which hydraulic element is the fluid or property located?
- **Rheology — Direct when applicable:** Which rheological-behavior hypothesis or model applies?

## Hydraulic network

- **Topology — Light, becoming Direct when connections are requested:** How do branches, junctions,
  logical elements, topside and downhole networks connect? Which equipment does the hydraulic
  representation describe?
- **Estimation — Light:** Which computation unit produces an estimated hydraulic quantity or state?
- **State — Direct:** Which hydraulic-element state is intended?

## Mechanical system or drill string

- **Connection chain — Direct:** How do the mechanical logical elements connect?
- **Specific type — Light:** Is a more specific component type known than the generic mechanical
  element?
- **State — Direct:** Which mechanical-element state is intended?
- **Motion versus mechanical state — Direct when either appears:** Does the user intend a motion type
  or a mechanical state? Capture the engineering choice without asking the user to reason about
  ontology exclusivity.

## Clarification priority

Across all active branches, ask first about unknowns that select different graph structures:

1. what each principal entity is and what its value or role means;
2. hierarchy, comparison, topology, or connection relationships;
3. measured versus estimated, calculated, transformed, or externally provided origin;
4. required physical, mechanical, hydraulic, or reference location;
5. dependencies, provider/consumer flow, controller or procedure relationships;
6. uncertainty, timing, tuning, and optional descriptive detail.

Do not block generation on a field irrelevant to the request. In interactive mode, do block when
two plausible answers require different entities or relations and the user has not authorized an
assumption. In non-interactive mode, apply the conservative interpretation rule instead.

## Validation-side constraints

Do not ask users to declare parser or ontology mechanics. Exact class membership, datatype
compatibility, type disjointness, functional-property cardinality, graph connectivity, edge
direction, domain/range compatibility, and mutual-exclusion constraints belong to ontology
grounding and validation. Ask only for the engineering meaning needed to choose between valid
models, then let the validator diagnose their formal construction.

Corpus coverage notes are evidence for how strongly to phrase a question, not proof that a relation
is mandatory. Do not invent optional entities merely to reproduce a common corpus pattern.

## Intent sketch

Use this shape as a guide and omit fields that are not applicable. Preserve user terminology until
ontology grounding begins.

```yaml
operation: create | modify | repair
configuration_scope: []  # signal, limit, procedure, advice, function, fluid, hydraulic, mechanical
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
related_objects:
  limit_or_threshold: null
  comparison: null
  incident: null
  procedure_or_step: null
  advice_or_recommendation: null
  function_or_controller: null
  objective: null
  fluid_or_component: null
  hydraulic_topology_or_state: null
  mechanical_connection_or_state: null
assumptions: []
missing_information: []
clarification_requirements: []
```

The sketch is complete when `clarification_requirements` is empty and the known information is
sufficient to distinguish the intended entities and relations. `missing_information` may retain
non-blocking details that the user chose not to model or that non-interactive input did not provide.
