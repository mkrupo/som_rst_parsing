# Experiments

Live-run outputs are local files under Git-ignored `results/`. Give each
exploratory run a descriptive, versioned ID. The runner refuses to overwrite an
existing prediction file; use a new versioned directory for each new run.

Recommended layout:

```text
results/<experiment_id>/predictions.jsonl
results/<experiment_id>/raw_responses.jsonl
```

## Completed exploratory runs

### synthetic_smoke_v1

- Input: `data/example.jsonl`
- Purpose: verify OpenRouter and TypeSafe SDK transport, response parsing,
  probability distributions, caching, and metrics.
- Requested model: `jev-1.13`
- Served snapshot: `typesafe/jev-1.13-20260917`
- Size: `n=1`

This was a transport and implementation smoke test, not a scientific
evaluation.

### diagnostic_v1

- Input: `data/diagnostic.jsonl`
- Purpose: eight real ArgMicrotexts local RST decisions.
- Requested model: `jev-1.13`
- Size: `n=8`
- Relation accuracy: `0.50`
- Nuclearity accuracy: `0.875`

Several apparent relation errors were coherent alternative discourse
analyses. In particular, gold `cause/SN` versus predicted `result/NS`
preserved the same causal direction while changing prominence. This is a
diagnostic suite, not a benchmark.
