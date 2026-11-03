"""Compare two processor differential runs (shim vs official) and report diffs.

Usage: python tests/differential/compare_processor_runs.py run_a.json run_b.json
Exit code 0 = all outputs, error kinds and error types match (error-message
wording may still differ; reported as warnings), 1 = differences (listed) or
usage error.
"""
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    a_path, b_path = map(Path, sys.argv[1:])
    a = json.loads(a_path.read_text(encoding="utf-8"))
    b = json.loads(b_path.read_text(encoding="utf-8"))

    print(f"A: {a_path}  impl={a['impl']}  import={a.get('import_method', '?')}")
    print(f"B: {b_path}  impl={b['impl']}  import={b.get('import_method', '?')}")
    print(f"A versions: {a['versions']}")
    print(f"B versions: {b['versions']}")
    print(f"PYTHONHASHSEED: A={a['pythonhashseed']} B={b['pythonhashseed']}")
    print()

    diffs = 0
    warnings = 0
    total_steps = 0
    names_a, names_b = list(a["scenarios"]), list(b["scenarios"])
    if names_a != names_b:
        print(f"SCENARIO SETS DIFFER: {names_a} vs {names_b}")
        diffs += 1

    for name in names_a:
        steps_a = a["scenarios"][name]
        steps_b = b["scenarios"].get(name, [])
        for i, (sa, sb) in enumerate(zip(steps_a, steps_b)):
            total_steps += 1
            if "error" in sa or "error" in sb:
                kind_a = "error" if "error" in sa else "output"
                kind_b = "error" if "error" in sb else "output"
                if kind_a != kind_b:
                    diffs += 1
                    print(f"DIFF scenario={name} step={i} op={sa['op']}: kind {kind_a} vs {kind_b}")
                    print(f"  A: {sa!r}")
                    print(f"  B: {sb!r}")
                elif sa["error_type"] != sb["error_type"]:
                    diffs += 1
                    print(f"DIFF scenario={name} step={i} op={sa['op']}: error_type "
                          f"{sa['error_type']} vs {sb['error_type']}")
                    print(f"  A: {sa['error']}")
                    print(f"  B: {sb['error']}")
                elif sa.get("error_msg") != sb.get("error_msg"):
                    # Same exception type, different wording (Cython vs CPython
                    # unpack errors) - reported, not a failure.
                    warnings += 1
                    print(f"WARN scenario={name} step={i} op={sa['op']}: same error type "
                          f"{sa['error_type']}, wording differs")
                    print(f"  A: {sa['error']}")
                    print(f"  B: {sb['error']}")
            else:
                oa, ob = sa.get("output"), sb.get("output")
                if oa != ob:
                    diffs += 1
                    print(f"DIFF scenario={name} step={i} op={sa['op']}")
                    print(f"  A: {oa!r}")
                    print(f"  B: {ob!r}")
        if len(steps_a) != len(steps_b):
            diffs += 1
            print(f"DIFF scenario={name}: step count {len(steps_a)} vs {len(steps_b)}")

    print(f"\n{total_steps} steps compared across {len(names_a)} scenarios -> "
          f"{diffs} differences, {warnings} wording-only warnings")
    if diffs == 0:
        if warnings:
            print(f"RESULT: MATCH - outputs identical on all steps; {warnings} error "
                  f"message(s) differ in wording only (same exception type)")
        else:
            print("RESULT: IDENTICAL - Windows shim matches the official processor on all cases")
        return 0
    print("RESULT: MISMATCH")
    return 1


if __name__ == "__main__":
    sys.exit(main())
