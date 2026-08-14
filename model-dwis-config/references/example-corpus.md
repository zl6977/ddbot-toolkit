# Example corpus

`assets/dwis-config-examples.jsonl` is the shared retrieval corpus used by both the Agent
and `ddbot motif`. Each non-empty line is one independent JSON object.

## Keyword retrieval

Build the query from discriminative intent-sketch values rather than a full sentence. Start with
three to six terms for the core concept, value role, origin, and location or equipment. Include only
known and applicable values. Search transformation, uncertainty, timing, or other secondary
patterns separately when combining everything would dilute the core match.

Search this JSONL explicitly with `ddbot motif` so the Agent receives ranked, structured matches:

```bash
uv run <skill-root>/scripts/ddbot.py motif \
  "standpipe pressure measured sensor" \
  --library <skill-root>/assets/dwis-config-examples.jsonl \
  --limit 5
```

If the first result set is empty or weak, perform another search using ontology names, an
engineering synonym, or a more specific origin/location term. Avoid broad single-word queries when
the intent sketch contains better discriminators. For an additional concern, run a separate query,
for example `"Gaussian uncertainty pressure measurement"`, and combine only compatible patterns
from the two result sets.

Review `descriptions`, `intent_sketch`, and asserted `dwis_config` in the highest-ranked records.
Reuse only relevant modelling patterns. Do not treat retrieval rank as proof that an example matches
the user's intent.

## Direct inspection

Search the JSONL directly only when inspecting provenance or fields that the CLI result does not
expose. Limit direct searches to a few matching records; never read the whole corpus into context.

Useful direct searches include:

```bash
rg -i -m 5 'standpipe pressure' <skill-root>/assets/dwis-config-examples.jsonl
rg -n -m 5 'HasDynamicValue' <skill-root>/assets/dwis-config-examples.jsonl
```

## Record fields

- `sample_id`: stable record identifier.
- `lineage`: source provenance.
- `descriptions`: natural-language summaries used for retrieval.
- `intent_sketch`: normalized modelling intents used for retrieval.
- `dwis_config`: asserted DWIS CONFIG example.
- `inferred_dwis_config`: derived statements; do not copy them as asserted configuration.
- `raw_code`: original source representation when available.
- `question_list`: example questions associated with individual intents.
- `rdf_ttl` and `inferred_rdf_ttl`: derived reasoning representations, not deliverables.

Treat every record as an example rather than an authoritative template. Reuse only the declarations
and relations relevant to the current request, then validate the resulting DWIS CONFIG.
