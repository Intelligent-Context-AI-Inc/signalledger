# Atlas Pack Builder Roadmap

## Purpose

This roadmap turns the top-20 source catalog into an execution tracker. It distinguishes what is already safe to claim from what still needs collection, legal review, and quality validation.

## Maturity Labels

- `active_seed`: implemented and used in public-alpha outputs.
- `priority_alpha`: public metadata sources identified; next in line for deeper pack population.
- `baseline_registered`: domain exists in the registry with public source families mapped.
- `private_pack_candidate`: likely valuable for richer private overlays after legal/IP review.

## Top-20 Tracker

| Domain | Public source families | Metadata fields available | Pack maturity | Legal/IP risk | Next collection step |
| --- | --- | --- | --- | --- | --- |
| `financial_services` | SEC EDGAR/XBRL, FINRA notices, Federal Reserve stress scenarios, public dataset cards | regulatory tags, fiscal bounds, sector ratios, source hashes, license/provenance descriptors | `active_seed` | Low for public metadata; medium for private customer overlays | Deepen benchmark and lineage feedback-loop baselines |
| `healthcare_clinical` | NIH/ClinicalTrials.gov metadata, FDA device/drug labels, public benchmark cards | study phase tags, clinical taxonomy tags, de-identification markers, license descriptors | `priority_alpha` | High due health data sensitivity; use metadata only | Build HIPAA-safe structural taxonomy and synthetic-data risk signals |
| `it_software` | CVE/NVD metadata, package registry metadata, benchmark cards, public repo descriptors | dependency families, vulnerability categories, license tags, code benchmark aliases | `priority_alpha` | Medium due OSS license complexity | Add supply-chain and benchmark contamination source rows |
| `legal_regulatory` | CourtListener metadata, public regulatory dockets, contract benchmark cards | jurisdiction tags, document class tags, citation graph hashes, license descriptors | `priority_alpha` | Medium-high due document rights variance | Build jurisdiction-clean taxonomy and citation leakage checks |
| `retail_ecommerce` | Product taxonomy standards, public review dataset cards, commerce benchmark cards | category trees, price bucket tags, review-source descriptors, license fields | `baseline_registered` | Medium due review/content licensing | Build source-mixture and synthetic review contamination profiles |
| `contact_centers` | Public call-center benchmark cards, QA taxonomy references, speech dataset cards | channel tags, intent taxonomy, redaction flags, language coverage | `baseline_registered` | High due conversation sensitivity | Define no-transcript metadata schema and escalation taxonomy |
| `telecom` | FCC public metadata, network benchmark summaries, incident taxonomies | service-class tags, region buckets, outage category tags, license fields | `baseline_registered` | Low-medium | Build network-domain drift and regional compliance tags |
| `media_gaming` | Public media benchmark cards, game telemetry taxonomies, rating board categories | content-class tags, platform tags, safety labels, license descriptors | `baseline_registered` | Medium due content licensing | Add content provenance and benchmark alias registry |
| `manufacturing` | NIST manufacturing references, public defect dataset cards, process taxonomies | process tags, defect categories, sensor metadata descriptors, license fields | `baseline_registered` | Medium for proprietary process metadata | Build defect-lineage and plant-source abstraction tags |
| `pharma_biotech` | FDA labels, PubChem metadata, clinical benchmark cards, public assay descriptors | compound class tags, study-stage tags, safety taxonomy, provenance links | `priority_alpha` | High due regulated claims and trial sensitivity | Build strict evidence taxonomy and publication leakage flags |
| `education` | NCES public metadata, education benchmark cards, curriculum taxonomies | grade bands, subject tags, assessment benchmark aliases, license fields | `baseline_registered` | Medium-high due minors and student privacy | Define student-data exclusion and assessment leakage checks |
| `government` | Data.gov metadata, public procurement taxonomies, public policy datasets | agency tags, public record classes, license descriptors, jurisdiction tags | `baseline_registered` | Medium due jurisdiction and classification boundaries | Build public/private source separation and retention tags |
| `hr_talent` | O*NET metadata, public job taxonomy references, hiring benchmark cards | role taxonomy, seniority bands, skill tags, bias benchmark aliases | `baseline_registered` | High due employment and bias sensitivity | Build fairness-risk metadata schema and protected-class exclusion checks |
| `marketing_advertising` | IAB taxonomies, public ad benchmark cards, campaign metadata schemas | audience class tags, channel tags, brand-safety categories, license fields | `baseline_registered` | Medium-high due audience profiling | Build privacy-safe audience metadata controls |
| `automotive_mobility` | NHTSA metadata, mobility benchmark cards, public sensor dataset cards | scenario tags, vehicle subsystem tags, safety event descriptors, license fields | `baseline_registered` | High for safety-critical claims | Build scenario coverage and simulation-source lineage checks |
| `logistics_supply_chain` | HS code references, port/shipping metadata, public routing benchmark cards | route class tags, shipment category tags, disruption taxonomy, source descriptors | `baseline_registered` | Medium | Build route abstraction and vendor-source provenance tags |
| `energy_utilities` | EIA metadata, NERC categories, grid benchmark cards | asset class tags, demand scenario tags, reliability categories, license fields | `baseline_registered` | High for critical infrastructure | Build critical-infrastructure metadata boundaries |
| `aerospace_defense` | NASA public metadata, FAA categories, public aerospace benchmarks | mission class tags, safety taxonomy, export-control markers, license fields | `baseline_registered` | Very high due export/control boundaries | Build public-only guardrails and export-control exclusion tags |
| `travel_hospitality` | public tourism taxonomies, aviation/hotel benchmark cards, review dataset cards | booking category tags, geography buckets, review-source descriptors, license fields | `baseline_registered` | Medium due review and customer data | Build geography-safe and review-license source profiles |
| `real_estate_proptech` | public parcel metadata references, listing taxonomy cards, housing benchmark summaries | property class tags, geography buckets, listing-source descriptors, license fields | `baseline_registered` | Medium-high due fair housing sensitivity | Build fair-housing risk taxonomy and listing-source boundaries |

## Next Build Sequence

1. Financial Services hardening: improve negative evaluation deltas, benchmark aliases, and lineage-loop signatures.
2. Healthcare/Clinical: build strict privacy-safe structural taxonomy with zero clinical text.
3. Legal/Regulatory: add jurisdiction-clean source descriptors and citation leakage checks.
4. IT/Software: add dependency, CVE, package, and code-benchmark metadata profiles.
5. Pharma/Biotech: add regulated-evidence and assay-metadata source descriptors.

## Quality Bar

A domain pack is not buyer-claimable as "deep" until it has:

- At least six public metadata-only source families.
- A domain-specific compliance/taxonomy section.
- A benchmark alias registry.
- A lineage feedback-loop risk profile.
- No-payload validation tests.
- Legal/IP risk note.
- One sanitized artifact example.
