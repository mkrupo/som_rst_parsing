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

### Systematic Cause dataset

- Input: `data/argmicrotexts_cause_direct.jsonl`
- Source: automatically extracted from ArgMicrotexts RS3 annotations with the
  repository extractor.
- Size: 17 direct EDU-to-EDU `cause` relations from 16 unique source documents.
- Composition: 6 `cause/NS`, 11 `cause/SN`, 0 `NN`.
- All IDs are unique, and every row has source file, satellite segment ID, and
  nucleus segment ID provenance.
- Regeneration from the local RS3 source was byte-identical.
- SHA-256: `11bf71baa940d9b70f78c254e8022d85236eb8ab70454b14fe3d60ecf2f64b28`

This systematically extracted diagnostic set is not an official benchmark
split. The fixed file was used unchanged for both formulations below.

### cause_direct_systematic_independent_v1

- Input: `data/argmicrotexts_cause_direct.jsonl`
- Formulation: independent relation `Choice` plus nuclearity `Choice`.
- Requested model: `jev-1.13`
- Size: `n=17`
- Relation accuracy: `0.5294117647`
- Nuclearity accuracy: `0.5294117647`

All 6 gold `cause/NS` cases were predicted exactly as `cause/NS`. Among the 11
gold `cause/SN` cases, 3 were predicted `cause/SN`, 6 `result/NS`, 1
`evaluation-s/NS`, and 1 `reason/NS`. `cause/SN` and `result/NS` preserve the
same underlying causal direction while differing in relation orientation and
rhetorical prominence. This equivalence is descriptive only, not a standard
RST evaluation metric.

### cause_direct_systematic_joint_v1

- Input: `data/argmicrotexts_cause_direct.jsonl`
- Formulation: one joint `Choice` over 61 valid relation/nuclearity combinations.
- Requested model: `jev-1.13`
- Size: `n=17`
- Joint accuracy: `0.5882352941`
- Relation accuracy: `0.5882352941`
- Nuclearity accuracy: `0.5882352941`

All 6 gold `cause/NS` cases again remained `cause/NS`. Among the 11 gold
`cause/SN` cases, 4 were predicted `cause/SN`, 5 `result/NS`, 1
`evaluation-s/NS`, and 1 `conjunction/NN`. Coupling relation and nuclearity
produced a small improvement over the independent formulation, but did not
remove the strong NS/SN asymmetry.

These results reduce the manual-selection concern from the earlier 8-case
diagnostics, but remain specific to a small Cause-focused diagnostic and
should not be generalized to RST parsing overall. They motivate later study of
whether the `cause/SN` versus `result/NS` differences reflect model or task
formulation effects, linguistically plausible alternative analyses, or
human-label variation.

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

### causal_direction_joint_v1

- Input: `data/causal_direction.jsonl`
- Formulation: one joint `Choice` over 61 valid relation/nuclearity combinations.
- Requested model: `jev-1.13`
- Served snapshot: `typesafe/jev-1.13-20260917`
- Size: `n=8`
- Joint accuracy: `0.625`
- Relation accuracy: `0.625`
- Nuclearity accuracy: `0.625`

All four `cause/NS` cases remained `cause/NS`. `causal-sn-b051` changed from
the independent formulation's `result/NS` to the gold `cause/SN`; the other
three `cause/SN` cases remained `result/NS`. The first run therefore matched
5/8 full labels. Coupling relation and nuclearity had a small but reproducible
effect, but did not explain most of the earlier
`cause/SN` to `result/NS` pattern. This remains a small diagnostic experiment,
not a benchmark or general performance result.

#### Fresh-call replication

The fresh joint run reproduced the same 5/8 label pattern exactly.

#### Fresh-call replication: causal_direction_joint_repeat_v1

The fresh-call replication used the same `data/causal_direction.jsonl`,
requested `jev-1.13` (served snapshot
`typesafe/jev-1.13-20260917`), and had `n=8`. It reproduced the same
qualitative 5/8 label pattern as `causal_direction_joint_v1`: all four
`cause/NS` cases were `cause/NS`, one `cause/SN` case was `cause/SN`, and the
other three were `result/NS`.
