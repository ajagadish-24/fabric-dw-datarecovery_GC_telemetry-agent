import json
from collections import defaultdict


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def load_workspace_mapping(path):
    data = load_json(path)
    mappings = data.get("mappings", []) if isinstance(data, dict) else []
    by_workspace = {}
    for row in mappings:
        workspace_id = normalize_id(row.get("workspace_id"))
        if workspace_id:
            by_workspace[workspace_id] = row
    return by_workspace


def load_telemetry_rows(path):
    data = load_json(path)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("rows", "telemetry", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    return []


def normalize_id(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def _first_non_empty(row, keys):
    for key in keys:
        value = row.get(key)
        if value not in (None, "", "null"):
            return value
    return None


def _normalize_feature(feature_mapping, operation_name):
    if not operation_name:
        return "Unknown"
    normalized = str(operation_name).strip()
    for feature_name, operations in feature_mapping.items():
        if normalized in operations:
            return feature_name
    return normalized


def _is_failure(row):
    if "IsFailure" in row:
        return bool(row.get("IsFailure"))
    if "Failure" in row:
        return bool(row.get("Failure"))
    result_code = row.get("ResultCode")
    if result_code is not None:
        try:
            return int(result_code) != 200
        except (TypeError, ValueError):
            return str(result_code).strip().lower() not in ("ok", "success", "200")
    status = row.get("Status") or row.get("OperationStatus") or row.get("Result")
    if status is not None:
        return str(status).strip().lower() in ("failed", "failure", "error")
    return False


def enrich_telemetry_rows(telemetry_rows, workspace_mapping, feature_mapping):
    enriched = []
    for row in telemetry_rows:
        workspace_id = normalize_id(_first_non_empty(row, ["WorkspaceId", "Workspace GUID", "WorkspaceGuid", "workspace_id"]))
        tenant_id = normalize_id(_first_non_empty(row, ["TenantID", "TenantId", "tenant_id"]))
        operation_name = _first_non_empty(row, ["OperationName", "FeatureName", "feature", "operation"])
        mapping = workspace_mapping.get(workspace_id, {})
        if not tenant_id:
            tenant_id = normalize_id(mapping.get("tenant_id"))
        operations = row.get("Operations", row.get("TotalOperations", row.get("TotalRuns", 1)))
        try:
            operations = int(operations)
        except (TypeError, ValueError):
            operations = 1
        failures = row.get("Failures")
        if failures is None:
            failures = operations if _is_failure(row) else 0
        try:
            failures = int(failures)
        except (TypeError, ValueError):
            failures = 0
        feature_name = _normalize_feature(feature_mapping, operation_name)
        enriched.append(
            {
                "feature": feature_name,
                "operation_name": operation_name or "Unknown",
                "tenant_id": tenant_id or "unknown-tenant",
                "workspace_id": workspace_id or "unknown-workspace",
                "customer_name": mapping.get("customer_name", "Unknown"),
                "region": mapping.get("region", "Unknown"),
                "tier": mapping.get("tier", "Unknown"),
                "operations": max(operations, 0),
                "failures": max(failures, 0),
            }
        )
    return enriched


def aggregate_feature_attribution(enriched_rows, top_n=5):
    by_feature_entity = defaultdict(lambda: {"operations": 0, "failures": 0, "customer_name": "Unknown", "region": "Unknown", "tier": "Unknown"})

    for row in enriched_rows:
        key = (row["feature"], row["tenant_id"], row["workspace_id"])
        bucket = by_feature_entity[key]
        bucket["operations"] += row["operations"]
        bucket["failures"] += row["failures"]
        bucket["customer_name"] = row["customer_name"]
        bucket["region"] = row["region"]
        bucket["tier"] = row["tier"]

    feature_attribution = []
    for (feature, tenant_id, workspace_id), values in by_feature_entity.items():
        operations = values["operations"]
        failures = values["failures"]
        feature_attribution.append(
            {
                "feature": feature,
                "tenant_id": tenant_id,
                "workspace_id": workspace_id,
                "customer_name": values["customer_name"],
                "region": values["region"],
                "tier": values["tier"],
                "operations": operations,
                "failures": failures,
                "failure_rate": round(100.0 * failures / operations, 2) if operations > 0 else 0,
            }
        )

    feature_attribution.sort(key=lambda r: (r["feature"], -r["operations"], -r["failures"]))

    top_tenants = []
    top_workspaces = []
    failures_by_feature = []
    grouped = defaultdict(list)
    for row in feature_attribution:
        grouped[row["feature"]].append(row)
        failures_by_feature.append(row)

    for feature, rows in grouped.items():
        tenant_rollup = defaultdict(lambda: {"operations": 0, "failures": 0})
        workspace_rollup = defaultdict(lambda: {"operations": 0, "failures": 0, "tenant_id": "", "customer_name": "", "region": "", "tier": ""})
        for row in rows:
            tenant_rollup[row["tenant_id"]]["operations"] += row["operations"]
            tenant_rollup[row["tenant_id"]]["failures"] += row["failures"]
            workspace_rollup[row["workspace_id"]]["operations"] += row["operations"]
            workspace_rollup[row["workspace_id"]]["failures"] += row["failures"]
            workspace_rollup[row["workspace_id"]]["tenant_id"] = row["tenant_id"]
            workspace_rollup[row["workspace_id"]]["customer_name"] = row["customer_name"]
            workspace_rollup[row["workspace_id"]]["region"] = row["region"]
            workspace_rollup[row["workspace_id"]]["tier"] = row["tier"]

        tenant_items = sorted(tenant_rollup.items(), key=lambda item: (-item[1]["operations"], -item[1]["failures"]))[:top_n]
        for tenant_id, values in tenant_items:
            ops = values["operations"]
            fails = values["failures"]
            top_tenants.append(
                {
                    "feature": feature,
                    "tenant_id": tenant_id,
                    "operations": ops,
                    "failures": fails,
                    "failure_rate": round(100.0 * fails / ops, 2) if ops > 0 else 0,
                }
            )

        workspace_items = sorted(workspace_rollup.items(), key=lambda item: (-item[1]["operations"], -item[1]["failures"]))[:top_n]
        for workspace_id, values in workspace_items:
            ops = values["operations"]
            fails = values["failures"]
            top_workspaces.append(
                {
                    "feature": feature,
                    "workspace_id": workspace_id,
                    "tenant_id": values["tenant_id"],
                    "customer_name": values["customer_name"],
                    "region": values["region"],
                    "tier": values["tier"],
                    "operations": ops,
                    "failures": fails,
                    "failure_rate": round(100.0 * fails / ops, 2) if ops > 0 else 0,
                }
            )

    failures_by_feature.sort(key=lambda r: (-r["failures"], -r["operations"], r["feature"]))
    return {
        "feature_attribution": feature_attribution,
        "top_tenants_by_feature": top_tenants,
        "top_workspaces_by_feature": top_workspaces,
        "failures_by_feature": failures_by_feature,
    }
