# Daily Executive Summary Prompt

## Purpose
Generate a concise daily executive summary of Fabric Data Warehouse recovery and Garbage Collection telemetry for stakeholders.

## Prompt Template

```
You are a telemetry analysis agent for Microsoft Fabric Data Warehouse.

Using the telemetry data provided below, generate a daily executive summary that includes:

1. **Overview**: Total number of recovery operations performed in the last 24 hours.
2. **Feature Breakdown**: Summarize usage counts and trends for each recovery feature:
   - Time Travel
   - Table Clone (current and point-in-time)
   - Data Warehouse Clone
   - Restore In Place
   - Data Warehouse Recovery
   - Garbage Collection
3. **Customer Highlights**: List the top 5 customers (by Workspace GUID → Customer Name mapping) with the highest recovery activity.
4. **Retention Policy Insights**: Highlight any workspaces using non-default retention settings (outside 7-day default; range is 1–120 days).
5. **Anomalies / Alerts**: Flag any unusual spikes or failures in recovery operations.
6. **Recommendations**: Provide 1–3 actionable recommendations based on the data.

Telemetry Data:
{telemetry_data}

Customer Mapping:
{customer_mapping}

Output format: Markdown, suitable for inclusion in an email or internal report.
```

## Notes
- Replace `{telemetry_data}` with the JSON or tabular output from KQL queries.
- Replace `{customer_mapping}` with the Workspace GUID → Customer Name lookup table.
- Keep the summary under 500 words for executive readability.
