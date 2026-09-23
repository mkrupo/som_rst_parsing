# SOM RST Parsing

A small zero-shot experiment that asks TypeSafe Jev to classify an ordered pair
of RST spans with one relation label and one nuclearity label. Every uncached
record is sent in one `system_one` request containing two `Choice` questions.

This repository tests local RST decisions for two supplied spans. Unlike the
[end-to-end pipeline in `llm_rst_parsing`](https://github.com/mkrupo/llm_rst_parsing),
it does not build or output complete RST trees.

The first benchmark set is a fixed 14-document subset of the original English
ArgMicrotexts Part 1 collection. The task uses 34 RST relation labels, with
`sameunit` excluded. The exact document IDs and data
scope are recorded in [the task profile](docs/argmicrotexts.md). Relation
definitions live in [`configs/rst_relations.json`](configs/rst_relations.json).

## Start here

- [Cold start and experiment workflow](docs/cold-start.md)
- [ArgMicrotexts task profile and local data format](docs/argmicrotexts.md)
- [Experiment history and result layout](docs/experiments.md)
- [Optional direct TypeSafe browser demo](docs/playground.md)
- [Contributor and agent instructions](AGENTS.md)

## Quick run

The default live provider is OpenRouter. The [cold-start guide](docs/cold-start.md)
explains setup and distinguishes offline checks from the synthetic live smoke
request and later ArgMicrotexts experiments.

Use Python 3.11. For the locked environment and offline checks, run:

```bash
uv sync --python 3.11
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m src.experiment --help
```

The tests make no Jev calls. If you do not use `uv`, see the [cold-start
guide](docs/cold-start.md) for a standard-library virtual environment setup.
Set `OPENROUTER_API_KEY` only when you are ready to make the one synthetic
live request. Check the [current OpenRouter model page](https://openrouter.ai/typesafe)
for pricing before running it:

```bash
read -rsp "OpenRouter API key: " OPENROUTER_API_KEY
export OPENROUTER_API_KEY
printf '\n'
.venv/bin/python -m src.experiment run --provider openrouter --model jev-1.13 --input data/example.jsonl --output results/synthetic_smoke_v2/predictions.jsonl --cache results/synthetic_smoke_v2/raw_responses.jsonl
```

The included `data/example.jsonl` row is synthetic. Its prediction and metrics
are a smoke check, not an evaluation result. Corpus files are not included;
see [the data guide](docs/argmicrotexts.md). Local ArgMicrotexts JSONL files
are ignored by Git.

Exploratory live runs use descriptive, versioned directories under
`results/`; existing prediction outputs are never overwritten.

The command above writes predictions to
`results/synthetic_smoke_v2/predictions.jsonl` and raw responses to
`results/synthetic_smoke_v2/raw_responses.jsonl`. It prints accuracy,
macro-F1, NLL, Brier score, 10-bin ECE, and latency summaries. It does not
train a model.
