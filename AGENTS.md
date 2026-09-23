# Contributor and agent guide

## Project boundary

- Treat this repository as the complete project. Keep documentation and
  examples self-contained and suitable for a public repository.
- Keep changes in this repository. Do not rely on machine-specific paths,
  private notes, or files outside this checkout.
- Keep this experiment small: Python 3.11, `typesafe-sdk`, JSONL input/output,
  and direct functions are enough. Do not add training, a web service, a
  workflow framework, or new abstraction layers without a concrete need.

## Experiment contract

- The task is zero-shot classification of an ordered pair of spans with one
  RST relation and one nuclearity prediction.
- Send both predictions as `Choice` questions in the same `system_one` request
  for each uncached input record.
- Read the canonical labels and definitions from
  `configs/rst_relations.json`. Do not maintain a second runtime inventory in
  Python.
- Input rows contain `document_context`, `span_a`, `span_b`, `gold_relation`,
  and `gold_nuclearity`. Gold fields are only for validation/evaluation; never
  include them in the Jev state.
- The default OpenRouter provider reads credentials only from
  `OPENROUTER_API_KEY`; optional direct TypeSafe access reads only from
  `TYPESAFE_API_KEY`. Do not add key files or command-line key options, and
  never serialize credentials.
- Preserve each raw response before parsing it. Keep retries disabled unless
  the experiment contract is deliberately revised and documented.
- Evaluation uses the saved choice probabilities. Do not silently alter
  labels or reconcile a relation/nuclearity mismatch after the response.

## Experiment housekeeping

- Never overwrite or delete an existing experimental output unless the user
  explicitly instructs you to.
- Use descriptive, versioned experiment IDs such as `diagnostic_v1`.
- Put live-run artifacts under `results/<experiment_id>/`.
- Check existing experiment names and `docs/experiments.md` before
  creating a new experiment.
- Keep frozen experimental inputs and gold labels unchanged unless the user
  explicitly asks to revise them.
- Do not infer or invent research conclusions. Implement supplied
  experimental designs and preserve outputs.
- Use `README.md` for project orientation,
  `docs/cold-start.md` for operational setup,
  `docs/experiments.md` for the concise experiment trail, and
  `AGENTS.md` for agent/contributor rules. Avoid duplicating detailed
  content across them.

## Data and privacy

- Keep the full ArgMicrotexts corpus data and annotations uncommitted. Keep
  local corpus-derived JSONL under ignored `data/argmicrotexts*.jsonl`
  paths. Small public diagnostic excerpts may be committed when their public
  provenance and diagnostic purpose are documented.
- Document which corpus part, language, annotation release, segmentation, and
  document-level split a dataset uses.
- The bundled `data/example.jsonl` is synthetic and must remain clearly
  labeled as such.

## Changes and checks

- Keep public-facing docs accurate, self-contained, and linked to public
  sources where needed. Avoid references to private conversations or local
  documents.
- For changes to the relation inventory, check that every relation has a
  definition and valid nuclearity set, and update the playground example if
  label semantics changed.
- Do not make live Jev calls during routine edits. A live request needs an
  explicit user request.
- Keep automated checks in the Python standard library's `unittest`; do not
  add a separate test framework without a concrete need.
- Offline tests must use fake or mock responses. Never trigger a paid model
  request as part of routine verification.
