"""Serve the built app at its real Pages prefix in isolated browser contexts."""

import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def pages_url(tmp_path_factory):
    if url := os.environ.get("PAGES_TEST_URL"):
        yield url
        return
    assert (ROOT / "dist" / "index.html").exists(), "Run scripts/build_pages.py first"
    directory = tmp_path_factory.mktemp("pages")
    (directory / "annual-loss-distribution").symlink_to(ROOT / "dist", target_is_directory=True)

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(directory)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/annual-loss-distribution/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.fixture(params=["chromium", "firefox"])
def page(request):
    with sync_playwright() as playwright:
        browser = getattr(playwright, request.param).launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.set_default_timeout(30_000)
        errors = []
        page.on("pageerror", lambda error: errors.append(error.stack))
        page.on("requestfailed", lambda req: print(f"Failed request: {req.url}: {req.failure}"))
        try:
            yield page
            assert not errors, "Uncaught browser errors: " + "\n".join(errors)
        finally:
            context.close()
            browser.close()
