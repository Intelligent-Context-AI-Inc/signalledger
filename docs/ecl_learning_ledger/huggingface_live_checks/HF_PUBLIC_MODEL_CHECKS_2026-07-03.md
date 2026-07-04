# Hugging Face Live Public Catalog Checks

Captured: `2026-07-03T20:00:50Z`

## Scope

SignalLedger ran a zero-payload metadata check against two public Hugging Face model catalog entries. The collector used public API metadata only and did not download repository files, model weights, dataset rows, README bodies, prompts, completions, embeddings, token sequences, checkpoint bytes, or private customer data.

Checked entries:

- `Qwen/Qwen3-8B`
- `mistralai/Mistral-7B-Instruct-v0.3`

## No-Payload Evidence

- raw_dataset_rows_downloaded: `false`
- raw_model_files_downloaded: `false`
- weights_or_checkpoints_downloaded: `false`
- readme_or_card_body_downloaded: `false`
- sample_prompts_or_outputs_retained: `false`
- spaces_or_downstream_apps_retained: `false`
- private_customer_data_touched: `false`

Excluded from stored evidence:

- README / model-card body
- widgetData sample prompts or outputs
- spaces list
- config.tokenizer_config.chat_template
- extra_gated_prompt full license text
- extra_gated_fields collection form details
- raw model, tokenizer, checkpoint, safetensor, PyTorch, TensorFlow, GGUF, or dataset files

## Results Matrix

| Public catalog entry | Status | License | Base model | Training-data reference | Eval metadata | Language metadata | Key gaps |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [Qwen/Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B) | `watch` | `present` | `present` | `missing` | `tag_only` | `missing` | LANGUAGE_METADATA_GAP, TRAINING_DATA_PROVENANCE_GAP, EVAL_RESULTS_TAG_WITHOUT_MODEL_INDEX |
| [mistralai/Mistral-7B-Instruct-v0.3](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3) | `review_recommended` | `present` | `present` | `missing` | `missing` | `missing` | LICENSE_FILE_NOT_LISTED, PIPELINE_TAG_MISSING, LANGUAGE_METADATA_GAP, TRAINING_DATA_PROVENANCE_GAP, EVAL_METADATA_GAP |

## Per-Entry Findings

### Qwen/Qwen3-8B

- Repository: [Qwen/Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B)
- Status: `watch`
- Metadata fingerprint: `01319d97e6c5dd4e6c7273ae0441d5b2b0b7627ba93ca06c12cc269cad4cae33`
- Last modified: `2025-07-26T03:49:13.000Z`
- Gated: `False`; private: `False`; disabled: `False`
- License metadata: `apache-2.0`
- Repository file bodies downloaded: `false`; model artifacts downloaded: `false`

Findings:

- `medium` `LANGUAGE_METADATA_GAP`: No machine-readable language field/tag was visible. Recommendation: Add language metadata in cardData or tags.
- `medium` `TRAINING_DATA_PROVENANCE_GAP`: No machine-readable dataset/training-data reference was visible. Recommendation: Add dataset references, source-mixture descriptors, or a provenance summary that avoids raw payload.
- `medium` `EVAL_RESULTS_TAG_WITHOUT_MODEL_INDEX`: The repo has an eval-results tag but no model-index entries in API metadata. Recommendation: Add model-index evaluation entries or a structured evaluation summary.
- `info` `WIDGET_DATA_EXCLUDED`: HF API returned widgetData; collector deliberately excluded sample prompts/outputs from stored evidence. Recommendation: Keep widgetData outside compliance artifacts or store only an exclusion assertion.
- `info` `CHAT_TEMPLATE_EXCLUDED`: HF API returned tokenizer chat_template; collector excluded the raw template from evidence. Recommendation: Store only a hash or presence flag if chat-template governance is needed.

Recommended portable indicators:

