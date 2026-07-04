# AI CI/CD Release Gate Positioning

Traditional CI/CD tells an LLM team whether code, tests, and deployment mechanics
passed. LLM release gates tell the team whether a candidate model, RAG pipeline,
or agent behavior stayed inside acceptable quality, cost, latency, safety, and
drift bounds.

SignalLedger / ECL Trainer lives one step earlier.

## Category Position

Post-build LLM release gates ask:

> Did the candidate model or RAG pipeline regress?

SignalLedger asks:

> Are we about to train, refresh, or evaluate on a risky data mixture before
> compute is spent?

This makes SignalLedger an upstream training-data release gate. It complements
baseline evals, drift detection, shadow validation, and cost/latency gates; it
does not replace them.

## Product Implications

### 1. Say Where SignalLedger Runs

SignalLedger should be described as a pre-training and pre-refresh gate:

- before fine-tuning;
- before continued pretraining;
- before RAG corpus refresh;
- before model-card or dataset-card publication;
- before expensive eval or shadow deployment.

Recommended line:

> Eval gates catch bad model behavior late. SignalLedger catches risky training
> signals early.

### 2. Add The Eval Baseline Bridge

SignalLedger already records metadata-only evaluation outcomes. The roadmap
should make this explicit:

- link dataset fingerprints, source-mixture metadata, lineage IDs, and schema
  hashes to later eval outcomes;
- version eval suites and baseline summaries as metadata-only ledger events;
- compare a proposed training-data PR against prior local ledger history;
- produce a future "expected eval risk" score once enough customer-local history
  exists.

Safe current claim:

> SignalLedger records the evidence needed to correlate training-data structure
> with later eval behavior.

Avoid current claim:

> SignalLedger guarantees model performance prediction.

### 3. Use Training-Data Release Gate Language

Preferred phrases:

- local training-data release gate;
- upstream AI CI/CD gate;
- pre-flight shield for training-data PRs;
- metadata-only gate before GPU spend;
- hash-chained evidence for training-data changes.

Avoid phrases that overclaim:

- model quality guarantee;
- compliance certification;
- dataset legality approval;
- automatic model safety approval.

### 4. Emphasize Local / Offline / No Upload

The core buyer proof is not just risk scoring. It is the trust boundary:

- no SaaS account required;
- no dataset upload;
- no raw payload;
- no prompt/completion capture;
- no embeddings, token sequences, model weights, raw diffs, or notebook cells;
- local reports, local ledger, local compliance passport.

Recommended line:

> The gate runs where the PR runs. The evidence stays local.

### 5. Preserve Progressive Policy Modes

LLM teams will bypass a gate that blocks too much too soon. The recommended
rollout should remain:

1. `report_only`: learn the signal without blocking.
2. `warn`: require reviewer attention.
3. `block_on_payload_violation`: fail closed when raw-payload risk appears.
4. `block_on_high_risk`: block selected high-risk structural findings after
   local tuning.

Recommended line:

> Start by measuring. Then warn. Then block the failures your team trusts.

## Landing-Page Bridge Copy

> Traditional LLM release gates ask whether a candidate model regressed.
> SignalLedger asks whether the training-data change is structurally risky
> before the candidate model exists.

> Baseline evals, drift detection, and shadow validation are still necessary.
> SignalLedger gives those gates a local, hash-chained history of what changed
> upstream.

## Roadmap Bridge

The stronger future product is a predictive local ledger layer:

- local teams keep their private event history;
- SignalLedger learns from metadata-only patterns and evaluation deltas;
- aggregate learning can happen only through opt-in, privacy-preserving,
  metadata-only contribution flows;
- private Atlas packs stay separate from public sample records.

This preserves the no-payload promise while building toward more accurate
training-data risk forecasts over time.
