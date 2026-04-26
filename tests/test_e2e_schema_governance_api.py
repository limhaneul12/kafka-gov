from __future__ import annotations

import pytest
import requests


@pytest.mark.e2e
def test_e2e_schema_governance_proxy_endpoints_are_available(e2e_urls: dict[str, str]) -> None:
    frontend_base = e2e_urls["frontend_url"]

    api_info = requests.get(f"{frontend_base}/api/v1", timeout=15)
    approvals = requests.get(f"{frontend_base}/api/v1/approval-requests", timeout=15)
    audit_recent = requests.get(f"{frontend_base}/api/v1/audit/recent", timeout=15)

    assert api_info.status_code == 200
    assert api_info.json()["message"] == "Data Governance API"

    assert approvals.status_code == 200
    assert isinstance(approvals.json(), list)

    assert audit_recent.status_code == 200
    assert isinstance(audit_recent.json(), list)
