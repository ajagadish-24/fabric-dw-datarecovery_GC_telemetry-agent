"""
run_kql_queries.py
Loads RTI-oriented telemetry JSON input, enriches with workspace mapping,
and writes feature attribution output consumed by dashboards/emails/summaries.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from agent.attribution import (
    aggregate_feature_attribution,
    enrich_telemetry_rows,
    load_json,
    load_telemetry_rows,
    load_workspace_mapping,
)


def resolve_telemetry_input_path(args):
    if args.telemetry_input:
        return args.telemetry_input
    env_path = os.getenv(args.rti_input_env, "")
    return env_path or None


def run(args):
    mapping = load_workspace_mapping(args.mapping)
    feature_mapping = load_json(args.feature_mapping)
    telemetry_input = resolve_telemetry_input_path(args)
    telemetry_rows = load_telemetry_rows(telemetry_input) if telemetry_input and os.path.exists(telemetry_input) else []
    enriched_rows = enrich_telemetry_rows(telemetry_rows, mapping, feature_mapping)
    attribution = aggregate_feature_attribution(enriched_rows, top_n=args.top_n)

    payload = {
        "report_date": args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "telemetry_row_count": len(telemetry_rows),
        "enriched_row_count": len(enriched_rows),
        "feature_attribution": attribution["feature_attribution"],
        "top_tenants_by_feature": attribution["top_tenants_by_feature"],
        "top_workspaces_by_feature": attribution["top_workspaces_by_feature"],
        "failures_by_feature": attribution["failures_by_feature"],
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Attribution output written: {args.output}")
    print(f"Input rows: {len(telemetry_rows)}, enriched rows: {len(enriched_rows)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate attributed telemetry payload from RTI telemetry input")
    parser.add_argument("--date", help="Report date (YYYY-MM-DD). Defaults to current UTC date.", default="")
    parser.add_argument("--telemetry-input", help="Path to RTI telemetry JSON input artifact", default="")
    parser.add_argument("--mapping", default="config/workspace_mapping.json", help="Path to workspace mapping JSON")
    parser.add_argument("--feature-mapping", default="config/feature_mapping.json", help="Path to feature mapping JSON")
    parser.add_argument("--rti-input-env", default="RTI_TELEMETRY_INPUT", help="Env var name containing telemetry input path")
    parser.add_argument("--top-n", type=int, default=5, help="Top N tenants/workspaces per feature")
    parser.add_argument("--output", required=True, help="Output JSON path")
    run(parser.parse_args())
