import argparse
import json
import math
import sys
from pathlib import Path


def _sanitize_nans(obj):
    """Recursively replace float('nan') with None for strict JSON schema checks."""
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if isinstance(obj, list):
        return [_sanitize_nans(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _sanitize_nans(v) for k, v in obj.items()}
    return obj


def load_json(path: Path):
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def validate_with_jsonschema(instance, schema):
    try:
        import jsonschema  # type: ignore
    except Exception:
        print("jsonschema is not installed; running a lightweight structural check...", file=sys.stderr)
        # Minimal checks: type and required keys
        required = schema.get("required", [])
        props = schema.get("properties", {})
        missing = [k for k in required if k not in instance]
        if missing:
            raise SystemExit(f"Missing required keys: {missing}")
        unknown = [k for k in instance.keys() if k not in props]
        if unknown:
            print(f"Warning: unknown keys present (not in schema): {unknown}", file=sys.stderr)
        return True

    jsonschema.validate(instance=instance, schema=schema)
    return True


def main(argv=None):
    p = argparse.ArgumentParser(description="Validate rtgamma report JSON against schema")
    p.add_argument("report", nargs="+", help="Path(s) to report JSON to validate")
    p.add_argument("--schema", default=str(Path("docs/openspec/report.schema.json")), help="Path to JSON schema")
    p.add_argument("--sanitize-nan", action="store_true", help="Replace NaN with null before validation")
    args = p.parse_args(argv)

    schema_path = Path(args.schema)
    if not schema_path.exists():
        raise SystemExit(f"Schema not found: {schema_path}")
    schema = load_json(schema_path)

    ok_all = True
    for rpt in args.report:
        rpt_path = Path(rpt)
        if not rpt_path.exists():
            print(f"Not found: {rpt_path}", file=sys.stderr)
            ok_all = False
            continue
        data = load_json(rpt_path)
        if args.sanitize_nan:
            data = _sanitize_nans(data)
        try:
            validate_with_jsonschema(data, schema)
            print(f"OK: {rpt_path}")
        except Exception as e:
            ok_all = False
            print(f"FAIL: {rpt_path} -> {e}", file=sys.stderr)

    if not ok_all:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

