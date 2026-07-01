# Intelligent Context Atlas Collection

The Atlas collector pipeline builds the local Option B seed index from public structural evidence only.

It collects metadata such as dataset names, versions, token-count estimates, source-mixture categories, filtering methods, benchmark names, regulatory categories, taxonomy tags, reference hashes, and provenance links. It does not collect raw corpora, raw filings, prompt examples, dataset rows, embeddings, token sequences, model weights, raw diffs, or notebook cells.

## Local Build

```bash
python -m atlas_pipeline.build_atlas \
  --sources-root atlas_sources \
  --output-path atlas_artifacts/option_b_alpha/intelligent-context-atlas.duckdb
```

The output DuckDB file is a local runtime artifact. `Dockerfile.ecl-trainer` runs this build during image creation, so the GitHub Action can query the baked Atlas without a SaaS account, network call, or dataset upload.

## Current Public Seed Scope

- Global core: public open-science structural metadata families.
- Financial Services: public taxonomy, regulatory category, and financial-system reference families.
- Priority expansion packs: public structural evidence families for Healthcare/Clinical, Legal/Regulatory, IT/Software, and Pharma/Biotech.
- Other top-20 domains: representative metadata-only public structural references used to exercise toggles, passport boundaries, and local build behavior.

The public alpha build contains 65 source records total. This is enough to exercise top-20 toggles and passport boundaries locally, while still leaving richer proprietary domain rows out of public examples and source distributions.

Priority deep-pack quality floor:

- Financial Services: at least 6 structural sources.
- Healthcare/Clinical: at least 6 structural sources.
- Legal/Regulatory: at least 6 structural sources.
- IT/Software: at least 6 structural sources.
- Pharma/Biotech: at least 6 structural sources.

Financial Services remains the first flagship deep validator pack. Healthcare/Clinical, Legal/Regulatory, IT/Software, and Pharma/Biotech now have deeper public-alpha structural evidence and are ready for private overlay expansion.

## Public/Private Boundary

Public materials describe schema shape, local build behavior, source counts, and metadata-only guardrails. Private operating manuals own target endpoint lists, collector expansion priorities, weighting heuristics, customer-specific overlay rows, and production correlation coefficients.

Public examples must be treated as schema validation fixtures. They are not production Atlas rows and must not be represented as proprietary baseline coefficients.

## Guardrails

Every source record is validated with `NoPayloadValidator` before it can be written into the atlas. The collector also rejects long non-hash text fields so a source manifest cannot smuggle raw document excerpts into the seed index.

The package exposes aggregate shield, blueprint, and passport behavior. It does not expose a public row browser for the seed records.
