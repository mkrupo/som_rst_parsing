# First ArgMicrotexts benchmark set

The first Jev/LLM comparison uses a fixed 14-document subset of the original
English ArgMicrotexts Part 1 collection. These document IDs identify the
subset:

```text
micro_b001_original
micro_b002_original
micro_b003_original
micro_b004_original
micro_b005_original
micro_b011_original
micro_b012_original
micro_b013_original
micro_b014_original
micro_b021_original
micro_b022_original
micro_b023_original
micro_b024_original
micro_b025_original
```

This is an experiment-defined slice, not an official train/dev/test split.
Treat it as an evaluation set for zero-shot runs, and use the same documents,
pair extraction, input text, labels, and gold annotations for Jev and LLM
comparisons. Results describe this 14-document set; they are not estimates of
performance across the entire corpus. The upstream corpus has 112 original
Part 1 texts, written in German and professionally translated to English, and
a separate Part 2 of 178 English texts. This initial set is from Part 1, not
Part 2. The RST annotations with EDU segmentation are in the
[ArgMicrotexts multilayer release](https://github.com/peldszus/arg-microtexts-multilayer).

## Label inventory

[`../configs/rst_relations.json`](../configs/rst_relations.json) defines the
34 relation labels used by the subset's no-Same-Unit RS3 headers. The 14
selected documents use that inventory and do not declare or use `sameunit`.
The profile excludes `sameunit` as a segmentation policy: spans are not split
to repair interrupted EDUs. Do not treat label absence in observed edges as a
reason to shrink the choice set.

The config assigns nuclearity this way:

- 27 mononuclear labels allow `NS` or `SN`.
- Seven multinuclear labels (`conjunction`, `contrast`, `disjunction`, `joint`,
  `list`, `restatement-mn`, and `sequence`) allow only `NN`.

`unstated-relation` is a fallback when a relation is clear but none of the
more specific labels applies. `evaluation-s` and `evaluation-n` encode which
side is evaluated. `cause` and `result` distinguish the satellite's causal
direction relative to the nucleus. Definitions are maintained in the config
file and included in the Jev question criteria.

## Pair format

Each JSONL row describes one labeled relation between two supplied spans:

- `document_context` is the complete source document.
- `span_a` and `span_b` are the two spans in textual order, with A earlier.
- `gold_relation` is one of the config labels.
- `gold_nuclearity` is `NS`, `SN`, or `NN`.

For traceability, prefix each row's `id` with its document ID, for example
`micro_b001_original:pair-001`. The runner uses gold fields only to validate
and evaluate; it does not send them to Jev. This repo currently defines the
label scheme and input contract, but does not include corpus files or a
pair-extraction utility. Before scoring, record exactly how tree relations
become ordered span pairs and how any multi-child relation is handled. Use the
same resulting pair rows for every model being compared.

The task is pairwise classification. It does not predict EDU boundaries,
serialize a complete RST tree, or apply a structural decoder.

## Data and attribution

Corpus texts and annotations are not included here. Keep local derived JSONL
files at `data/argmicrotexts*.jsonl`; Git ignores those paths. The upstream
Part 1 and multilayer release state a CC BY-NC-SA 4.0 license. Obtain data from
its maintainers, follow the license terms, and do not add corpus text or
annotations to this repository.

When publishing results, cite both sources:

- Andreas Peldszus and Manfred Stede. “An annotated corpus of argumentative
  microtexts.” First European Conference on Argumentation: Argumentation and
  Reasoned Action, 2015. See the
  [corpus page and citation details](https://angcl.ling.uni-potsdam.de/resources/argmicro.html).
- Manfred Stede, Stergos Afantenos, Andreas Peldszus, Nicholas Asher, and
  Jérémy Perret. “Parallel Discourse Annotations on a Corpus of Short Texts.”
  LREC 2016. The multilayer release lists this citation and its
  [license](https://github.com/peldszus/arg-microtexts-multilayer#license-and-citation).
