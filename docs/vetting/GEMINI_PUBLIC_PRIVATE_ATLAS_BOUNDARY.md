# Gemini Vet Packet: Public/Private Atlas Boundary

You are acting as an independent AI product security and enterprise risk reviewer.

## Review Goal

Assess whether the current public-facing ECL Trainer / Intelligent Context Atlas materials preserve the product moat while staying credible to enterprise buyers.

The product boundary is:

- public package may expose domain IDs, toggle behavior, public-alpha source references, sample records, aggregate reports, and local GitHub Action behavior
- private/proprietary Atlas rows, richer matching logic, scoring heuristics, and source expansion strategy must not be exposed in a way that lets competitors reconstruct the full solution
- marketing copy must not overclaim full top-20 deep intelligence until those private packs are populated

## Materials To Review

- `docs/INTELLIGENT_CONTEXT_ATLAS.md`
- `docs/INTELLIGENT_CONTEXT_ATLAS_COLLECTION.md`
- `docs/GITHUB_ACTION.md`
- `docs/NO_PAYLOAD_POLICY.md`
- `docs/SUPPLY_CHAIN_EVIDENCE.md`
- `docs/GOLDEN_DEMO.md`
- `examples/ecl_records/README.md`
- `examples/ecl_records/financial-services-atlas-seed-ledger.sample.json`
- `atlas_sources/domain_extensions/top20_public_seed_sources.json`
- `atlas_sources/domain_extensions/priority_deep_seed_sources.json`
- `atlas_sources/financial_services/financial_structure_sources.json`
- `.github/actions/ecl-trainer-scan/action.yml`
- `Dockerfile.ecl-trainer`

## Questions To Answer

1. Does any public file expose too much of the proprietary Atlas strategy?
2. Does the public sample reveal enough to copy the product, or only enough to prove the no-payload architecture?
3. Are we honest about current coverage: Financial Services deep, priority packs partially deep, remaining domains registered/baseline?
4. Is the “local-only, no SaaS, no upload” promise clear and defensible?
5. Are there claims that sound like legal compliance guarantees rather than evidence-support artifacts?
6. Are GitHub Action installation steps specific enough for a platform engineer to adopt?
7. What should be moved from public docs into a private internal operating manual?

## Expected Output Format

Use this format:

```text
Finding:
Risk level: Critical | High | Medium | Low
Audience affected: Buyer | Auditor | Engineer | Competitor | Legal
Location:
Why it matters:
Recommended wording or action:
```

## Review Standard

Be commercially skeptical. Protect the moat, but do not make the public artifact so vague that a buyer cannot understand or trust it.

