# Cold start

This guide is enough to set up the experiment from a fresh checkout. The
project requires Python 3.11 and pins `typesafe-sdk` in `pyproject.toml`.

## Install

The lock file records the complete tested environment:

```bash
uv sync --python 3.11
```

Or use Python's built-in virtual environment support and install the pinned
SDK directly:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

On Windows, activate the environment with `.venv\Scripts\activate`.

## Verify offline

From the repository root, run:

```bash
python -m unittest discover -s tests -v
python -m src.experiment --help
```

These checks use a fake Jev response and do not need an account, API key, or
network access. They verify the relation config and example row, the two
question request shape, raw response caching and reuse, prediction output,
metrics, and the command interface. The Playground smoke test below is a
separate manual check and makes a live request.

## Understand the task

The input to Jev is a document context and two ordered spans. The model makes
two separate closed-set decisions in one request:

1. Which of the 34 ArgMicrotexts RST relation labels connects the spans?
2. What is their nuclearity: `NS`, `SN`, or `NN`?

`span_a` precedes `span_b` in the text. `NS` means A is nucleus and B is
satellite; `SN` means A is satellite and B is nucleus; `NN` means both are
nuclei. The label inventory and definitions are in
[`../configs/rst_relations.json`](../configs/rst_relations.json).

This is pairwise classification. It predicts neither EDU boundaries nor a
complete document tree. The bundled row in `data/example.jsonl` is synthetic;
it is not an ArgMicrotexts sample.

## Prepare an input file

Create UTF-8 JSONL with one record per labeled pair. The required fields are:

```json
{"id":"doc01-pair01","document_context":"The road was wet. It had rained all night.","span_a":"The road was wet.","span_b":"It had rained all night.","gold_relation":"cause","gold_nuclearity":"NS"}
```

`id` is optional, but unique IDs make output easier to trace. Keep each pair's
full source document in `document_context`. Use the exact lowercase relation
labels in the config and one of `NS`, `SN`, or `NN`. The runner checks that
gold relation/nuclearity combinations are allowed by the config.

Keep ArgMicrotexts JSONL files at `data/argmicrotexts*.jsonl`; Git ignores
those files. See [the ArgMicrotexts guide](argmicrotexts.md) for corpus part,
license, the exact 14-document benchmark set, segmentation, and split details.
For the first comparison, create rows only from those documents and prefix
each row ID with its source document ID.

## Set the API key when ready

The runner reads credentials only from `TYPESAFE_API_KEY`. Do not put the key
in a source file or input JSONL.

```bash
read -rsp "TypeSafe API key: " TYPESAFE_API_KEY
export TYPESAFE_API_KEY
printf '\n'
```

## Run or evaluate

```bash
python -m src.experiment run --input data/argmicrotexts_test.jsonl
```

Each uncached record makes one request containing relation and nuclearity
`Choice` questions. Raw HTTP response text is appended to
`cache/raw_responses.jsonl` before it is parsed. Matching cache entries are
reused on later runs. The default model is `jev-latest`; SDK retries are
disabled.

The runner writes `predictions.jsonl` and prints relation/nuclearity accuracy,
macro-F1, NLL, multiclass Brier score, 10-bin ECE, and mean/median/p95 API
latency. Recompute metrics from saved predictions without requesting Jev:

```bash
python -m src.experiment evaluate --predictions predictions.jsonl
```

Use `--output`, `--cache`, `--relations`, and `--model` to change those paths
or settings. Run `python -m src.experiment --help` for the command interface.

## Try the browser demo first

To inspect the task through a web interface before setting up API access, use
the copyable instructions in [`playground.md`](playground.md). The demo uses
the official TypeSafe console and a synthetic example. It is a live request
under your TypeSafe account, not an evaluation run; check the account's credits
and pricing before clicking Run.
