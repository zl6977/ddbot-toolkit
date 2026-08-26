# DWIS CONFIG format

Use one declaration or relation per line. Blank lines are allowed. Lines beginning with `dwis `
are ignored by the current parser. Lines beginning with `#` are comment annotations and are
ignored by the parser.

## Type declaration

```text
ClassName:instanceId
```

- Resolve `ClassName` against the DWIS ontology.
- Keep `instanceId` non-empty and distinct from ontology class names.
- Multiple compatible classes may type the same instance using separate lines.

## Relation

```text
subjectId PredicateName objectId
```

- Use exactly three whitespace-separated tokens.
- Declare the subject instance.
- Use either a declared instance or a valid ontology class shorthand as the object.
- Resolve `PredicateName` to an ontology object property.

A class shorthand denotes an anonymous object typed by that ontology class. It is not a normal
instance identifier. Quantity shorthands can resolve through the ontology naming convention; for
example, `ForceDrilling` resolves to `ForceDrillingQuantity`:

```text
WOB:wobPoint
wobPoint IsOfMeasurableQuantity ForceDrilling
```

The subject currently has no equivalent shorthand form and must be declared explicitly.

## Minimal example

```text
DynamicDrillingSignal:wobSignal
WOB:wobPoint
wobPoint HasDynamicValue wobSignal
```

## Intent annotation

After validation passes, annotate the CONFIG with the confirmed intent sketch. Place `# intent`
comment lines **directly before the declarations or relations they describe**, not in a single
block at the top of the file. Each annotation line uses the format `# key: value`.

```text
# intent: block velocity limit for auto driller
# quantity: BlockVelocityDrilling
# value_role: recommended maximum (ROP limit)
# value_behavior: continuous, dynamic
DrillingSignal:va_bos_rmax
DynamicDrillingSignal:va_bos_rmax
RecommendedMaximum:va_bos_rmax#01
ROPLimit:va_bos_rmax#01
ContinuousDataType:va_bos_rmax#01
va_bos_rmax#01 HasDynamicValue va_bos_rmax
va_bos_rmax#01 IsOfMeasurableQuantity BlockVelocityDrilling
# location: bottom of string
BottomOfStringReferenceLocation:bos#01
va_bos_rmax#01 IsPhysicallyLocatedAt bos#01
# objective: stable drilling
# consumer: ADCS interface
# origin: D-WIS advice composer
StableDrillingObjective:stableDrilling
ControllerFunction:autoDriller
va_bos_rmax#01 IsMaximumLimitFor autoDriller
DWISAdviceComposer:dWISComposer
DWISADCSInterface:aDCSStandardInterface
va_bos_rmax#01 IsProvidedBy dWISComposer
va_bos_rmax#01 IsProvidedTo aDCSStandardInterface
```

Rules:

- One annotation line per key intent field: `# key: value`.
- Place each annotation immediately before the lines it describes. Group related annotations
  together above the group of declarations or relations they qualify.
- Omit fields that are not applicable to the signal.
- Use plain engineering language, not ontology identifiers, for the `value` part when it
  improves readability (e.g., `bottom of string` rather than `BottomOfStringReferenceLocation`).
- The annotation is documentation; it does not affect validation. The parser ignores `#`
  lines.
- Revalidate the complete file (including the annotation) before delivery.

Always use `uv run <script-path> --ontology <ontology-path> validate` to establish whether a concrete
configuration is valid. Syntax alone does not establish semantic consistency or graph
connectivity.
