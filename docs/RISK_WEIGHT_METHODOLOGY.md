# Risk Weight Methodology

The public SignalLedger alpha includes small `risk_weight` values only as metadata-only
runtime fixtures. They are useful for exercising local blueprint, shield, and reporting
flows, but they are not calibrated production risk scores and should not be represented as
validated predictive coefficients.

## Public Alpha Boundary

- Financial Services is the only active public starter pack.
- Public `domain_patterns` rows are schema/runtime fixtures.
- Richer private pack rows, calibrated scoring weights, customer overlays, and source-family
  ranking logic belong outside the public repository.
- Every public fixture must remain metadata-only and must pass `NoPayloadValidator`.

## Calibration Requirement

A weight should only be described as validated after it is backed by one or more of:

- backtesting against known training-data incidents,
- structured expert elicitation with documented disagreement,
- customer-approved local ledger history, or
- a signed private pack with versioned provenance.

Until then, public rows are evidence of the local mechanism, not evidence of production
predictive accuracy.
