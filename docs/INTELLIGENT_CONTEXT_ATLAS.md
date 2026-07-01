# Intelligent Context Atlas

The Intelligent Context Atlas is the local Option B seed asset for ECL Learning Ledger. It is built from metadata-only source manifests, packaged into the Docker image as a read-only DuckDB index, and queried by guarded oracle APIs only.

## Architecture

- Global structural core: always enabled and not user-disableable.
- Domain extensions: top-20 industry packs controlled by toggles.
- Flagship deep domain: `financial_services`.
- Global cross-industry telemetry tracks universal structural failure patterns across all top-20 enterprise domains.
- Financial Services is the first deep active validator pack mapped to public financial taxonomy and regulatory evidence.
- Healthcare/Clinical, Legal/Regulatory, IT/Software, and Pharma/Biotech are priority public-alpha expansion packs.
- The remaining domains are registered public-alpha baseline packs and stay ready for deeper private overlays.
- Public alpha seed records demonstrate metadata-only operation; private customer packs and richer matching rows are not exposed through public APIs or examples.

## Top-20 Domain IDs

- `financial_services`
- `healthcare_clinical`
- `it_software`
- `legal_regulatory`
- `retail_ecommerce`
- `contact_centers`
- `telecom`
- `media_gaming`
- `manufacturing`
- `pharma_biotech`
- `education`
- `government`
- `hr_talent`
- `marketing_advertising`
- `automotive_mobility`
- `logistics_supply_chain`
- `energy_utilities`
- `aerospace_defense`
- `travel_hospitality`
- `real_estate_proptech`

## Toggle Modes

- `auto`: run the global core and infer one domain extension from safe manifest metadata.
- `explicit`: run the global core and only the requested domain extensions.
- `core_only`: run only the global structural core.

The default is `auto`. If no safe domain can be inferred, the oracle falls back to `core_only` and reports `skipped_no_domain`.

## CLI

```bash
ecl-trainer oracle shield \
  --manifest ecl-trainer.manifest.json \
  --domain-selection-mode auto

ecl-trainer oracle blueprint \
  --manifest ecl-trainer.manifest.json \
  --target target-metrics.json \
  --domain financial_services

ecl-trainer oracle passport \
  --ledger-path .ecl-trainer/events.jsonl \
  --domain financial_services
```

## Manifest Boundary

Oracle manifests must be metadata-only. They may contain hashes, short controlled tags, numeric distributions, and structural metadata. They must not contain raw dataset rows, prompts, completions, raw diffs, token sequences, embeddings, model weights, notebook cells, secrets, or local paths.

## Container Build

`Dockerfile.ecl-trainer` builds `/opt/ecl-trainer/atlas/intelligent-context-atlas.duckdb` with:

```bash
python -m atlas_pipeline.build_atlas \
  --sources-root atlas_sources \
  --output-path /opt/ecl-trainer/atlas/intelligent-context-atlas.duckdb
```

The action exposes only aggregate Atlas source counts in PR artifacts. It does not expose a seed row browser.

The public alpha Atlas currently builds 65 source records: 3 global-core records, 8 Financial Services records, 38 baseline records covering the other 19 domains, and 16 additional priority-pack records for Healthcare/Clinical, Legal/Regulatory, IT/Software, and Pharma/Biotech.

Quality floor for the first public-alpha expansion packs: Financial Services, Healthcare/Clinical, Legal/Regulatory, IT/Software, and Pharma/Biotech each have at least six metadata-only structural sources. Financial Services is the first flagship deep-compliance deployment module. The remaining 15 domains have public-alpha baseline coverage and are ready for deeper private packs.

## Lifecycle Freshness

The Atlas includes an `ecl_atlas_metadata` birthmark with a version tag, UTC compile timestamp, supported-domain mask, and deterministic signature. `ecl-trainer lifecycle check` reads that local metadata and emits `lifecycle-report.json`; GitHub PR reports include the same status in the PR comment.

Air-gapped updates use `ecl-trainer lifecycle apply-patch --patch-archive PATH`. Patch archives must be `.tar.gz` files with a signed metadata manifest, declared member hashes, allowlisted JSON members, and bounded operations only; arbitrary SQL and raw payload members are rejected.

The lifecycle layer must remain local-only, metadata-only, non-blocking, and compatible with air-gapped deployment. The protocol details are tracked in `docs/DETERMINISTIC_FRESHNESS_PROTOCOL_PLAN.md`.
