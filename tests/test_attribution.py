import unittest

from agent.attribution import aggregate_feature_attribution, enrich_telemetry_rows


class AttributionTests(unittest.TestCase):
    def test_enrich_rows_normalizes_workspace_tenant_and_feature(self):
        telemetry = [
            {
                "TenantID": "TENANT-A",
                "Workspace GUID": "W1",
                "OperationName": "Restore",
                "ResultCode": 500,
            },
            {
                "WorkspaceId": "W2",
                "OperationName": "GC",
                "ResultCode": 200,
                "Operations": 3,
            },
        ]
        mapping = {
            "w1": {"customer_name": "Contoso", "tenant_id": "tenant-a", "region": "eastus", "tier": "F64"},
            "w2": {"customer_name": "Fabrikam", "tenant_id": "tenant-b", "region": "westeurope", "tier": "F8"},
        }
        feature_mapping = {"RestoreInPlace": ["Restore"], "GarbageCollection": ["GC"]}

        enriched = enrich_telemetry_rows(telemetry, mapping, feature_mapping)

        self.assertEqual(enriched[0]["tenant_id"], "tenant-a")
        self.assertEqual(enriched[0]["workspace_id"], "w1")
        self.assertEqual(enriched[0]["feature"], "RestoreInPlace")
        self.assertEqual(enriched[0]["failures"], 1)
        self.assertEqual(enriched[1]["tenant_id"], "tenant-b")
        self.assertEqual(enriched[1]["operations"], 3)

    def test_aggregate_feature_attribution_rollups(self):
        enriched = [
            {"feature": "RestoreInPlace", "tenant_id": "t1", "workspace_id": "w1", "customer_name": "Contoso", "region": "eastus", "tier": "F64", "operations": 10, "failures": 2},
            {"feature": "RestoreInPlace", "tenant_id": "t1", "workspace_id": "w1", "customer_name": "Contoso", "region": "eastus", "tier": "F64", "operations": 5, "failures": 1},
            {"feature": "GarbageCollection", "tenant_id": "t2", "workspace_id": "w2", "customer_name": "Fabrikam", "region": "westeurope", "tier": "F8", "operations": 7, "failures": 0},
        ]
        result = aggregate_feature_attribution(enriched, top_n=2)

        restore_row = [r for r in result["feature_attribution"] if r["feature"] == "RestoreInPlace"][0]
        self.assertEqual(restore_row["operations"], 15)
        self.assertEqual(restore_row["failures"], 3)
        self.assertEqual(restore_row["failure_rate"], 20.0)
        self.assertTrue(result["top_tenants_by_feature"])
        self.assertTrue(result["top_workspaces_by_feature"])
        self.assertEqual(result["failures_by_feature"][0]["feature"], "RestoreInPlace")


if __name__ == "__main__":
    unittest.main()
