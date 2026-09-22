# DWIS CONFIG format

Use one declaration, relation, or datatype attribute per line. Blank lines are allowed. Lines
beginning with `#` are comment annotations and are ignored by the parser. A trailing semicolon is
optional, and exact duplicate semantic lines are reduced to their first occurrence. Any other
nonblank line, including a legacy `dwis ...` line, is invalid.

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
instance identifier. The shorthand must be the exact name of a class in the loaded ontology; the
validator does not append `Quantity` or otherwise expand aliases:

```text
WOB:wobPoint
wobPoint IsOfMeasurableQuantity ForceDrillingQuantity
```

The subject currently has no equivalent shorthand form and must be declared explicitly.

## Datatype attribute

```text
instanceId.DataPropertyName = Literal
```

- Declare `instanceId` before assigning the attribute.
- Resolve `DataPropertyName` to an ontology datatype property, not an object property.
- Match the property's effective domain and range. Supported ranges are `xsd:string`,
  `xsd:boolean`, `xsd:integer`, `xsd:int`, `xsd:decimal`, `xsd:float`, `xsd:double`, and
  `xsd:dateTime`.
- Quote strings and ISO 8601 date-time values with JSON-compatible double quotes. Write booleans as
  `true` or `false`; write numeric values without quotes.
- A functional datatype property may have only one distinct value for an instance.

```text
DataProvider:provider
provider.ProviderName = "Acme Drilling"
```

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
va_bos_rmax#01 IsOfMeasurableQuantity BlockVelocityDrillingQuantity
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
