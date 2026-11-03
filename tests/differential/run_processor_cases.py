"""Run reproducible IndicProcessor differential cases against one implementation.

Usage:
    python tests/differential/run_processor_cases.py --impl shim   --out win.json
    wsl: ~/itv2_venv/bin/python .../run_processor_cases.py --impl official --out off.json

--impl shim      : the Windows pure-Python port (src/indic_processor.py)
--impl official  : the official Cython IndicTransToolkit build (WSL2)

PYTHONHASHSEED must be 0 for byte-identical results (set-iteration order in the
official placeholder logic); the script refuses to run otherwise unless
--allow-any-seed is given. Outputs are JSON files later compared with
compare_processor_runs.py.
"""
import argparse
import importlib.metadata
import json
import platform
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def get_versions():
    vers = {"python": sys.version.split()[0], "platform": platform.platform()}
    for pkg in ["regex", "sacremoses", "indic-nlp-library-itt", "transformers", "sentencepiece", "tqdm"]:
        try:
            vers[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            vers[pkg] = "NOT-INSTALLED"
    return vers


def load_processor_class(impl):
    """Return (IndicProcessor, import_method)."""
    if impl == "shim":
        sys.path.insert(0, str(REPO))
        from src.indic_processor import IndicProcessor
        return IndicProcessor, "shim_src.indic_processor"
    if impl == "official":
        # Preferred: canonical package import.
        try:
            from IndicTransToolkit import IndicProcessor
            return IndicProcessor, "package_IndicTransToolkit"
        except ImportError as e:
            # Known issue (verified 2026-10-29, Windows + WSL): IndicTransToolkit
            # 1.1.1 __init__ imports collator/evaluator which require
            # transformers<5 (transformers 5.x has no transformers.tokenization_utils).
            # The official processor Cython extension itself does NOT depend on
            # transformers, so load the compiled extension directly - identical code.
            import glob
            import importlib.metadata as md
            import importlib.util

            dist = md.distribution("indictranstoolkit")
            base = Path(dist.locate_file("IndicTransToolkit"))
            so = sorted(glob.glob(str(base / "processor*.so")))
            if not so:
                raise
            spec = importlib.util.spec_from_file_location("official_processor.processor", so[0])
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.IndicProcessor, f"extension_direct ({Path(so[0]).name}); package import failed: {e}"
    raise SystemExit(f"unknown --impl {impl!r}")


def run_step(Processor, op_cls, step):
    """Execute one step; return dict with either output or error (never raise)."""
    rec = {"op": step["op"]}
    try:
        if step["op"] == "preprocess":
            kwargs = {}
            if "is_target" in step:
                kwargs["is_target"] = step["is_target"]
            out = op_cls.preprocess_batch(
                step["batch"], step["src_lang"], step.get("tgt_lang"), **kwargs
            )
        elif step["op"] == "postprocess":
            sents = step["sents"]
            if isinstance(sents, dict) and "ref" in sents:
                raise KeyError("postprocess ref must be resolved before run_step")
            kwargs = {}
            if "num_return_sequences" in step:
                kwargs["num_return_sequences"] = step["num_return_sequences"]
            out = op_cls.postprocess_batch(sents, lang=step["lang"], **kwargs)
        else:
            raise ValueError(f"unknown op {step['op']}")
        rec["output"] = out
    except Exception as e:  # noqa: BLE001 - differential harness records all errors
        rec["error_type"] = type(e).__name__
        rec["error_msg"] = str(e)
        rec["error"] = f"{type(e).__name__}: {e}"
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--impl", choices=["shim", "official"], required=True)
    ap.add_argument("--cases", default=str(Path(__file__).with_name("cases.json")))
    ap.add_argument("--out", required=True)
    ap.add_argument("--allow-any-seed", action="store_true")
    args = ap.parse_args()

    seed = __import__("os").environ.get("PYTHONHASHSEED")
    if seed != "0" and not args.allow_any_seed:
        raise SystemExit(
            f"PYTHONHASHSEED is {seed!r}, must be '0' for reproducible placeholder ordering"
        )

    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    Processor, import_method = load_processor_class(args.impl)

    results = {}
    for scenario in cases["scenarios"]:
        ip = Processor(inference=True)  # fresh processor => fresh placeholder queue
        steps_out = []
        outputs_by_index = []
        for i, step in enumerate(scenario["steps"]):
            step = dict(step)
            if step["op"] == "note":
                steps_out.append({"op": "note", "comment": step.get("comment", "")})
                outputs_by_index.append(None)
                continue
            # resolve {"ref": n} against previous outputs of this scenario
            if isinstance(step.get("sents"), dict) and "ref" in step["sents"]:
                step["sents"] = outputs_by_index[step["sents"]["ref"]]
            print(
                f"[{args.impl}] {scenario['name']} step {i}: {step['op']}"
                + (f" src={step.get('src_lang', step.get('lang'))} n={len(step.get('batch', step.get('sents', [])))}"),
                file=sys.stderr,
                flush=True,
            )
            rec = run_step(Processor, ip, step)
            steps_out.append(rec)
            outputs_by_index.append(rec.get("output"))
        results[scenario["name"]] = steps_out

    payload = {
        "impl": args.impl,
        "processor_class": f"{Processor.__module__}.{Processor.__name__}",
        "import_method": import_method,
        "pythonhashseed": seed,
        "versions": get_versions(),
        "scenarios": results,
    }
    Path(args.out).write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    n_steps = sum(len(v) for v in results.values())
    n_err = sum(1 for v in results.values() for r in v if "error" in r)
    print(f"[{args.impl}] wrote {args.out}: {len(results)} scenarios, {n_steps} steps, {n_err} recorded errors")


if __name__ == "__main__":
    main()
