"""
generate_email.py
Generates a rich HTML email with embedded KPI cards, feature table,
retention bar, and an "Open Interactive Dashboard" button.

Usage:
  python generate_email.py \
    --recovery-data recovery_data.json \
    --gc-data gc_data.json \
    --retention-data retention_data.json \
    --thresholds config/thresholds.json \
    --dashboard-url https://your-hosting/daily_health.html \
    --agent-summary agent_summary.md \
    --output output/email_body.html
"""

import argparse
import json
import os
from datetime import datetime


POWERBI_DATA_RECOVERY_URL = "https://msit.fabric.microsoft.com/groups/8869af0c-8405-4a99-ab6f-73ad87bf9c0e/reports/d5792894-a260-4877-b670-55aaa120efff/903670727285ffcd6ba4?experience=power-bi"
POWERBI_GC_TELEMETRY_URL = "https://msit.powerbi.com/groups/me/reports/69bc811a-2f14-40d8-9ecd-a672c13f12ea/ReportSectionac6dc9e5740db24be543?experience=power-bi"


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def load_text(path):
    with open(path, "r") as f:
        return f.read()


def compute_health(recovery_data, gc_data, thresholds):
    """Determine health status and return badge color/label."""
    for row in gc_data:
        if row.get("FailureRate", 0) > thresholds["gc_failure_rate_threshold_pct"]:
            return "CRITICAL", "#da3633"
        if row.get("BacklogGrowthPct", 0) > thresholds["gc_backlog_growth_pct"]:
            return "WARNING", "#9e6a03"
    for row in recovery_data:
        baseline = row.get("baseline_failure_rate", 0)
        current = row.get("FailureRate", 0)
        if baseline > 0 and current > baseline * thresholds["restore_failure_rate_multiplier"]:
            return "CRITICAL", "#da3633"
    return "HEALTHY", "#238636"


def failure_rate_color(rate):
    if rate >= 5:
        return "#f85149"
    elif rate >= 2:
        return "#d29922"
    return "#3fb950"


