# fabric-dw-datarecovery_GC_telemetry-agent

Internal telemetry AI agent for **Microsoft Fabric Data Warehouse** — queries Kusto telemetry, analyzes recovery feature usage, generates daily executive summaries, and sends automated emails.

---

## Repository Structure

```
.
├── prompts/                         # AI prompt templates
│   ├── daily_summary.md             # Prompt: generate daily executive summary
│   ├── recovery_analysis.md         # Prompt: deep-dive analysis per recovery feature
│   └── email_template.md            # Prompt: format and send summary email
│
├── kql/                             # KQL queries for Kusto telemetry
│   ├── time_travel.kql              # Time Travel operations
│   ├── table_clone.kql              # Table Clone (current & point-in-time)
│   ├── dw_clone.kql                 # Data Warehouse Clone
│   ├── restore_in_place.kql         # Restore In Place
│   ├── dw_recovery.kql              # Data Warehouse Recovery
│   ├── garbage_collection.kql       # Garbage Collection (GC)
│   ├── retention_config.kql         # Configurable Retention (1–120 days)
│   └── customer_attribution.kql     # Workspace GUID → Customer Name mapping
│
├── workflows/                       # Automation workflow definitions
│   ├── daily_summary.yml            # Scheduled: run queries + generate summary
│   └── email_notification.yml       # Triggered: send summary email to recipients
│
├── config/                          # Configuration files
│   ├── agent_config.json            # Main agent config (Kusto, AI model, features)
│   ├── workspace_mapping.json       # Workspace GUID → Customer Name lookup table
│   └── email_config.json            # Email recipients, SMTP, and schedule config
│
└── README.md
```

---

## Recovery Features Covered

| Feature | KQL File |
|---|---|
| Time Travel | `kql/time_travel.kql` |
| Table Clone (current) | `kql/table_clone.kql` |
| Table Clone (point-in-time) | `kql/table_clone.kql` |
| Data Warehouse Clone | `kql/dw_clone.kql` |
| Restore In Place | `kql/restore_in_place.kql` |
| Data Warehouse Recovery | `kql/dw_recovery.kql` |
| Garbage Collection | `kql/garbage_collection.kql` |
| Configurable Retention (1–120 days) | `kql/retention_config.kql` |

---

## Customer Attribution

Customer identity is resolved via **Workspace GUID → Customer Name** mapping stored in [`config/workspace_mapping.json`](config/workspace_mapping.json).  
The [`kql/customer_attribution.kql`](kql/customer_attribution.kql) query joins telemetry with this mapping to attribute operations to named customers.

---

## Getting Started

1. **Configure Kusto connection** — update `config/agent_config.json` with your cluster URI, database, and authentication details.
2. **Add workspace mappings** — populate `config/workspace_mapping.json` with your customer Workspace GUIDs and names.
3. **Set up email recipients** — update `config/email_config.json` with SMTP settings and recipient addresses.
4. **Set repository secrets** — add the following GitHub Actions secrets:
   - `KUSTO_CLUSTER_URI`, `KUSTO_DATABASE`, `KUSTO_CLIENT_ID`, `KUSTO_CLIENT_SECRET`, `KUSTO_TENANT_ID`
   - `OPENAI_API_KEY`
   - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SENDER_EMAIL`
5. **Replace KQL table names** — update `<TelemetryTable>` and `<WorkspaceMappingTable>` placeholders in each `.kql` file with actual table names.
6. **Implement agent scripts** — create `agent/run_kql_queries.py`, `agent/generate_summary.py`, and `agent/send_email.py` as referenced in the workflow files.

---

## Workflows

| Workflow | Trigger | Description |
|---|---|---|
| `daily_summary.yml` | Cron (06:00 UTC) or manual | Runs all KQL queries, calls AI to generate summary, uploads artifact |
| `email_notification.yml` | Workflow dispatch (from above) | Downloads summary artifact, generates email via AI, sends to recipients |
