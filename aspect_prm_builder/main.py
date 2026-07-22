"""Command-line interface for the ASPECT .prm middleware.

Usage examples:

    # Interactive mode
    python -m aspect_prm_builder --output my_model.prm

    # Generate from a JSON/YAML answer file
    python -m aspect_prm_builder --answers answers.json --output my_model.prm

    # Read an existing cookbook and re-render it
    python -m aspect_prm_builder --from cookbook.prm --output rewritten.prm

    # Validate answers without writing
    python -m aspect_prm_builder --answers answers.json --validate
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from . import assembler, engine, schema, validator


def load_answers(path: str) -> Dict[str, Any]:
    p = Path(path)
    if p.suffix in (".json", ".prm"):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    raise ValueError(f"Unsupported answer format: {p.suffix}")


def save_answers(path: str, answers: Dict[str, Any]):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(answers, f, indent=2, ensure_ascii=False)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Interactive middleware for building ASPECT .prm files"
    )
    parser.add_argument("--output", "-o", help="Output .prm file path")
    parser.add_argument("--answers", "-a", help="Path to JSON answer file")
    parser.add_argument("--from", "-f", dest="from_prm", help="Read an existing .prm file")
    parser.add_argument("--validate", action="store_true", help="Validate answers and exit")
    parser.add_argument("--save-answers", help="Save collected answers to a JSON file")
    parser.add_argument(
        "--strict", action="store_true", help="Treat missing optional sections as errors"
    )
    parser.add_argument(
        "--title", help="Title comment for the generated .prm file"
    )
    parser.add_argument(
        "--header", help="Header text for the generated .prm file"
    )
    parser.add_argument(
        "--export-schema",
        help="Export the parameter schema to a JSON file and exit",
    )
    parser.add_argument(
        "--force", action="store_true", help="Write output even if validation fails"
    )

    args = parser.parse_args(argv)

    if args.export_schema:
        s = schema.build_schema()
        with open(args.export_schema, "w", encoding="utf-8") as f:
            json.dump(schema.schema_to_json(s), f, indent=2, ensure_ascii=False)
        print(f"Exported schema to {args.export_schema}")
        return 0

    if args.from_prm:
        text = Path(args.from_prm).read_text(encoding="utf-8")
        answers = assembler.parse_prm(text)
    elif args.answers:
        answers = load_answers(args.answers)
    else:
        answers = engine.GuidedBuildSession().run()

    if args.save_answers:
        save_answers(args.save_answers, answers)

    errors = validator.validate_answers(answers, schema.build_schema(), strict=args.strict)
    if errors:
        for path, msg in errors:
            print(f"ERROR: {path}: {msg}", file=sys.stderr)
        if args.validate or not args.force:
            return 1

    if args.validate:
        print("Validation passed.")
        return 0

    if not args.output:
        args.output = "output.prm"

    header = args.header
    if not header and args.title:
        header = args.title

    assembler.write_prm(args.output, answers, schema.build_schema(), header=header)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
