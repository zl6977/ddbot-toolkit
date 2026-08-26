# Example corpus

`assets/dwis-config-examples.jsonl` is the shared retrieval corpus used by both the agent
and `ddbot examples`. Each non-empty line is one independent JSON object.

## Keyword retrieval

Build the query from discriminative intent-sketch values rather than a full sentence. Start with
three to six terms for the core concept, value role, origin, and location or equipment. Include only
known and applicable values. Search transformation, uncertainty, timing, or other secondary
patterns separately when combining everything would dilute the core match.

Search this JSONL explicitly with `ddbot examples` so the agent receives ranked, structured
matches:

```bash
uv run <script-path> examples \
  "standpipe pressure measured sensor" \
  --corpus <example-corpus-path> \
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

Search the JSONL directly when inspecting provenance or accessing fields that the CLI result does
not expose. Limit direct searches to a few matching records; never read the whole corpus into
context.

Useful direct searches include:

```bash
rg -i -m 5 'standpipe pressure' <example-corpus-path>
rg -n -m 5 'HasDynamicValue' <example-corpus-path>
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
