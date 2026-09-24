"""Extract direct EDU-to-EDU cause relations from a local ArgMicrotexts RS3 corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def _local_name(tag: str) -> str:
    """Return an XML tag name without an optional namespace prefix."""
    return tag.rsplit("}", 1)[-1]


def _normalized_text(element: ET.Element) -> str:
    return " ".join("".join(element.itertext()).split())


def extract_records(rst_dir: Path) -> list[dict[str, str]]:
    """Return direct segment-to-segment cause relations in deterministic order."""
    if not rst_dir.is_dir():
        raise ValueError(f"RST directory does not exist: {rst_dir}")

    records: list[dict[str, str]] = []
    rs3_files = sorted(rst_dir.rglob("*.rs3"), key=lambda path: path.as_posix())
    for source_path in rs3_files:
        source_file = source_path.relative_to(rst_dir).as_posix()
        try:
            root = ET.parse(source_path).getroot()
        except (OSError, ET.ParseError) as exc:
            raise ValueError(f"Could not parse RS3 file {source_path}: {exc}") from exc

        body = next((node for node in root.iter() if _local_name(node.tag) == "body"), None)
        if body is None:
            raise ValueError(f"RS3 file has no body element: {source_path}")

        segments = [node for node in body.iter() if _local_name(node.tag) == "segment"]
        segment_ids: dict[str, int] = {}
        for index, segment in enumerate(segments):
            segment_id = segment.get("id")
            if not segment_id:
                raise ValueError(f"Segment without an id in {source_path}")
            if segment_id in segment_ids:
                raise ValueError(f"Duplicate segment id {segment_id!r} in {source_path}")
            segment_ids[segment_id] = index

        texts = [_normalized_text(segment) for segment in segments]
        document_context = " ".join(text for text in texts if text)

        for satellite_index, satellite in enumerate(segments):
            if satellite.get("relname") != "cause":
                continue

            nucleus_id = satellite.get("parent")
            nucleus_index = segment_ids.get(nucleus_id or "")
            if nucleus_index is None or nucleus_index == satellite_index:
                # A missing segment parent is a group/root parent or malformed edge.
                continue

            satellite_id = satellite.get("id")
            assert satellite_id is not None  # checked while building segment_ids
            if satellite_index < nucleus_index:
                span_a, span_b = texts[satellite_index], texts[nucleus_index]
                nuclearity = "SN"
            else:
                span_a, span_b = texts[nucleus_index], texts[satellite_index]
                nuclearity = "NS"

            records.append(
                {
                    "id": f"{source_file}:sat-{satellite_id}:nuc-{nucleus_id}",
                    "document_context": document_context,
                    "span_a": span_a,
                    "span_b": span_b,
                    "gold_relation": "cause",
                    "gold_nuclearity": nuclearity,
                    "source_file": source_file,
                    "satellite_segment_id": satellite_id,
                    "nucleus_segment_id": nucleus_id or "",
                }
            )

    return records


def extract_to_jsonl(rst_dir: Path, output: Path) -> int:
    """Extract rows and create a JSONL output without replacing an existing file."""
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing output file: {output}")

    records = extract_records(rst_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x", encoding="utf-8") as stream:
            for record in records:
                stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    except FileExistsError as exc:
        # Exclusive creation also protects against a file appearing after the check.
        raise FileExistsError(
            f"Refusing to overwrite existing output file: {output}"
        ) from exc
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract direct EDU-to-EDU cause relations from local RS3 files."
    )
    parser.add_argument("--rst-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        count = extract_to_jsonl(args.rst_dir, args.output)
    except (FileExistsError, OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(f"Wrote {count} records to {args.output}")


if __name__ == "__main__":
    main()
