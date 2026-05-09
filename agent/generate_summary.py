"""
generate_summary.py
Creates a compact markdown summary from attributed telemetry output.
"""

import argparse
import json
import os


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def top_list(rows, key, count=5):
    return sorted(rows, key=lambda r: (-r.get(key, 0), -r.get("operations", 0)))[:count]


def build_summary(payload):
    feature_rows = payload.get("feature_attribution", [])
    top_tenants = payload.get("top_tenants_by_feature", [])
    failures = payload.get("failures_by_feature", [])

    features = sorted({row.get("feature", "Unknown") for row in feature_rows})
    tenants = sorted({row.get("tenant_id", "unknown-tenant") for row in feature_rows})
    workspaces = sorted({row.get("workspace_id", "unknown-workspace") for row in feature_rows})

    lines = [
        f"# Fabric DW Telemetry Summary ({payload.get('report_date', 'N/A')})",
        "",
        "## Attribution Coverage",
        f"- Telemetry rows processed: **{payload.get('telemetry_row_count', 0)}**",
        f"- Enriched rows: **{payload.get('enriched_row_count', 0)}**",
        f"- Features observed: **{len(features)}**",
        f"- Tenants observed: **{len(tenants)}**",
        f"- Workspaces observed: **{len(workspaces)}**",
        "",
        "## Top Tenant Feature Usage",
    ]

    top_usage = top_list(top_tenants, "operations", 5)
    if top_usage:
        for row in top_usage:
            lines.append(
                f"- **{row.get('feature')}** • tenant `{row.get('tenant_id')}`: "
                f"{row.get('operations', 0)} ops, {row.get('failures', 0)} failures "
                f"({row.get('failure_rate', 0)}%)"
            )
    else:
        lines.append("- No attributed usage rows found.")

    lines.extend(["", "## Top Failure Hotspots"])
    top_failures = top_list(failures, "failures", 5)
    if top_failures:
        for row in top_failures:
            lines.append(
                f"- **{row.get('feature')}** • tenant `{row.get('tenant_id')}` • workspace "
                f"`{row.get('workspace_id')}` ({row.get('customer_name', 'Unknown')}): "
                f"{row.get('failures', 0)} failures / {row.get('operations', 0)} ops"
            )
    else:
        lines.append("- No feature failures found.")

    return "\n".join(lines) + "\n"


def run(args):
    payload = load_json(args.telemetry)
    summary = build_summary(payload)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        f.write(summary)
    print(f"Summary generated: {args.output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate markdown summary from attributed telemetry payload")
    parser.add_argument("--telemetry", required=True, help="Path to telemetry payload JSON")
    parser.add_argument("--mapping", help="Unused compatibility argument for workflow scaffolding", default="")
    parser.add_argument("--prompt", help="Unused compatibility argument for workflow scaffolding", default="")
    parser.add_argument("--output", required=True, help="Output markdown path")
    run(parser.parse_args())
