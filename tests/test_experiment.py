from __future__ import annotations

import contextlib
import io
import json
import os
import re
import sys
import tempfile
import types
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from src import experiment


class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scheme, cls.scheme_hash = experiment.load_scheme(experiment.DEFAULT_RELATIONS)
        cls.relation_labels = list(cls.scheme["relation_by_label"])

    def test_argmicrotexts_scheme_and_synthetic_input(self) -> None:
        self.assertEqual(len(self.relation_labels), 34)
        self.assertNotIn("sameunit", self.relation_labels)
        self.assertEqual(
            sum(
                relation["nuclearity"] == ["NN"]
                for relation in self.scheme["relation_by_label"].values()
            ),
            7,
        )
        items = experiment.load_items(
            experiment.ROOT / "data" / "example.jsonl",
            self.scheme["relation_by_label"],
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["gold_relation"], "cause")
        self.assertEqual(items[0]["gold_nuclearity"], "NS")

    def test_real_data_diagnostic_input_validates(self) -> None:
        items = experiment.load_items(
            experiment.ROOT / "data" / "diagnostic.jsonl",
            self.scheme["relation_by_label"],
        )

        self.assertEqual(len(items), 8)
        ids = [item["id"] for item in items]
        self.assertEqual(len(set(ids)), 8)
        for item in items:
            relation = item["gold_relation"]
            nuclearity = item["gold_nuclearity"]
            self.assertIn(relation, self.scheme["relation_by_label"])
            self.assertIn(
                nuclearity,
                self.scheme["relation_by_label"][relation]["nuclearity"],
            )

    def test_causal_direction_input_validates(self) -> None:
        items = experiment.load_items(
            experiment.ROOT / "data" / "causal_direction.jsonl",
            self.scheme["relation_by_label"],
        )

        self.assertEqual(len(items), 8)
        self.assertTrue(all(item["gold_relation"] == "cause" for item in items))
        nuclearities = [item["gold_nuclearity"] for item in items]
        self.assertEqual(nuclearities.count("NS"), 4)
        self.assertEqual(nuclearities.count("SN"), 4)
        ids = [item["id"] for item in items]
        self.assertEqual(len(set(ids)), 8)
        for item in items:
            relation = item["gold_relation"]
            nuclearity = item["gold_nuclearity"]
            self.assertIn(relation, self.scheme["relation_by_label"])
            self.assertIn(
                nuclearity,
                self.scheme["relation_by_label"][relation]["nuclearity"],
            )

    def test_joint_label_inventory_has_61_valid_unique_options(self) -> None:
        inventory = experiment.joint_label_inventory(self.scheme)
        configured_pairs = {
            (relation_label, nuclearity_label)
            for relation_label, relation in self.scheme["relation_by_label"].items()
            for nuclearity_label in relation["nuclearity"]
        }

        self.assertEqual(len(inventory), 61)
        self.assertEqual(len(set(inventory)), 61)
        self.assertEqual(set(inventory.values()), configured_pairs)
        for joint_label, (relation_label, nuclearity_label) in inventory.items():
            self.assertEqual(joint_label, f"{relation_label}_{nuclearity_label}")
            self.assertIn(relation_label, self.scheme["relation_by_label"])
            self.assertIn(
                nuclearity_label,
                self.scheme["relation_by_label"][relation_label]["nuclearity"],
            )
        self.assertNotIn("cause_NN", inventory)
        self.assertNotIn("contrast_NS", inventory)
        self.assertNotIn("contrast_SN", inventory)

    def test_request_contains_two_choices_and_no_gold_fields(self) -> None:
        item = experiment.load_items(
            experiment.ROOT / "data" / "example.jsonl",
            self.scheme["relation_by_label"],
        )[0]
        state, questions, cache_key = experiment.make_request(
            item, self.scheme, "openrouter", "jev-1.13", self.scheme_hash
        )

        self.assertEqual(set(questions), {"relation", "nuclearity"})
        self.assertEqual(questions["relation"]["type"], "choice")
        self.assertEqual(questions["nuclearity"]["type"], "choice")
        self.assertEqual(len(questions["relation"]["criteria"]), 34)
        self.assertEqual(
            questions["relation"]["instructions"],
            "Choose exactly one argmicrotexts RST relation that best describes the relation "
            "between span A and span B. Use the supplied relation definitions. "
            "Span A precedes span B in the document.",
        )
        self.assertEqual(
            questions["nuclearity"]["instructions"],
            "Choose the nuclearity of the relation between the same ordered spans. "
            "Span A precedes span B in the document. Select NN for an equal-weight multinuclear relation.",
        )
        expected_relation_criteria = {}
        for label, relation in self.scheme["relation_by_label"].items():
            definition = relation["definition"]
            if relation["nuclearity"] == ["NN"]:
                definition += " This relation is multinuclear and must use NN."
            else:
                definition += " This relation is mononuclear and must use NS or SN."
            expected_relation_criteria[label] = definition
        self.assertEqual(questions["relation"]["criteria"], expected_relation_criteria)
        self.assertEqual(
            questions["nuclearity"]["criteria"],
            {
                label: entry["definition"]
                for label, entry in self.scheme["nuclearity_by_label"].items()
            },
        )
        self.assertNotIn("gold_relation", state)
        self.assertNotIn("gold_nuclearity", state)
        self.assertEqual(len(cache_key), 64)

    def test_joint_request_uses_one_choice_canonical_criteria_and_isolated_cache_key(self) -> None:
        item = experiment.load_items(
            experiment.ROOT / "data" / "example.jsonl",
            self.scheme["relation_by_label"],
        )[0]
        state, questions, joint_cache_key = experiment.make_request(
            item,
            self.scheme,
            "openrouter",
            "jev-1.13",
            self.scheme_hash,
            formulation="joint",
        )
        independent_state, independent_questions, independent_cache_key = experiment.make_request(
            item, self.scheme, "openrouter", "jev-1.13", self.scheme_hash
        )
        inventory = experiment.joint_label_inventory(self.scheme)
        joint_criteria = questions["relation_nuclearity"]["criteria"]
        expected_criteria = {
            joint_label: (
                f"{self.scheme['relation_by_label'][relation_label]['definition']} "
                f"{self.scheme['nuclearity_by_label'][nuclearity_label]['definition']}"
            )
            for joint_label, (relation_label, nuclearity_label) in inventory.items()
        }

        self.assertEqual(set(questions), {"relation_nuclearity"})
        self.assertEqual(questions["relation_nuclearity"]["type"], "choice")
        self.assertEqual(len(joint_criteria), 61)
        self.assertEqual(joint_criteria, expected_criteria)
        instructions = questions["relation_nuclearity"]["instructions"]
        self.assertIn("Choose exactly one valid relation+nuclearity analysis", instructions)
        self.assertIn("Span A precedes Span B in the document", instructions)
        self.assertIn("Each option already specifies both the RST relation", instructions)
        self.assertIn("Use the supplied definitions", instructions)
        self.assertEqual(set(state), {"document_context", "span_a", "span_b"})
        self.assertEqual(state, independent_state)
        self.assertEqual(set(independent_questions), {"relation", "nuclearity"})
        self.assertNotIn("gold_relation", state)
        self.assertNotIn("gold_nuclearity", state)
        self.assertNotEqual(joint_cache_key, independent_cache_key)

        old_independent_identity = {
            "provider": "openrouter",
            "input_id": item["id"],
            "request": {
                "model": "jev-1.13",
                "state": state,
                "questions": independent_questions,
            },
            "scheme_sha256": self.scheme_hash,
        }
        self.assertEqual(
            independent_cache_key,
            experiment.sha256_text(experiment.canonical_json(old_independent_identity)),
        )

    def test_provider_cli_defaults_are_pinned(self) -> None:
        args = experiment.build_parser().parse_args(
            ["run", "--input", "data/example.jsonl"]
        )
        self.assertEqual(args.provider, "openrouter")
        self.assertEqual(args.model, "jev-1.13")
        self.assertEqual(args.formulation, "independent")
        joint_args = experiment.build_parser().parse_args(
            ["run", "--input", "data/example.jsonl", "--formulation", "joint"]
        )
        self.assertEqual(joint_args.formulation, "joint")

    def test_joint_response_decoding_marginals_record_and_evaluation(self) -> None:
        item = next(
            item
            for item in experiment.load_items(
                experiment.ROOT / "data" / "causal_direction.jsonl",
                self.scheme["relation_by_label"],
            )
            if item["id"] == "causal-sn-b051"
        )
        inventory = experiment.joint_label_inventory(self.scheme)
        joint_probabilities = {label: 0.0 for label in inventory}
        joint_probabilities["cause_SN"] = 0.4
        joint_probabilities["result_NS"] = 0.6
        response_body = {
            "model": "typesafe/jev-1.13-20260917",
            "answers": {
                "relation_nuclearity": {
                    "type": "choice",
                    "choice": "result_NS",
                    "confidence": 0.77,
                    "probabilities": joint_probabilities,
                }
            },
        }

        parsed = experiment.response_answers(response_body, self.scheme, "joint")
        joint_answer = parsed["answers"]["joint"]
        relation_probabilities = parsed["answers"]["relation"]["probabilities"]
        nuclearity_probabilities = parsed["answers"]["nuclearity"]["probabilities"]
        record = experiment.prediction_record(
            item,
            parsed,
            provider="openrouter",
            model="jev-1.13",
            cache_key="offline-joint-cache-key",
            cache_entry={"api_latency_ms": 1.0},
            cache_hit=False,
            scheme_hash=self.scheme_hash,
            scheme_name=self.scheme["scheme"],
        )

        self.assertEqual(len(joint_answer["probabilities"]), 61)
        self.assertEqual(set(joint_answer["probabilities"]), set(inventory))
        self.assertEqual(joint_answer["probabilities"], joint_probabilities)
        self.assertEqual(joint_answer["confidence"], 0.77)
        self.assertEqual(record["formulation"], "joint")
        self.assertEqual(record["gold_joint"], "cause_SN")
        self.assertEqual(record["predicted_joint"], "result_NS")
        self.assertEqual(record["joint_confidence"], 0.77)
        self.assertEqual(record["predicted_relation"], "result")
        self.assertEqual(record["predicted_nuclearity"], "NS")
        self.assertNotIn("relation_confidence", record)
        self.assertNotIn("nuclearity_confidence", record)
        self.assertEqual(set(relation_probabilities), set(self.relation_labels))
        self.assertEqual(relation_probabilities["cause"], 0.4)
        self.assertEqual(relation_probabilities["result"], 0.6)
        self.assertEqual(nuclearity_probabilities, {"NS": 0.6, "SN": 0.4, "NN": 0.0})
        self.assertAlmostEqual(sum(relation_probabilities.values()), 1.0)
        self.assertAlmostEqual(sum(nuclearity_probabilities.values()), 1.0)

        report = experiment.evaluate_predictions(
            [record],
            self.relation_labels,
            list(inventory),
        )
        self.assertIn("joint", report)
        self.assertIn("relation", report)
        self.assertIn("nuclearity", report)
        self.assertEqual(
            set(report["joint"]),
            {"n", "accuracy", "macro_f1", "nll", "brier_score", "ece"},
        )
        self.assertEqual(report["joint"]["accuracy"], 0.0)

    def test_joint_run_with_fake_typesafe_client(self) -> None:
        items = experiment.load_items(
            experiment.ROOT / "data" / "example.jsonl",
            self.scheme["relation_by_label"],
        )
        self.assertEqual(len(items), 1)
        joint_labels = experiment.joint_label_inventory(self.scheme)
        probabilities = {label: 0.0 for label in joint_labels}
        probabilities["cause_SN"] = 0.3
        probabilities["result_NS"] = 0.7
        response_body = {
            "model": "typesafe/jev-1.13-20260917",
            "answers": {
                "relation_nuclearity": {
                    "type": "choice",
                    "choice": "result_NS",
                    "confidence": 0.84,
                    "probabilities": probabilities,
                }
            },
        }
        raw_response_text = json.dumps(response_body)
        calls: list[tuple[dict[str, str], dict[str, object], str]] = []
        self_outer = self

        class FakeChoice:
            def __init__(self, *, instructions: str, criteria: dict[str, str]) -> None:
                self.instructions = instructions
                self.criteria = criteria

        class FakeRetryPolicy:
            def __init__(self, *, max_retries: int) -> None:
                self.max_retries = max_retries

        class FakeHTTPResponse:
            status_code = 200
            text = raw_response_text
            headers: dict[str, str] = {}

        class FakeResponse:
            raw_http_response = FakeHTTPResponse()

        class FakeClient:
            def __init__(
                self,
                *,
                api_key: str,
                base_url: str,
                retry: FakeRetryPolicy,
            ) -> None:
                self_outer.assertEqual(api_key, "offline-openrouter-secret")
                self_outer.assertEqual(base_url, "https://openrouter.ai/api")
                self.retry = retry

            def __enter__(self) -> FakeClient:
                return self

            def __exit__(self, *_: object) -> bool:
                return False

            def system_one(
                self,
                *,
                state: dict[str, str],
                questions: dict[str, FakeChoice],
                model: str,
            ) -> FakeResponse:
                calls.append((state, questions, model))
                self_outer.assertEqual(set(state), {"document_context", "span_a", "span_b"})
                self_outer.assertEqual(set(questions), {"relation_nuclearity"})
                self_outer.assertIsInstance(questions["relation_nuclearity"], FakeChoice)
                self_outer.assertEqual(
                    set(questions["relation_nuclearity"].criteria),
                    set(joint_labels),
                )
                self_outer.assertEqual(len(questions["relation_nuclearity"].criteria), 61)
                self_outer.assertEqual(model, "jev-1.13")
                self_outer.assertEqual(self.retry.max_retries, 0)
                return FakeResponse()

        fake_sdk = types.ModuleType("typesafe_sdk")
        fake_sdk.Choice = FakeChoice
        fake_sdk.RetryPolicy = FakeRetryPolicy
        fake_sdk.TypeSafeClient = FakeClient
        fake_sdk.TypeSafeAPIError = type("TypeSafeAPIError", (Exception,), {})

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            args = Namespace(
                input=experiment.ROOT / "data" / "example.jsonl",
                output=base / "predictions.jsonl",
                cache=base / "cache" / "raw_responses.jsonl",
                relations=experiment.DEFAULT_RELATIONS,
                provider="openrouter",
                model="jev-1.13",
                formulation="joint",
            )
            output = io.StringIO()
            with (
                patch.dict(sys.modules, {"typesafe_sdk": fake_sdk}),
                patch.dict(
                    os.environ,
                    {"OPENROUTER_API_KEY": "offline-openrouter-secret"},
                    clear=True,
                ),
                contextlib.redirect_stdout(output),
            ):
                experiment.run(args)
                prediction = json.loads(args.output.read_text(encoding="utf-8"))
                cached = json.loads(args.cache.read_text(encoding="utf-8"))
                report = json.loads(output.getvalue())

        self.assertEqual(len(calls), 1)
        self.assertEqual(prediction["formulation"], "joint")
        self.assertEqual(prediction["joint_probabilities"], probabilities)
        self.assertEqual(prediction["predicted_joint"], "result_NS")
        self.assertEqual(prediction["predicted_relation"], "result")
        self.assertEqual(prediction["predicted_nuclearity"], "NS")
        self.assertAlmostEqual(sum(prediction["relation_probabilities"].values()), 1.0)
        self.assertAlmostEqual(sum(prediction["nuclearity_probabilities"].values()), 1.0)
        self.assertEqual(prediction["joint_confidence"], 0.84)
        self.assertNotIn("relation_confidence", prediction)
        self.assertNotIn("nuclearity_confidence", prediction)
        self.assertEqual(cached["raw_response_text"], raw_response_text)
        self.assertEqual(report["n_instances"], len(items))
        self.assertIn("joint", report)

    def test_provider_client_configuration_needs_no_network(self) -> None:
        openrouter_key = "offline-openrouter-secret"
        with (
            patch.dict(os.environ, {"OPENROUTER_API_KEY": openrouter_key}),
            patch("typesafe_sdk.TypeSafeClient") as client_class,
        ):
            result = experiment.create_client("openrouter")

        self.assertIs(result, client_class.return_value)
        openrouter_config = client_class.call_args.kwargs
        self.assertEqual(openrouter_config["api_key"], openrouter_key)
        self.assertEqual(openrouter_config["base_url"], "https://openrouter.ai/api")
        self.assertEqual(openrouter_config["retry"].max_retries, 0)

        typesafe_key = "offline-typesafe-secret"
        with (
            patch.dict(os.environ, {"TYPESAFE_API_KEY": typesafe_key}),
            patch("typesafe_sdk.TypeSafeClient") as client_class,
        ):
            experiment.create_client("typesafe")
        typesafe_config = client_class.call_args.kwargs
        self.assertEqual(typesafe_config["api_key"], typesafe_key)
        self.assertEqual(typesafe_config["base_url"], "https://api.typesafe.ai")
        self.assertEqual(typesafe_config["retry"].max_retries, 0)

        with patch.dict(os.environ, {"TYPESAFE_API_KEY": typesafe_key}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "OPENROUTER_API_KEY"):
                experiment.create_client("openrouter")

    def test_playground_question_criteria_match_config(self) -> None:
        guide = (experiment.ROOT / "docs" / "playground.md").read_text(encoding="utf-8")
        marker = "## Add both Choice questions"
        self.assertIn(marker, guide)
        question_section = guide.split(marker, maxsplit=1)[1]
        lines = question_section.splitlines()
        start = next(index for index, line in enumerate(lines) if line == "    {")
        end = next(index for index in range(start, len(lines)) if lines[index] == "    }")
        question_json = "\n".join(line[4:] for line in lines[start : end + 1])
        playground_questions = json.loads(question_json)

        expected_relation_criteria = {}
        for label, relation in self.scheme["relation_by_label"].items():
            definition = relation["definition"]
            if relation["nuclearity"] == ["NN"]:
                definition += " This relation is multinuclear and must use NN."
            else:
                definition += " This relation is mononuclear and must use NS or SN."
            expected_relation_criteria[label] = definition

        self.assertEqual(set(playground_questions), {"relation", "nuclearity"})
        self.assertEqual(playground_questions["relation"]["criteria"], expected_relation_criteria)
        self.assertEqual(
            playground_questions["nuclearity"]["criteria"],
            {
                label: entry["definition"]
                for label, entry in self.scheme["nuclearity_by_label"].items()
            },
        )

    def test_local_markdown_links_resolve(self) -> None:
        markdown_files = [
            experiment.ROOT / "README.md",
            experiment.ROOT / "AGENTS.md",
            *sorted((experiment.ROOT / "docs").glob("*.md")),
        ]
        for markdown_file in markdown_files:
            content = markdown_file.read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)]+)\)", content):
                if target.startswith(("https://", "http://", "mailto:")):
                    continue
                local_target = target.split("#", maxsplit=1)[0]
                if local_target:
                    self.assertTrue(
                        (markdown_file.parent / local_target).exists(),
                        f"Broken local link in {markdown_file.relative_to(experiment.ROOT)}: {target}",
                    )

    def test_runner_caches_raw_response_and_reuses_it(self) -> None:
        probabilities = {label: 0.0 for label in self.relation_labels}
        probabilities["cause"] = 0.8
        probabilities["result"] = 0.2
        response_body = {
            "model": "typesafe/jev-1.13-20260917",
            "id": "gen-dec-offline-test",
            "provider": "TypeSafe",
            "answers": {
                "relation": {
                    "type": "choice",
                    "choice": "cause",
                    "confidence": 0.8,
                    "probabilities": probabilities,
                },
                "nuclearity": {
                    "type": "choice",
                    "choice": "NN",
                    "confidence": 0.6,
                    "probabilities": {"NS": 0.3, "SN": 0.1, "NN": 0.6},
                },
            },
            "usage": {"input_tokens": 10, "output_tokens": 10},
        }
        raw_response_text = json.dumps(response_body)
        calls: list[tuple[dict[str, object], dict[str, object], str]] = []

        class FakeChoice:
            def __init__(self, *, instructions: str, criteria: dict[str, str]) -> None:
                self.instructions = instructions
                self.criteria = criteria

        class FakeRetryPolicy:
            def __init__(self, *, max_retries: int) -> None:
                self.max_retries = max_retries

        class FakeHTTPResponse:
            status_code = 200
            text = raw_response_text
            headers: dict[str, str] = {}

        class FakeResponse:
            raw_http_response = FakeHTTPResponse()

        class FakeClient:
            def __init__(
                self,
                *,
                api_key: str,
                base_url: str,
                retry: FakeRetryPolicy,
            ) -> None:
                self_outer.assertEqual(api_key, "offline-openrouter-secret")
                self_outer.assertEqual(base_url, "https://openrouter.ai/api")
                self.retry = retry

            def __enter__(self) -> FakeClient:
                return self

            def __exit__(self, *_: object) -> bool:
                return False

            def system_one(
                self,
                *,
                state: dict[str, str],
                questions: dict[str, FakeChoice],
                model: str,
            ) -> FakeResponse:
                calls.append((state, questions, model))
                self_outer.assertEqual(set(questions), {"relation", "nuclearity"})
                self_outer.assertEqual(model, "jev-1.13")
                self_outer.assertEqual(self.retry.max_retries, 0)
                return FakeResponse()

        fake_sdk = types.ModuleType("typesafe_sdk")
        fake_sdk.Choice = FakeChoice
        fake_sdk.RetryPolicy = FakeRetryPolicy
        fake_sdk.TypeSafeClient = FakeClient
        fake_sdk.TypeSafeAPIError = type("TypeSafeAPIError", (Exception,), {})

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            args = Namespace(
                input=experiment.ROOT / "data" / "example.jsonl",
                output=base / "predictions.jsonl",
                cache=base / "cache" / "raw_responses.jsonl",
                relations=experiment.DEFAULT_RELATIONS,
                provider="openrouter",
                model="jev-1.13",
            )
            self_outer = self
            output = io.StringIO()
            with (
                patch.dict(sys.modules, {"typesafe_sdk": fake_sdk}),
                patch.dict(
                    os.environ,
                    {
                        "OPENROUTER_API_KEY": "offline-openrouter-secret",
                        "TYPESAFE_API_KEY": "offline-typesafe-secret",
                    },
                    clear=True,
                ),
                contextlib.redirect_stdout(output),
            ):
                experiment.run(args)
                first_report = json.loads(output.getvalue())
                first_prediction = json.loads(args.output.read_text(encoding="utf-8"))
                cached = json.loads(args.cache.read_text(encoding="utf-8"))

                output.seek(0)
                output.truncate(0)
                args.output = base / "predictions-from-cache.jsonl"
                experiment.run(args)
                second_prediction = json.loads(args.output.read_text(encoding="utf-8"))
                serialized_outputs = (
                    args.output.read_text(encoding="utf-8")
                    + args.cache.read_text(encoding="utf-8")
                    + output.getvalue()
                )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][2], "jev-1.13")
        self.assertEqual(json.loads(cached["raw_response_text"]), response_body)
        self.assertEqual(cached["provider"], "openrouter")
        self.assertIsNone(cached["request_id"])
        self.assertEqual(first_prediction["predicted_relation"], "cause")
        self.assertEqual(first_prediction["predicted_nuclearity"], "NN")
        self.assertEqual(first_prediction["provider"], "openrouter")
        self.assertEqual(first_prediction["model"], "jev-1.13")
        self.assertEqual(first_prediction["response_model"], "typesafe/jev-1.13-20260917")
        self.assertEqual(
            first_prediction["relation_probabilities"],
            probabilities,
        )
        self.assertEqual(
            first_prediction["nuclearity_probabilities"],
            {"NS": 0.3, "SN": 0.1, "NN": 0.6},
        )
        self.assertEqual(first_prediction["gold_relation"], "cause")
        self.assertEqual(first_prediction["gold_nuclearity"], "NS")
        self.assertFalse(first_prediction["cache_hit"])
        self.assertTrue(second_prediction["cache_hit"])
        self.assertEqual(first_prediction["formulation"], "independent")
        legacy_prediction = dict(first_prediction)
        legacy_prediction.pop("formulation")
        legacy_report = experiment.evaluate_predictions(
            [legacy_prediction],
            self.relation_labels,
        )
        self.assertNotIn("joint", legacy_report)
        self.assertEqual(legacy_report["relation"], first_report["relation"])
        self.assertEqual(first_report["relation"]["accuracy"], 1.0)
        self.assertEqual(first_report["nuclearity"]["accuracy"], 0.0)
        self.assertNotIn("offline-openrouter-secret", serialized_outputs)
        self.assertNotIn("offline-typesafe-secret", serialized_outputs)

    def test_existing_prediction_output_fails_before_client_setup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            existing_output = base / "predictions.jsonl"
            original_contents = '{"previous":"experiment output"}\n'
            existing_output.write_text(original_contents, encoding="utf-8")
            args = Namespace(
                input=experiment.ROOT / "data" / "example.jsonl",
                output=existing_output,
                cache=base / "cache" / "raw_responses.jsonl",
                relations=experiment.DEFAULT_RELATIONS,
                provider="openrouter",
                model="jev-1.13",
            )

            with patch.object(
                experiment,
                "create_client",
                side_effect=AssertionError("API client setup must not be reached"),
            ) as create_client:
                with self.assertRaisesRegex(
                    FileExistsError,
                    r"already exists.*Existing experiment outputs are not overwritten.*new output path",
                ):
                    experiment.run(args)

            create_client.assert_not_called()
            self.assertEqual(
                existing_output.read_text(encoding="utf-8"),
                original_contents,
            )


if __name__ == "__main__":
    unittest.main()