- `payload_policy`: `zero_payload_metadata_only_passed`
- `license`: `present`
- `license_file`: `listed`
- `base_model_lineage`: `present`
- `training_data_reference`: `missing`
- `eval_metadata`: `tag_only`
- `language_metadata`: `missing`
- `review_status`: `watch`

### mistralai/Mistral-7B-Instruct-v0.3

- Repository: [mistralai/Mistral-7B-Instruct-v0.3](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3)
- Status: `review_recommended`
- Metadata fingerprint: `fb8edeec7e6c759dd70dfe10c6531e695b8e79e3e69dee76f881cab3ecfe3eb0`
- Last modified: `2025-12-03T12:13:48.000Z`
- Gated: `False`; private: `False`; disabled: `False`
- License metadata: `apache-2.0`
- Repository file bodies downloaded: `false`; model artifacts downloaded: `false`

Findings:

- `medium` `LICENSE_FILE_NOT_LISTED`: License metadata is present, but no LICENSE/LICENSE.md sibling was visible in repository metadata. Recommendation: Add or expose a license file alongside the model card.
- `medium` `PIPELINE_TAG_MISSING`: No machine-readable text-generation pipeline tag was visible. Recommendation: Add pipeline_tag: text-generation or equivalent model-card metadata.
- `medium` `LANGUAGE_METADATA_GAP`: No machine-readable language field/tag was visible. Recommendation: Add language metadata in cardData or tags.
- `medium` `TRAINING_DATA_PROVENANCE_GAP`: No machine-readable dataset/training-data reference was visible. Recommendation: Add dataset references, source-mixture descriptors, or a provenance summary that avoids raw payload.
- `medium` `EVAL_METADATA_GAP`: No eval-results tag or model-index entries were visible. Recommendation: Add structured eval summary metadata, with benchmark names and verification status where available.
- `info` `CHAT_TEMPLATE_EXCLUDED`: HF API returned tokenizer chat_template; collector excluded the raw template from evidence. Recommendation: Store only a hash or presence flag if chat-template governance is needed.

Recommended portable indicators:

- `payload_policy`: `zero_payload_metadata_only_passed`
- `license`: `present`
- `license_file`: `not_listed`
- `base_model_lineage`: `present`
- `training_data_reference`: `missing`
- `eval_metadata`: `missing`
- `language_metadata`: `missing`
- `review_status`: `review_recommended`

## Partnership Framing

This is the exact wedge to show Hugging Face: we can run live, zero-payload checks on public Hub catalog metadata; produce an evidence bundle and portable indicators; then scale the same approach across the Hub catalog and into joint enterprise customer workflows. The result supports compliance review and catalog governance, but it is not a legal certification and does not claim Hugging Face endorsement.

## Pain Made Visible

The sample shows the practical platform pain:

- Even high-visibility public model pages can have missing or tag-only machine-readable trust metadata.
- The gaps are detectable without downloading model weights, raw datasets, prompts, completions, embeddings, token sequences, or README bodies.
- The same gap classes matter to enterprise buyers, platform governance teams, and downstream model builders: provenance, license visibility, language coverage, eval detail, and structural release metadata.
- Manual review does not scale across the Hub catalog; a no-payload metadata collector can turn catalog inconsistency into a prioritized cleanup and trust-indicator workflow.

Suggested meeting line:

> Here is what we found from two public catalog entries without touching raw payloads. Imagine this running across the Hub catalog and inside joint enterprise customer workflows.

SignalLedger is built on Intelligent Context AI's broader 12+ patent context-engineering portfolio: governed context boundaries, metadata-only evidence receipts, no-payload learning loops, and context-aware release gates.

## Machine-Readable Evidence

- JSON bundle: `docs/ecl_learning_ledger/huggingface_live_checks/hf_public_model_checks_2026-07-03.json`
- Bundle fingerprint: `77ec962b50470139d3e77d67122d3b13edcab9a30dda0e3672a77ac031a7fe14`
