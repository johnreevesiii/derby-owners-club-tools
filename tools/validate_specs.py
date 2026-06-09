#!/usr/bin/env python3
"""Validate DOC ROM version specs against rom-spec.schema.json.

Full validation when `jsonschema` is installed; otherwise a built-in structural
check runs and says so. Exit code 0 = all valid, 1 = any failure.

Usage:
    python tools/validate_specs.py
"""
import json
import sys
from pathlib import Path

VERSIONS = Path(__file__).resolve().parent.parent / "versions"
SPECS = ["rev-c.json", "rev-d.json", "doc-2000.json", "doc-99.json"]


def load(name):
    return json.loads((VERSIONS / name).read_text(encoding="utf-8"))


def validate_full(schema):
    from jsonschema import Draft202012Validator
    Draft202012Validator.check_schema(schema)
    v = Draft202012Validator(schema)
    ok = True
    for s in SPECS:
        errs = sorted(v.iter_errors(load(s)), key=lambda e: list(e.path))
        if errs:
            ok = False
            print(f"FAIL {s}: {len(errs)} error(s)")
            for e in errs:
                loc = "/".join(str(p) for p in e.path) or "(root)"
                print(f"     {loc}: {e.message}")
        else:
            print(f"PASS {s}")
    return ok


def validate_structural():
    """Dependency-free fallback: checks the load-bearing invariants only."""
    import re
    sha_re = re.compile(r"^[0-9a-f]{64}$")
    sig_re = re.compile(r"^[0-9a-f]{32}$")
    hex_re = re.compile(r"^0x[0-9a-fA-F]+$")
    frames = {"file", "runtime", "ghidra"}
    req_tables = ["roster", "names", "sire", "dam", "g1", "tracks",
                  "foods", "strings", "racePace", "personality"]
    ok = True
    for s in SPECS:
        problems = []
        d = load(s)
        ident = d.get("identity", {})
        if not sha_re.match(ident.get("sha256", "")):
            problems.append("identity.sha256 not a 64-hex string")
        sig = ident.get("signature", {})
        if not sig_re.match(sig.get("bytes", "")):
            problems.append("identity.signature.bytes not a 32-hex string")
        if d.get("identity", {}).get("romSize") != 4194304:
            problems.append("identity.romSize != 4194304")
        tables = d.get("tables", {})
        for t in req_tables:
            if t not in tables:
                problems.append(f"tables.{t} missing")
                continue
            entry = tables[t]
            off = entry.get("offset", {})
            if off.get("frame") not in frames:
                problems.append(f"tables.{t}.offset.frame invalid")
            val = off.get("value")
            if val is not None and not hex_re.match(val):
                problems.append(f"tables.{t}.offset.value not hex/null")
            if not isinstance(entry.get("verified"), bool):
                problems.append(f"tables.{t}.verified not boolean")
            if not entry.get("source"):
                problems.append(f"tables.{t}.source empty")
        if problems:
            ok = False
            print(f"FAIL {s}: {len(problems)} issue(s)")
            for p in problems:
                print(f"     {p}")
        else:
            print(f"PASS {s} (structural)")
    return ok


def main():
    schema = load("rom-spec.schema.json")
    json.loads((VERSIONS / "_shared.json").read_text(encoding="utf-8"))  # parse check
    try:
        import jsonschema  # noqa: F401
        print("Validator: jsonschema (full Draft 2020-12)\n")
        ok = validate_full(schema)
    except ImportError:
        print("Validator: built-in structural check (install 'jsonschema' for full validation)\n")
        ok = validate_structural()
    print("\nALL VALID" if ok else "\nFAILURES PRESENT")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
