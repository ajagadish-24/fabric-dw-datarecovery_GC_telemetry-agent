"""
generate_dashboard.py
Reads KQL output JSON files and hydrates the daily_health.html template
with live data, KPI calculations, alerts, and health status.

Usage:
  python generate_dashboard.py \
    --recovery-data recovery_data.json \
    --gc-data gc_data.json \
    --retention-data retention_data.json \
    --thresholds config/thresholds.json \
    --template dashboard/daily_health.html \
    --output output/daily_health.html
"""

import argparse
import json
import os
from datetime import datetime


FEATURE_LABELS = {
    "Restore": "Restore",
    "TimeTravelQuery": "Time Travel",
    "TableClone": "Table Clone",
    "TableClonePIT": "Clone (PIT)",
    "WarehouseClone": "DW Clone",
    "WarehouseRecovery": "DW Recovery",
    "GC": "GC",
    "Retention": "Retention",
}

POWERBI_URL = "https://msit.powerbi.com/groups/me/reports/69bc811a-2f14-40d8-9ecd-a672c13f12ea/d82e71a98be8a5972d8e?experience=power-bi"


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def compute_health_status(gc_data, recovery_data, thresholds):
    """Return (label, emoji, color) based on threshold checks."""
    alerts = []

    for row in gc_data:
        rate = row.get("FailureRate", 0)
        if rate > thresholds.get("gc_failure_rate_threshold_pct", 5):
            alerts.append({"level": "critical", "message": f"GC failure rate at {rate}% (threshold: {thresholds['gc_failure_rate_threshold_pct']}%)"})
        backlog = row.get("BacklogGrowthPct", 0)
        if backlog > thresholds.get("gc_backlog_growth_pct", 20):
            alerts.append({"level": "warning", "message": f"GC backlog growing at {backlog}% day-over-day"})

    for row in recovery_data:
        rate = row.get("FailureRate", 0)
        op = row.get("OperationName", "unknown")
        multiplier = thresholds.get("restore_failure_rate_multiplier", 2)
        if rate > thresholds.get("gc_failure_rate_threshold_pct", 5) * multiplier:
            alerts.append({"level": "critical", "message": f"{op} failure rate at {rate}%"})

    has_critical = any(a["level"] == "critical" for a in alerts)
    has_warning = any(a["level"] == "warning" for a in alerts)

    if has_critical:
        return "CRITICAL", "🔴", "#da3633", alerts
    elif has_warning:
        return "WARNING", "🟡", "#9e6a03", alerts
    return "HEALTHY", "🟢", "#238636", alerts


def build_kpi_data(recovery_data, gc_data, retention_data):
    """Aggregate KPI values."""
    total_ops = sum(r.get("TotalOperations", r.get("TotalRuns", 0)) for r in recovery_data + gc_data)
    total_fail = sum(r.get("Failures", 0) for r in recovery_data + gc_data)
    fail_rate = round(total_fail / total_ops * 100, 2) if total_ops > 0 else 0
    p95_values = [r.get("P95LatencyMs", 0) for r in recovery_data + gc_data if r.get("P95LatencyMs", 0) > 0]
    avg_p95 = round(sum(p95_values) / len(p95_values), 0) if p95_values else 0
    gc_backlog = sum(r.get("BacklogGB", 0) for r in gc_data)
    impacted = sum(r.get("ImpactedCustomers", 0) for r in recovery_data + gc_data)
    features = len(set(r.get("OperationName", "GC") for r in recovery_data + gc_data))

    return {
        "total_ops": total_ops,
        "failure_rate": fail_rate,
        "avg_p95": avg_p95,
        "gc_backlog": gc_backlog,
        "impacted": impacted,
        "active_features": features,
    }


def build_feature_data(recovery_data, gc_data):
    """Build per-feature data for bar charts and tabs."""
    features = []
    for row in recovery_data + gc_data:
        op = row.get("OperationName", "GC")
        features.append({
            "name": FEATURE_LABELS.get(op, op),
            "ops": row.get("TotalOperations", row.get("TotalRuns", 0)),
            "failures": row.get("Failures", 0),
            "failure_rate": row.get("FailureRate", 0),
            "p95": row.get("P95LatencyMs", 0),
        })
    return features


def build_retention_data(retention_data):
    """Build retention bucket data for donut chart."""
    buckets = []
    for row in retention_data:
        buckets.append({
            "bucket": row.get("RetentionBucket", ""),
            "count": row.get("CustomerCount", 0),
        })
    return buckets


def generate_dashboard(args):
    recovery_data = load_json(args.recovery_data)
    gc_data = load_json(args.gc_data)
    retention_data = load_json(args.retention_data)
    thresholds = load_json(args.thresholds)

    with open(args.template, "r") as f:
        template = f.read()

    report_date = datetime.utcnow().strftime("%B %d, %Y")
    status_label, status_emoji, status_color, alerts = compute_health_status(gc_data, recovery_data, thresholds)
    kpi = build_kpi_data(recovery_data, gc_data, retention_data)
    features = build_feature_data(recovery_data, gc_data)
    retention = build_retention_data(retention_data)

    # Replace template placeholders
    html = template
    html = html.replace("{{REPORT_DATE}}", report_date)
    html = html.replace("{{STATUS_LABEL}}", status_label)
    html = html.replace("{{STATUS_EMOJI}}", status_emoji)
    html = html.replace("{{STATUS_COLOR}}", status_color)
    html = html.replace("{{POWERBI_URL}}", POWERBI_URL)
    html = html.replace("{{KPI_DATA}}", json.dumps(kpi))
    html = html.replace("{{FEATURE_DATA}}", json.dumps(features))
    html = html.replace("{{RETENTION_DATA}}", json.dumps(retention))
    html = html.replace("{{ALERTS_DATA}}", json.dumps(alerts))

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        f.write(html)

    print(f"Dashboard generated: {args.output}")
    print(f"Health status: {status_emoji} {status_label}")
    print(f"KPIs: {json.dumps(kpi, indent=2)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate interactive HTML dashboard")
    parser.add_argument("--recovery-data", required=True, help="Path to recovery KQL output JSON")
    parser.add_argument("--gc-data", required=True, help="Path to GC KQL output JSON")
    parser.add_argument("--retention-data", required=True, help="Path to retention KQL output JSON")
    parser.add_argument("--thresholds", required=True, help="Path to thresholds.json")
    parser.add_argument("--template", required=True, help="Path to HTML template")
    parser.add_argument("--output", required=True, help="Output HTML file path")
    args = parser.parse_args()
    generate_dashboard(args)
