---
name: model-dwis-config
description: Guide a user through multi-turn clarification of a drilling signal, turn the completed description into an intent sketch, and generate, modify, validate, or repair an ontology-grounded DWIS CONFIG. Use for DWIS signal modelling, existing CONFIG review, or questions that require resolving DWIS classes, predicates, graph constraints, and modelling patterns.
---

# Model DWIS Config

Produce a validated DWIS CONFIG through this workflow:

```text
collect user inputs
  → summarize and confirm the intent sketch
  → generate a DWIS CONFIG draft
  → validate and repair the draft
  → deliver the final DWIS CONFIG
```

Keep conversation, decisions, and file edits in the calling agent. Use DDBot Toolkit for ontology
grounding, example retrieval, and validation. Treat RDF as an internal derived representation, not
the deliverable.

## 0. Check the runtime environment

Read [the environment guide](references/environment.md) and run its preflight once per session
before starting CLI-dependent work. Confirm that the sandbox can execute `uv`, use Python 3.11 or
newer, read the bundled ontology and example corpus, and write both its environment/cache and the
requested output location.

Do not repeatedly run the preflight after it succeeds. If it fails, report the failed capability
and follow the guide's recovery path; never claim that ontology grounding, retrieval, or validation
ran when the sandbox could not execute it. The toolkit is offline after its Python environment is
available, but the first `uv` invocation may require network access to obtain Python or dependencies.

## 1. Collect user inputs

Read [the intent checklist](references/intent_checklist.md) before eliciting or interpreting a signal
description. Build the description over as many dialogue turns as needed.

- Preserve facts the user already supplied; never ask for them again.
- Ask only questions whose answers can change the graph, ontology type, or required relation.
- Ask one small, coherent group of questions per turn. Use plain engineering language, not ontology
  identifiers.
- Prioritize the signal's meaning, value role, origin, and relevant context. Apply conditional parts
  of the checklist only when the signal needs them.
- Update the working intent after every answer. Briefly reflect the new understanding when useful.
- Record an explicit assumption only when it is safe and the user accepts it. Keep unresolved
  structural choices as clarification requirements.

For an existing CONFIG, initialize the working intent from the file and ask only about the requested
change or ambiguous existing semantics.

## 2. Summarize and confirm the intent sketch

Convert the completed user input into the structure defined in the intent checklist. Keep the
user's terminology and distinguish:

- stated facts;
- accepted assumptions;
- information that is not applicable;
- unresolved clarification requirements.

Present the concise intent sketch to the user for confirmation before generation. If the user has
already confirmed the same structured intent in the current turn, do not ask again. Do not proceed
while a clarification requirement would materially change the configuration.

## 3. Generate a DWIS CONFIG draft

Use the intent sketch—not the raw conversation—as the generation input.

1. Resolve `<skill-root>` as the directory containing this `SKILL.md`.
2. Ground uncertain domain terms with ontology search:

   ```bash
   uv run <skill-root>/scripts/ddbot.py ontology "standpipe pressure" --limit 10
   uv run <skill-root>/scripts/ddbot.py ontology "physical location" --kind property
   ```

3. Extract a compact keyword query from the intent sketch. Start with three to six discriminative
   terms covering the core concept, value role, origin, and location or equipment. Omit unknown and
   generic terms. Search optional concerns such as transformation or uncertainty separately when
   one query would mix unrelated patterns.
4. Search the shared example corpus before composing the CONFIG:

   ```bash
   uv run <skill-root>/scripts/ddbot.py motif \
     "standpipe pressure measured sensor" \
     --library <skill-root>/assets/dwis-config-examples.jsonl \
     --limit 5
   ```

   If results are empty or semantically weak, refine the keywords with ontology names, synonyms, or
   a more specific location/origin term and search again. Run a second focused search such as
   `"Gaussian uncertainty pressure measurement"` when the intent contains an additional modelling
   concern. Follow
   [the corpus guide](references/example-corpus.md).

5. Review the best matching examples before generation. Compare their `descriptions`,
   `intent_sketch`, and asserted `dwis_config`; identify only the entities and relations relevant to
   the confirmed intent sketch. Inspect the JSONL directly only when a required raw field or
   provenance is absent from CLI output. Never load the complete corpus into context.

6. Compose the smallest configuration that expresses the sketch. Follow
   [the DWIS CONFIG format](references/dwis-config-format.md). Preserve valid identifiers when
   modifying an existing file. Save this candidate as the DWIS CONFIG draft. Do not present the
   draft as a completed DWIS CONFIG.

## 4. Validate and repair the draft

Treat validation and repair as a separate gate between the draft and the final DWIS CONFIG.

1. Validate the draft:

   ```bash
   uv run <skill-root>/scripts/ddbot.py validate path/to/config.dwis
   ```

2. Review `hard_errors`, `repair_suggestions`, and `soft_comments`. Trace each finding to the draft
   and the confirmed intent sketch.
3. Repair every hard error with the smallest change that preserves the confirmed intent. Do not add
   entities or relations merely to silence the validator.
4. Revalidate after every material repair. Repeat the validate → inspect → repair cycle until no
   hard errors remain.
5. If a repair requires an engineering choice not represented in the confirmed intent sketch, stop
   and ask the user. Update and reconfirm the sketch before revising the draft.
6. Promote the draft to the final DWIS CONFIG only when the validation result reports `valid: true`.
   Keep remaining soft comments and accepted assumptions for the final summary.

## 5. Deliver the final DWIS CONFIG

Return the final CONFIG path, a concise intent summary, and hard-error and soft-comment counts. State
any accepted assumptions that affect interpretation. Never deliver an unvalidated draft, invent
ontology terms, silently resolve a structural ambiguity, copy an entire retrieved example, or claim
that validation proves unstated engineering intent.

Invoke the bundled `scripts/ddbot.py` entry point rather than assuming that a global `ddbot`
command or separately installed Python package exists.