def generate_email(args):
    recovery_data = load_json(args.recovery_data)
    gc_data = load_json(args.gc_data)
    retention_data = load_json(args.retention_data)
    thresholds = load_json(args.thresholds)
    agent_summary = load_text(args.agent_summary)
    dashboard_url = args.dashboard_url

    report_date = datetime.utcnow().strftime("%B %d, %Y")
    status_label, status_color = compute_health(recovery_data, gc_data, thresholds)

    # Aggregate KPIs
    total_ops = sum(r.get("TotalOperations", r.get("TotalRuns", 0)) for r in recovery_data + gc_data)
    total_failures = sum(r.get("Failures", 0) for r in recovery_data + gc_data)
    overall_failure_rate = round(total_failures / total_ops * 100, 2) if total_ops > 0 else 0
    avg_p95 = round(sum(r.get("P95LatencyMs", 0) for r in recovery_data + gc_data) / max(len(recovery_data + gc_data), 1), 0)
    impacted = sum(r.get("ImpactedCustomers", 0) for r in recovery_data + gc_data)

    # Feature breakdown rows
    feature_rows = ""
    for row in recovery_data + gc_data:
        feature = row.get("OperationName", "GC")
        ops = row.get("TotalOperations", row.get("TotalRuns", 0))
        failures = row.get("Failures", 0)
        rate = row.get("FailureRate", 0)
        p95 = row.get("P95LatencyMs", 0)
        color = failure_rate_color(rate)
        feature_rows += f"""
        <tr>
          <td style="padding:10px 16px; border-bottom:1px solid #30363d; color:#e6edf3;">{feature}</td>
          <td style="padding:10px 16px; border-bottom:1px solid #30363d; color:#e6edf3; text-align:right;">{ops:,}</td>
          <td style="padding:10px 16px; border-bottom:1px solid #30363d; color:#e6edf3; text-align:right;">{failures:,}</td>
          <td style="padding:10px 16px; border-bottom:1px solid #30363d; text-align:right;">
            <span style="color:{color}; font-weight:600;">{rate:.2f}%</span>
          </td>
          <td style="padding:10px 16px; border-bottom:1px solid #30363d; color:#e6edf3; text-align:right;">{p95:,.0f} ms</td>
        </tr>"""

    # Retention bar
    total_customers = sum(r.get("CustomerCount", 0) for r in retention_data)
    retention_segments = ""
    colors = {"1-7": "#58a6ff", "8-30": "#3fb950", "31-60": "#d29922", "61-120": "#f85149"}
    retention_labels = ""
    for row in retention_data:
        bucket = row.get("RetentionBucket", "")
        count = row.get("CustomerCount", 0)
        pct = round(count / total_customers * 100, 1) if total_customers > 0 else 0
        color = colors.get(bucket, "#8b949e")
        retention_segments += f'<td style="width:{pct}%; background:{color}; height:28px; text-align:center; color:#fff; font-size:11px; font-weight:600;">{pct}%</td>'
        retention_labels += f'<td style="text-align:center; color:#8b949e; font-size:11px; padding-top:4px;">{bucket}d ({count})</td>'

    # Convert agent summary markdown to simple HTML (basic)
    summary_html = agent_summary.replace("\n\n", "</p><p>").replace("\n", "<br>")
    summary_html = f"<p>{summary_html}</p>"

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0; padding:0; background:#0d1117; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0d1117; padding:24px;">
<tr><td align="center">
<table width="640" cellpadding="0" cellspacing="0" style="background:#161b22; border-radius:12px; overflow:hidden;">

  <!-- Header -->
  <tr>
    <td style="padding:28px 32px 20px; border-bottom:1px solid #30363d;">
      <table width="100%">
        <tr>
          <td>
            <div style="font-size:22px; font-weight:700; color:#e6edf3;">🏥 Recovery & GC Daily Health</div>
            <div style="font-size:13px; color:#8b949e; margin-top:4px;">{report_date}</div>
          </td>
          <td align="right">
            <span style="background:{status_color}; color:#fff; padding:6px 18px; border-radius:20px; font-size:13px; font-weight:700;">{status_label}</span>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- KPI Cards -->
  <tr>
    <td style="padding:24px 32px;">
      <table width="100%" cellpadding="0" cellspacing="8">
        <tr>
          <td width="25%" style="background:#1c2128; border:1px solid #30363d; border-radius:8px; padding:16px; text-align:center;">
            <div style="color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:0.5px;">Total Ops</div>
            <div style="color:#e6edf3; font-size:28px; font-weight:700; margin:6px 0;">{total_ops:,}</div>
          </td>
          <td width="25%" style="background:#1c2128; border:1px solid #30363d; border-radius:8px; padding:16px; text-align:center;">
            <div style="color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:0.5px;">Failure Rate</div>
            <div style="color:{failure_rate_color(overall_failure_rate)}; font-size:28px; font-weight:700; margin:6px 0;">{overall_failure_rate}%</div>
          </td>
          <td width="25%" style="background:#1c2128; border:1px solid #30363d; border-radius:8px; padding:16px; text-align:center;">
            <div style="color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:0.5px;">Avg P95</div>
            <div style="color:#e6edf3; font-size:28px; font-weight:700; margin:6px 0;">{avg_p95:,.0f}<span style="font-size:14px;"> ms</span></div>
          </td>
          <td width="25%" style="background:#1c2128; border:1px solid #30363d; border-radius:8px; padding:16px; text-align:center;">
            <div style="color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:0.5px;">Impacted</div>
            <div style="color:{'#f85149' if impacted > 0 else '#3fb950'}; font-size:28px; font-weight:700; margin:6px 0;">{impacted}</div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Feature Breakdown Table -->
  <tr>
    <td style="padding:0 32px 24px;">
      <div style="color:#8b949e; font-size:13px; font-weight:600; margin-bottom:8px;">📦 Feature Breakdown (Yesterday)</div>
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#1c2128; border:1px solid #30363d; border-radius:8px; overflow:hidden;">
        <tr style="background:#161b22;">
          <th style="padding:10px 16px; text-align:left; color:#8b949e; font-size:12px; border-bottom:2px solid #30363d;">Feature</th>
          <th style="padding:10px 16px; text-align:right; color:#8b949e; font-size:12px; border-bottom:2px solid #30363d;">Ops</th>
          <th style="padding:10px 16px; text-align:right; color:#8b949e; font-size:12px; border-bottom:2px solid #30363d;">Failures</th>
          <th style="padding:10px 16px; text-align:right; color:#8b949e; font-size:12px; border-bottom:2px solid #30363d;">Rate</th>
          <th style="padding:10px 16px; text-align:right; color:#8b949e; font-size:12px; border-bottom:2px solid #30363d;">P95</th>
        </tr>
        {feature_rows}
      </table>
    </td>
  </tr>

  <!-- Retention Distribution Bar -->
  <tr>
    <td style="padding:0 32px 24px;">
      <div style="color:#8b949e; font-size:13px; font-weight:600; margin-bottom:8px;">🗂️ Retention Distribution</div>
      <table width="100%" cellpadding="0" cellspacing="0" style="border-radius:6px; overflow:hidden;">
        <tr>{retention_segments}</tr>
      </table>
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>{retention_labels}</tr>
      </table>
    </td>
  </tr>

  <!-- Dashboard Button -->
  <tr>
    <td style="padding:0 32px 24px;" align="center">
      <table cellpadding="0" cellspacing="0">
        <tr>
          <td style="background:#238636; border-radius:8px;">
            <a href="{dashboard_url}" target="_blank"
               style="display:inline-block; padding:14px 32px; color:#ffffff; font-size:15px; font-weight:700; text-decoration:none;">
              📊 Open Interactive Dashboard
            </a>
          </td>
        </tr>
        <tr><td height="12"></td></tr>
        <tr>
          <td align="center">
            <table cellpadding="0" cellspacing="0">
              <tr>
                <td style="background:#30363d; border-radius:8px;">
                  <a href="{POWERBI_DATA_RECOVERY_URL}" target="_blank"
                     style="display:inline-block; padding:14px 24px; color:#58a6ff; font-size:14px; font-weight:600; text-decoration:none;">
                    🔄 Data Recovery (Power BI)
                  </a>
                </td>
                <td width="12"></td>
                <td style="background:#30363d; border-radius:8px;">
                  <a href="{POWERBI_GC_TELEMETRY_URL}" target="_blank"
                     style="display:inline-block; padding:14px 24px; color:#58a6ff; font-size:14px; font-weight:600; text-decoration:none;">
                    🗑️ Garbage Collection (Power BI)
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- AI Executive Summary -->
  <tr>
    <td style="padding:0 32px 24px;">
      <div style="color:#8b949e; font-size:13px; font-weight:600; margin-bottom:8px;">🤖 AI Executive Summary</div>
      <div style="background:#1c2128; border:1px solid #30363d; border-radius:8px; padding:20px; color:#e6edf3; font-size:13px; line-height:1.6;">
        {summary_html}
      </div>
    </td>
  </tr>

  <!-- Footer -->
  <tr>
    <td style="padding:20px 32px; border-top:1px solid #30363d; text-align:center;">
      <div style="color:#8b949e; font-size:11px;">
        Generated by <strong style="color:#e6edf3;">Fabric DW Telemetry Agent</strong> •
        Data: TridentBcdrReliability + Artifacts •
        <a href="{POWERBI_DATA_RECOVERY_URL}" style="color:#58a6ff; text-decoration:none;">Data Recovery</a> •
        <a href="{POWERBI_GC_TELEMETRY_URL}" style="color:#58a6ff; text-decoration:none;">Garbage Collection</a>
      </div>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        f.write(html)

    print(f"Email HTML generated: {args.output}")
    print(f"Health status: {status_label}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate rich HTML email")
    parser.add_argument("--recovery-data", required=True)
    parser.add_argument("--gc-data", required=True)
    parser.add_argument("--retention-data", required=True)
    parser.add_argument("--thresholds", required=True)
    parser.add_argument("--dashboard-url", required=True)
    parser.add_argument("--agent-summary", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    generate_email(args)
