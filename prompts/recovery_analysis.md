# Recovery Feature Analysis Prompt

## Purpose
Deep-dive analysis of individual Fabric Data Warehouse recovery features using KQL telemetry output.

## Prompt Template

```
You are a telemetry analysis agent for Microsoft Fabric Data Warehouse recovery features.

Analyze the following telemetry data for the recovery feature: **{feature_name}**

Time range: {start_time} to {end_time}

Telemetry Data:
{telemetry_data}

Provide a structured analysis including:

1. **Usage Summary**
   - Total operation count
   - Unique workspaces / customers involved
   - Success vs. failure rate

2. **Trend Analysis**
   - Hourly / daily usage trend
   - Comparison to previous period (if available)

3. **Customer Segmentation**
   - Top customers by operation count
   - Customers with failure rates above 5%

4. **Latency & Performance**
   - Average, p50, p95, p99 operation latency
   - Identify slow outliers (> 2x average latency)

5. **Retention Policy Usage** (if applicable)
   - Distribution of configured retention periods (1–120 days)
   - Workspaces using default vs. custom retention

6. **Anomalies**
   - Sudden spikes or drops in usage
   - Repeated failures for specific workspaces

7. **Recommendations**
   - Actionable improvements or follow-up investigations

Output format: Markdown.
```

## Supported Feature Names
- `TimeTravel`
- `TableClone`
- `TableClonePointInTime`
- `DataWarehouseClone`
- `RestoreInPlace`
- `DataWarehouseRecovery`
- `GarbageCollection`

## Notes
- Replace placeholder variables `{feature_name}`, `{start_time}`, `{end_time}`, and `{telemetry_data}` before submitting.
