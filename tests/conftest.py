from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Generator
from pathlib import Path

import pytest
import requests
from playwright.sync_api import Browser, Page, sync_playwright


ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT_DIR / "frontend"

LOCAL_BACKEND_URL = "http://127.0.0.1:8000"
LOCAL_FRONTEND_URL = "http://127.0.0.1:3000"
CONTAINER_BACKEND_URL = "http://127.0.0.1:8001"
CONTAINER_FRONTEND_URL = "http://127.0.0.1:90"


def _wait_http_ready(url: str, timeout_sec: float = 60.0) -> None:
    started = time.time()
    while time.time() - started < timeout_sec:
        try:
            response = requests.get(url, timeout=1.5)
            if response.status_code < 500:
                return
        except requests.RequestException:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for service: {url}")


def _stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return

    _ = process.terminate()
    try:
        _ = process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        _ = process.kill()
        _ = process.wait(timeout=5)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="run full-system e2e tests",
    )
    parser.addoption(
        "--e2e-target",
        action="store",
        default="local",
        choices=["local", "container"],
        help="e2e target mode: local subprocesses or existing containers",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-e2e"):
        return

    skip_e2e = pytest.mark.skip(reason="use --run-e2e to run full-system e2e tests")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip_e2e)


@pytest.fixture(scope="session")
def e2e_urls(pytestconfig: pytest.Config) -> Generator[dict[str, str], None, None]:
    target = str(pytestconfig.getoption("--e2e-target"))

    if target == "container":
        backend_url = os.getenv("E2E_BACKEND_URL", CONTAINER_BACKEND_URL)
        frontend_url = os.getenv("E2E_FRONTEND_URL", CONTAINER_FRONTEND_URL)

        _wait_http_ready(f"{backend_url}/health", timeout_sec=120.0)
        _wait_http_ready(f"{frontend_url}/health", timeout_sec=120.0)
        yield {"backend_url": backend_url, "frontend_url": frontend_url}
        return

    backend_url = LOCAL_BACKEND_URL
    frontend_url = LOCAL_FRONTEND_URL

    env_backend = os.environ.copy()
    env_backend["PYTHONUNBUFFERED"] = "1"

    backend_process = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=ROOT_DIR,
        env=env_backend,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    env_front = os.environ.copy()
    env_front["CI"] = "true"

    frontend_process = subprocess.Popen(
        ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "3000"],
        cwd=FRONTEND_DIR,
        env=env_front,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    try:
        _wait_http_ready(f"{backend_url}/health", timeout_sec=90.0)
        _wait_http_ready(frontend_url, timeout_sec=120.0)
        yield {"backend_url": backend_url, "frontend_url": frontend_url}
    finally:
        _stop_process(frontend_process)
        _stop_process(backend_process)


@pytest.fixture(scope="session")
def browser(e2e_urls: dict[str, str]) -> Generator[Browser, None, None]:
    _ = e2e_urls
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            yield browser
        finally:
            browser.close()


@pytest.fixture
def page(browser: Browser, e2e_urls: dict[str, str]) -> Generator[Page, None, None]:
    context = browser.new_context(base_url=e2e_urls["frontend_url"])
    page = context.new_page()
    try:
        yield page
    finally:
        context.close()


@pytest.fixture
def backend_base_url(e2e_urls: dict[str, str]) -> str:
    return e2e_urls["backend_url"]
