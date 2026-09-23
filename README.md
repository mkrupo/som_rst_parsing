# SOM RST Parsing

A small zero-shot experiment that asks TypeSafe Jev to classify an ordered pair
of RST spans with one relation label and one nuclearity label. Every uncached
record is sent in one `system_one` request containing two `Choice` questions.

The first benchmark set is a fixed 14-document subset of the original English
ArgMicrotexts Part 1 collection. The task uses 34 RST relation labels, with
`sameunit` excluded. This is pairwise relation and nuclearity classification;
it does not build a complete discourse tree. The exact document IDs and data
scope are recorded in [the task profile](docs/argmicrotexts.md). Relation
definitions live in [`configs/rst_relations.json`](configs/rst_relations.json).

## Start here

- [Cold start and experiment workflow](docs/cold-start.md)
- [ArgMicrotexts task profile and local data format](docs/argmicrotexts.md)
- [Copyable Jev playground demo](docs/playground.md)
- [Contributor and agent instructions](AGENTS.md)

## Quick run

Try the [official browser demo](docs/playground.md) first to inspect the task.
It requires a TypeSafe account and makes a live request under that account, so
check its displayed credits and pricing before running it. The local runner
also makes live requests and may consume credits through `TYPESAFE_API_KEY`.

Use Python 3.11. For an exact environment from the lock file, run:

```bash
uv sync --python 3.11
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m src.experiment --help
```

The tests make no Jev calls. If you do not use `uv`, see the [cold-start
guide](docs/cold-start.md) for a standard-library virtual environment setup.
Set `TYPESAFE_API_KEY` only when you are ready to run API requests.

```bash
.venv/bin/python -m src.experiment run --input data/example.jsonl
```

The included JSONL row is synthetic and only checks the input shape. It is not
an ArgMicrotexts item or an evaluation example. Corpus files are not included;
see [the data guide](docs/argmicrotexts.md). Local ArgMicrotexts JSONL files
are ignored by Git.

The runner writes `predictions.jsonl`, caches raw responses under
`cache/raw_responses.jsonl`, and prints accuracy, macro-F1, NLL, Brier score,
10-bin ECE, and latency summaries. It does not train a model.
