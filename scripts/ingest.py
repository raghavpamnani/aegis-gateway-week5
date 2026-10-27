"""Validate a complete replacement fictional corpus. Does not accept arbitrary code."""

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aegis.models import Document

parser = argparse.ArgumentParser()
parser.add_argument("source", type=Path)
args = parser.parse_args()
if args.source.stat().st_size > 256000:
    raise SystemExit("Corpus too large for the local lab")
docs = [Document.model_validate(d) for d in json.loads(args.source.read_text())]
if not 1 <= len(docs) <= 100 or len({d.id for d in docs}) != len(docs):
    raise SystemExit("Require 1-100 documents with unique IDs")
for d in docs:
    if re.search(
        r"ignore (?:all |previous |prior )?instructions|system prompt|api[_ -]?key\s*[:=]", d.body, re.I
    ):
        raise SystemExit(f"Quarantined {d.id}: review potential instructions or secret material")
target = Path(__file__).resolve().parents[1] / "data/corpus.json"
temporary = target.with_suffix(".pending")
temporary.write_text(json.dumps([d.model_dump() for d in docs], indent=2) + "\n")
os.replace(temporary, target)
print("Validated", len(docs), "documents. Restart app to load corpus; cache namespace changes automatically.")
