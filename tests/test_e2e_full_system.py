from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect
from typing import cast


@pytest.mark.e2e
def test_full_system_shell_loads(page: Page) -> None:
    _ = page.goto("/", wait_until="domcontentloaded")

    expect(page.get_by_text("Data Gov")).to_be_visible()
    expect(page.get_by_role("link", name="Schemas")).to_be_visible()
    expect(
        page.locator("aside").get_by_role("link", name="Schema Registry", exact=True)
    ).to_be_visible()
    expect(page.locator("aside").get_by_role("link", name="Topics", exact=True)).to_have_count(0)
    expect(
        page.locator("aside").get_by_role("link", name="Schema Policies", exact=True)
    ).to_be_visible()
    expect(
        page.locator("aside").get_by_role("link", name="Approvals & Audit", exact=True)
    ).to_be_visible()
    expect(page.locator("aside").get_by_role("link", name="Consumers", exact=True)).to_have_count(0)


@pytest.mark.e2e
def test_full_system_schema_page_navigation(page: Page, e2e_urls: dict[str, str]) -> None:
    _ = page.goto("/", wait_until="domcontentloaded")
    page.get_by_role("link", name="Schemas").click()

    expect(page).to_have_url(f"{e2e_urls['frontend_url']}/schemas")
    expect(page.locator("aside").get_by_role("link", name="Schemas", exact=True)).to_have_attribute(
        "aria-current", "page"
    )


@pytest.mark.e2e
def test_full_system_browser_to_backend_proxy(page: Page) -> None:
    _ = page.goto("/", wait_until="domcontentloaded")

    payload = cast(
        dict[str, str],
        page.evaluate(
            """
        async () => {
          const response = await fetch('/api/v1');
          return await response.json();
        }
        """
        ),
    )

    assert payload["message"] == "Data Governance API"
    assert payload["version"] == "1.0.0"
