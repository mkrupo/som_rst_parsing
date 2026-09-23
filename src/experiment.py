from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import sys
import time
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELATIONS = ROOT / "configs" / "rst_relations.json"
REQUIRED_FIELDS = (
    "document_context",
    "span_a",
    "span_b",
    "gold_relation",
    "gold_nuclearity",
)
NUCLEARITY_LABELS = ("NS", "SN", "NN")
ECE_BINS = 10
NLL_EPSILON = 1e-15
DEFAULT_MODEL = "jev-1.13"
PROVIDERS = {
    "openrouter": {
        "api_key_env": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api",
    },
    "typesafe": {
        "api_key_env": "TYPESAFE_API_KEY",
        "base_url": "https://api.typesafe.ai",
    },
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_client(provider: str) -> Any:
    if provider not in PROVIDERS:
        raise ValueError(f"Unsupported provider {provider!r}.")
    provider_config = PROVIDERS[provider]
    api_key_env = provider_config["api_key_env"]
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise RuntimeError(f"Set {api_key_env} in the environment before making Jev requests.")

    from typesafe_sdk import RetryPolicy, TypeSafeClient

    return TypeSafeClient(
        api_key=api_key,
        base_url=provider_config["base_url"],
        retry=RetryPolicy(max_retries=0),
    )


def load_scheme(path: Path) -> tuple[dict[str, Any], str]:
    try:
        raw_text = path.read_text(encoding="utf-8")
        scheme = json.loads(raw_text)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read relation config {path}: {exc}") from exc

    if not isinstance(scheme, dict) or not isinstance(scheme.get("relations"), list):
        raise ValueError(f"Relation config {path} must contain a relations list.")
    if not isinstance(scheme.get("scheme"), str) or not scheme["scheme"].strip():
        raise ValueError(f"Relation config {path} must contain a non-empty scheme name.")
    relations: dict[str, dict[str, Any]] = {}
    for relation in scheme["relations"]:
        if not isinstance(relation, dict):
            raise ValueError("Each relation config entry must be an object.")
        label = relation.get("label")
        definition = relation.get("definition")
        allowed_nuclearity = relation.get("nuclearity")
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Every relation needs a non-empty label.")
        if not isinstance(definition, str) or not definition.strip():
            raise ValueError(f"Relation {label!r} needs a non-empty definition.")
        if label in relations:
            raise ValueError(f"Duplicate relation label in config: {label!r}.")
        if (
            not isinstance(allowed_nuclearity, list)
            or not allowed_nuclearity
            or any(item not in NUCLEARITY_LABELS for item in allowed_nuclearity)
        ):
            raise ValueError(f"Relation {label!r} has invalid nuclearity options.")
        relations[label] = relation

    if not relations or len(relations) > 255:
        raise ValueError("The relation config must define between 1 and 255 labels.")
    configured_nuclearity = scheme.get("nuclearity")
    if not isinstance(configured_nuclearity, list):
        raise ValueError("Relation config must contain a nuclearity list.")
    nuclearity = {item.get("label"): item for item in configured_nuclearity if isinstance(item, dict)}
    if set(nuclearity) != set(NUCLEARITY_LABELS):
        raise ValueError("Relation config must define NS, SN, and NN nuclearity labels.")
    if any(not isinstance(item.get("definition"), str) or not item["definition"].strip() for item in nuclearity.values()):
        raise ValueError("Every nuclearity label needs a non-empty definition.")

    scheme["relation_by_label"] = relations
    scheme["nuclearity_by_label"] = nuclearity
    return scheme, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


def load_items(path: Path, relation_by_label: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    try:
        source = path.open("r", encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Cannot open input JSONL {path}: {exc}") from exc

    with source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
            if not isinstance(item, dict):
                raise ValueError(f"Expected a JSON object at {path}:{line_number}.")

            for field in REQUIRED_FIELDS:
                value = item.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"{path}:{line_number}: {field!r} must be a non-empty string.")

            input_id = item.get("id", f"line-{line_number}")
            if not isinstance(input_id, str) or not input_id.strip():
                raise ValueError(f"{path}:{line_number}: 'id' must be a non-empty string when provided.")
            if input_id in seen_ids:
                raise ValueError(f"{path}:{line_number}: duplicate input id {input_id!r}.")
            seen_ids.add(input_id)

            relation = item["gold_relation"]
            nuclearity = item["gold_nuclearity"]
            if relation not in relation_by_label:
                raise ValueError(f"{path}:{line_number}: unknown gold relation {relation!r}.")
            if nuclearity not in NUCLEARITY_LABELS:
                raise ValueError(f"{path}:{line_number}: gold_nuclearity must be NS, SN, or NN.")
            if nuclearity not in relation_by_label[relation]["nuclearity"]:
                raise ValueError(
                    f"{path}:{line_number}: {relation!r} is incompatible with nuclearity {nuclearity!r}."
                )

            item["id"] = input_id
            item["line_number"] = line_number
            items.append(item)

    if not items:
        raise ValueError(f"Input JSONL {path} contains no records.")
    return items


def make_request(
    item: dict[str, Any],
    scheme: dict[str, Any],
    provider: str,
    model: str,
    scheme_hash: str,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    relation_criteria: dict[str, str] = {}
    for label, relation in scheme["relation_by_label"].items():
        definition = relation["definition"]
        if relation["nuclearity"] == ["NN"]:
            definition += " This relation is multinuclear and must use NN."
        else:
            definition += " This relation is mononuclear and must use NS or SN."
        relation_criteria[label] = definition

    nuclearity_criteria = {
        label: entry["definition"]
        for label, entry in scheme["nuclearity_by_label"].items()
    }
    state = {
        "document_context": item["document_context"],
        "span_a": item["span_a"],
        "span_b": item["span_b"],
    }
    question_payload = {
        "relation": {
            "type": "choice",
            "instructions": (
                f"Choose exactly one {scheme['scheme']} RST relation that best describes the relation "
                "between span A and span B. Use the supplied relation definitions. "
                "Span A precedes span B in the document."
            ),
            "criteria": relation_criteria,
        },
        "nuclearity": {
            "type": "choice",
            "instructions": (
                "Choose the nuclearity of the relation between the same ordered spans. "
                "Span A precedes span B in the document. Select NN for an equal-weight multinuclear relation."
            ),
            "criteria": nuclearity_criteria,
        },
    }
    request_payload = {"model": model, "state": state, "questions": question_payload}
    cache_key = sha256_text(
        canonical_json(
            {
                "provider": provider,
                "input_id": item["id"],
                "request": request_payload,
                "scheme_sha256": scheme_hash,
            }
        )
    )
    return state, question_payload, cache_key


def read_cache(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    cached: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid response cache JSON at {path}:{line_number}: {exc}") from exc
            if not isinstance(entry, dict) or not isinstance(entry.get("cache_key"), str):
                raise ValueError(f"Invalid response cache record at {path}:{line_number}.")
            if entry.get("status") == "success" and isinstance(entry.get("raw_response_text"), str):
                cached[entry["cache_key"]] = entry
    return cached


def append_jsonl(path: Path, value: dict[str, Any], *, sync: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as destination:
        destination.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
        destination.flush()
        if sync:
            os.fsync(destination.fileno())


def response_answers(response_body: Any, scheme: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(response_body, dict) or not isinstance(response_body.get("answers"), dict):
        raise ValueError("Jev response is missing its answers object.")
    answers = response_body["answers"]
    result: dict[str, Any] = {}
    for task, allowed_labels in (
        ("relation", list(scheme["relation_by_label"])),
        ("nuclearity", list(NUCLEARITY_LABELS)),
    ):
        answer = answers.get(task)
        if not isinstance(answer, dict):
            raise ValueError(f"Jev response is missing the {task!r} answer.")
        label = answer.get("choice")
        if label not in allowed_labels:
            raise ValueError(f"Jev returned unknown {task} label {label!r}.")
        raw_probabilities = answer.get("probabilities")
        if not isinstance(raw_probabilities, dict):
            raise ValueError(f"Jev response has no probability map for {task!r}.")
        unknown = set(raw_probabilities) - set(allowed_labels)
        missing = set(allowed_labels) - set(raw_probabilities)
        if unknown or missing:
            raise ValueError(
                f"Jev {task} probabilities have unexpected labels; missing={sorted(missing)}, "
                f"unknown={sorted(unknown)}."
            )
        probabilities: dict[str, float] = {}
        for candidate in allowed_labels:
            value = raw_probabilities[candidate]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"Jev returned a non-numeric probability for {task} label {candidate!r}.")
            probability = float(value)
            if not math.isfinite(probability) or probability < 0 or probability > 1:
                raise ValueError(f"Jev returned an invalid probability for {task} label {candidate!r}.")
            probabilities[candidate] = probability
        total = sum(probabilities.values())
        if total <= 0 or not math.isclose(total, 1.0, rel_tol=0.05, abs_tol=0.05):
            raise ValueError(f"Jev {task} probabilities do not sum approximately to 1 (sum={total}).")
        probabilities = {key: value / total for key, value in probabilities.items()}

        confidence = answer.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ValueError(f"Jev response has no numeric confidence for {task!r}.")
        confidence = float(confidence)
        if not math.isfinite(confidence) or confidence < 0 or confidence > 1:
            raise ValueError(f"Jev returned invalid confidence for {task!r}.")
        result[task] = {
            "prediction": label,
            "probabilities": probabilities,
            "confidence": confidence,
        }
    return {"answers": result, "response_model": response_body.get("model")}


def prediction_record(
    item: dict[str, Any],
    parsed: dict[str, Any],
    *,
    provider: str,
    model: str,
    cache_key: str,
    cache_entry: dict[str, Any],
    cache_hit: bool,
    scheme_hash: str,
    scheme_name: str,
) -> dict[str, Any]:
    relation = parsed["answers"]["relation"]
    nuclearity = parsed["answers"]["nuclearity"]
    return {
        "input_id": item["id"],
        "provider": provider,
        "model": model,
        "response_model": parsed.get("response_model"),
        "scheme": scheme_name,
        "scheme_sha256": scheme_hash,
        "gold_relation": item["gold_relation"],
        "predicted_relation": relation["prediction"],
        "relation_probabilities": relation["probabilities"],
        "relation_confidence": relation["confidence"],
        "gold_nuclearity": item["gold_nuclearity"],
        "predicted_nuclearity": nuclearity["prediction"],
        "nuclearity_probabilities": nuclearity["probabilities"],
        "nuclearity_confidence": nuclearity["confidence"],
        "api_latency_ms": cache_entry["api_latency_ms"],
        "cache_hit": cache_hit,
        "request_id": cache_entry.get("request_id"),
        "response_cache_key": cache_key,
    }


def evaluate_task(
    predictions: list[dict[str, Any]],
    *,
    gold_field: str,
    predicted_field: str,
    probabilities_field: str,
    labels: list[str],
) -> dict[str, Any]:
    if not predictions:
        raise ValueError("Cannot evaluate an empty predictions file.")
    count = len(predictions)
    correct = sum(row[gold_field] == row[predicted_field] for row in predictions)
    observed_labels = sorted({row[gold_field] for row in predictions} | {row[predicted_field] for row in predictions})
    f1_values: list[float] = []
    for label in observed_labels:
        true_positive = sum(row[gold_field] == label and row[predicted_field] == label for row in predictions)
        false_positive = sum(row[gold_field] != label and row[predicted_field] == label for row in predictions)
        false_negative = sum(row[gold_field] == label and row[predicted_field] != label for row in predictions)
        denominator = 2 * true_positive + false_positive + false_negative
        f1_values.append(2 * true_positive / denominator if denominator else 0.0)

    negative_log_likelihood = 0.0
    brier_score = 0.0
    confidence_buckets: list[list[tuple[float, bool]]] = [[] for _ in range(ECE_BINS)]
    for row in predictions:
        gold = row[gold_field]
        predicted = row[predicted_field]
        probabilities = row[probabilities_field]
        if set(probabilities) != set(labels):
            raise ValueError(f"Prediction {row.get('input_id')!r} has an incomplete probability distribution.")
        gold_probability = float(probabilities[gold])
        negative_log_likelihood -= math.log(max(gold_probability, NLL_EPSILON))
        brier_score += sum(
            (float(probabilities[label]) - (1.0 if label == gold else 0.0)) ** 2
            for label in labels
        )
        confidence = max(float(probabilities[label]) for label in labels)
        bucket = min(int(confidence * ECE_BINS), ECE_BINS - 1)
        confidence_buckets[bucket].append((confidence, predicted == gold))

    ece = 0.0
    for bucket in confidence_buckets:
        if bucket:
            average_confidence = sum(confidence for confidence, _ in bucket) / len(bucket)
            accuracy = sum(is_correct for _, is_correct in bucket) / len(bucket)
            ece += len(bucket) / count * abs(accuracy - average_confidence)

    return {
        "n": count,
        "accuracy": correct / count,
        "macro_f1": sum(f1_values) / len(f1_values),
        "nll": negative_log_likelihood / count,
        "brier_score": brier_score / count,
        "ece": ece,
    }


def evaluate_predictions(predictions: list[dict[str, Any]], relation_labels: list[str]) -> dict[str, Any]:
    latencies = [float(row["api_latency_ms"]) for row in predictions]
    ordered_latencies = sorted(latencies)
    p95_index = max(0, math.ceil(0.95 * len(ordered_latencies)) - 1)
    return {
        "n_instances": len(predictions),
        "relation": evaluate_task(
            predictions,
            gold_field="gold_relation",
            predicted_field="predicted_relation",
            probabilities_field="relation_probabilities",
            labels=relation_labels,
        ),
        "nuclearity": evaluate_task(
            predictions,
            gold_field="gold_nuclearity",
            predicted_field="predicted_nuclearity",
            probabilities_field="nuclearity_probabilities",
            labels=list(NUCLEARITY_LABELS),
        ),
        "api_latency_ms": {
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "p95": ordered_latencies[p95_index],
        },
        "ece_bins": ECE_BINS,
        "macro_f1_labels": "labels present in gold or predictions",
        "brier_score": "multiclass sum of squared probability errors, averaged over instances",
    }


def read_predictions(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid prediction JSON at {path}:{line_number}: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Expected a prediction object at {path}:{line_number}.")
            rows.append(row)
    return rows


def run(args: argparse.Namespace) -> None:
    scheme, scheme_hash = load_scheme(args.relations)
    items = load_items(args.input, scheme["relation_by_label"])
    cache = read_cache(args.cache)
    prepared = []
    for item in items:
        state, question_payload, cache_key = make_request(
            item, scheme, args.provider, args.model, scheme_hash
        )
        prepared.append((item, state, question_payload, cache_key, cache.get(cache_key)))

    needs_api = any(cache_entry is None for _, _, _, _, cache_entry in prepared)
    client_manager = nullcontext(None)
    if needs_api:
        try:
            from typesafe_sdk import Choice, TypeSafeAPIError

            client_manager = create_client(args.provider)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(
                f"Could not initialize the TypeSafe SDK client ({type(exc).__name__})."
            ) from exc

    args.output.parent.mkdir(parents=True, exist_ok=True)
    predictions: list[dict[str, Any]] = []

    with args.output.open("w", encoding="utf-8") as destination:
        with client_manager as client:
            for item, state, question_payload, cache_key, cache_entry in prepared:
                cache_hit = cache_entry is not None
                if cache_entry is None:
                    typed_questions = {
                        name: Choice(instructions=question["instructions"], criteria=question["criteria"])
                        for name, question in question_payload.items()
                    }
                    started = time.perf_counter()
                    try:
                        response = client.system_one(
                            state=state,
                            questions=typed_questions,
                            model=args.model,
                        )
                    except TypeSafeAPIError as exc:
                        latency_ms = (time.perf_counter() - started) * 1000
                        append_jsonl(
                            args.cache,
                            {
                                "cache_key": cache_key,
                                "status": "http_error",
                                "http_status": exc.status,
                                "api_latency_ms": latency_ms,
                                "request_id": exc.request_id,
                                "raw_response_body": exc.body,
                                "error_type": type(exc).__name__,
                                "error_message": str(exc),
                                "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                            },
                            sync=True,
                        )
                        raise RuntimeError(
                            f"Jev request failed for input {item['id']!r} (HTTP {exc.status}); "
                            f"error response saved in {args.cache}."
                        ) from exc
                    except Exception as exc:
                        latency_ms = (time.perf_counter() - started) * 1000
                        append_jsonl(
                            args.cache,
                            {
                                "cache_key": cache_key,
                                "status": "request_error",
                                "api_latency_ms": latency_ms,
                                "raw_response_body": None,
                                "error_type": type(exc).__name__,
                                "error_message": str(exc),
                                "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                            },
                            sync=True,
                        )
                        raise

                    latency_ms = (time.perf_counter() - started) * 1000
                    cache_entry = {
                        "cache_key": cache_key,
                        "status": "success",
                        "provider": args.provider,
                        "model": args.model,
                        "scheme_sha256": scheme_hash,
                        "api_latency_ms": latency_ms,
                        "http_status": response.raw_http_response.status_code,
                        "request_id": response.raw_http_response.headers.get(
                            "x-typesafe-request-id"
                        ),
                        "raw_response_text": response.raw_http_response.text,
                        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                    }
                    append_jsonl(args.cache, cache_entry, sync=True)
                    cache[cache_key] = cache_entry

                try:
                    response_body = json.loads(cache_entry["raw_response_text"])
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Cached Jev response for {item['id']!r} is not valid JSON.") from exc
                parsed = response_answers(response_body, scheme)
                record = prediction_record(
                    item,
                    parsed,
                    provider=args.provider,
                    model=args.model,
                    cache_key=cache_key,
                    cache_entry=cache_entry,
                    cache_hit=cache_hit,
                    scheme_hash=scheme_hash,
                    scheme_name=scheme["scheme"],
                )
                destination.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                destination.flush()
                predictions.append(record)

    report = evaluate_predictions(predictions, list(scheme["relation_by_label"]))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


def evaluate(args: argparse.Namespace) -> None:
    scheme, _ = load_scheme(args.relations)
    predictions = read_predictions(args.predictions)
    report = evaluate_predictions(predictions, list(scheme["relation_by_label"]))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run or evaluate the minimal zero-shot Jev RST span-decision experiment."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Classify each input instance with Jev.")
    run_parser.add_argument("--input", type=Path, required=True, help="Input JSONL file.")
    run_parser.add_argument("--output", type=Path, default=Path("predictions.jsonl"))
    run_parser.add_argument("--cache", type=Path, default=Path("cache/raw_responses.jsonl"))
    run_parser.add_argument("--relations", type=Path, default=DEFAULT_RELATIONS)
    run_parser.add_argument(
        "--provider",
        choices=tuple(PROVIDERS),
        default="openrouter",
        help="API provider (default: openrouter).",
    )
    run_parser.add_argument("--model", default=DEFAULT_MODEL)
    run_parser.set_defaults(func=run)

    evaluate_parser = subparsers.add_parser("evaluate", help="Evaluate an existing predictions JSONL file.")
    evaluate_parser.add_argument("--predictions", type=Path, default=Path("predictions.jsonl"))
    evaluate_parser.add_argument("--relations", type=Path, default=DEFAULT_RELATIONS)
    evaluate_parser.set_defaults(func=evaluate)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
