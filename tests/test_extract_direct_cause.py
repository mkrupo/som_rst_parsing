import json
from pathlib import Path
import tempfile
import unittest

from src.extract_direct_cause import extract_records, extract_to_jsonl


class DirectCauseExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.rst_dir = self.root / "rst"
        self.rst_dir.mkdir()

    def write_rs3(self, filename: str, body: str) -> Path:
        path = self.rst_dir / filename
        path.write_text(f"<rst><body>{body}</body></rst>", encoding="utf-8")
        return path

    def test_direct_cause_pairs_use_text_order_and_structural_nuclearity(self) -> None:
        self.write_rs3(
            "micro_test.rs3",
            """
            <segment id="10" parent="0" relname="span">Nucleus   first.</segment>
            <segment id="11" parent="10" relname="cause">Satellite\n after.</segment>
            <segment id="12" parent="13" relname="cause">Satellite before.</segment>
            <segment id="13" parent="0" relname="span">Nucleus later.</segment>
            <segment id="14" parent="10" relname="span">Last EDU.</segment>
            """,
        )

        rows = extract_records(self.rst_dir)

        self.assertEqual(len(rows), 2)
        ns, sn = rows
        self.assertEqual(ns["id"], "micro_test.rs3:sat-11:nuc-10")
        self.assertEqual(ns["span_a"], "Nucleus first.")
        self.assertEqual(ns["span_b"], "Satellite after.")
        self.assertEqual(ns["gold_nuclearity"], "NS")
        self.assertEqual(ns["gold_relation"], "cause")
        self.assertEqual(
            ns["document_context"],
            "Nucleus first. Satellite after. Satellite before. Nucleus later. Last EDU.",
        )
        self.assertEqual(ns["source_file"], "micro_test.rs3")
        self.assertEqual(ns["satellite_segment_id"], "11")
        self.assertEqual(ns["nucleus_segment_id"], "10")

        self.assertEqual(sn["id"], "micro_test.rs3:sat-12:nuc-13")
        self.assertEqual(sn["span_a"], "Satellite before.")
        self.assertEqual(sn["span_b"], "Nucleus later.")
        self.assertEqual(sn["gold_nuclearity"], "SN")
        self.assertEqual(sn["gold_relation"], "cause")

    def test_group_parent_and_non_cause_relation_are_excluded(self) -> None:
        self.write_rs3(
            "excluded.rs3",
            """
            <segment id="1" parent="0" relname="span">Nucleus.</segment>
            <segment id="2" parent="group-1" relname="cause">Group satellite.</segment>
            <segment id="3" parent="1" relname="reason">Other relation.</segment>
            <group id="group-1" type="span" />
            """,
        )

        self.assertEqual(extract_records(self.rst_dir), [])

    def test_jsonl_creation_and_existing_output_protection(self) -> None:
        self.write_rs3(
            "one.rs3",
            '<segment id="1" parent="0" relname="span">Nucleus.</segment>'
            '<segment id="2" parent="1" relname="cause">Satellite.</segment>',
        )
        output = self.root / "data" / "argmicrotexts_cause_direct.jsonl"

        self.assertEqual(extract_to_jsonl(self.rst_dir, output), 1)
        original = output.read_text(encoding="utf-8")
        record = json.loads(original)
        self.assertEqual(record["id"], "one.rs3:sat-2:nuc-1")

        with self.assertRaisesRegex(FileExistsError, "Refusing to overwrite"):
            extract_to_jsonl(self.rst_dir, output)
        self.assertEqual(output.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
