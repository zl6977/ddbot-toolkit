# DWIS CONFIG format

Use one declaration or relation per line. Blank lines are allowed. Lines beginning with `dwis `
are ignored by the current parser.

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

Always use `uv run <skill-root>/scripts/ddbot.py validate` to establish whether a concrete
configuration is valid. Syntax alone does not establish semantic consistency or graph
connectivity.
