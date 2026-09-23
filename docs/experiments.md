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

### causal_direction_v1

- Input: `data/causal_direction.jsonl`
- Purpose: test whether Jev handles ArgMicrotexts `cause` differently for
  `NS` versus `SN` nuclearity.
- Requested model: `jev-1.13`
- Served snapshot: `typesafe/jev-1.13-20260917`
- Size: `n=8`
- Composition: 4 `cause/NS` and 4 `cause/SN` direct EDU-to-EDU cases,
  all distinct from `diagnostic_v1`.
- Relation accuracy: `0.50`
- Nuclearity accuracy: `0.50`

All 4 gold `cause/NS` cases were predicted `cause/NS`, while all
4 gold `cause/SN` cases were predicted `result/NS`. The errors
therefore formed a perfectly directional pattern rather than random relation
confusion. Under the supplied Cause/Result definitions, `cause/SN` and
`result/NS` preserve the same underlying causal direction while differing
in rhetorical prominence and nuclearity. This raises a question for later
experiments: whether the behavior reflects Jev's preferred discourse analysis
or the current independent relation-plus-nuclearity task formulation. This
remains a small diagnostic experiment, not a performance benchmark.

#### Fresh-call replication

- Input: `data/causal_direction.jsonl`
- Fresh output/cache directory: `results/causal_direction_repeat_v1/`
- Requested model: `jev-1.13`
- Served snapshot: `typesafe/jev-1.13-20260917`
- Size: `n=8`
- Relation accuracy: `0.50`
- Nuclearity accuracy: `0.50`

All 8 predicted relation and nuclearity labels replicated exactly. Again, 4/4
`cause/NS` cases were predicted `cause/NS`, and 4/4
`cause/SN` cases were predicted `result/NS`. Probabilities varied
slightly across fresh calls, but the qualitative pattern was unchanged.
