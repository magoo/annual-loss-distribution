"""Exercise actual Python execution in both supported Pages test browsers."""

from playwright.sync_api import expect


def set_number(control, value):
    control.fill(str(value))
    control.press("Tab")
    # Marimo rate-limits numeric updates; allow the edit to reach Python before
    # triggering the separate snapshot action.
    control.page.wait_for_timeout(1_000)


def test_browser_workflow(page, pages_url):
    page.goto(pages_url)
    calculate = page.get_by_role("button", name="Calculate / Recalculate annual loss")
    # The independent heading cell can render before numerical dependencies are
    # initialized. Startup is complete only when the model controls are ready.
    expect(calculate).to_be_enabled(timeout=120_000)
    expect(page.get_by_role("heading", name="Annual losses from breaches")).to_be_visible()
    expect(page.get_by_text("Decision range", exact=True)).to_have_count(0)
    expect(page.locator(".js-plotly-plot")).to_have_count(2)
    calculate.click()
    expect(page.get_by_text("Decision range", exact=True)).to_be_visible(timeout=30_000)
    expect(page.locator(".js-plotly-plot")).to_have_count(3)
    metadata = page.locator(".ald-meta")
    expect(metadata).to_contain_text("Seed 12,345")
    baseline = metadata.inner_text()
    baseline_chart = page.locator(".js-plotly-plot").last.evaluate(
        "chart => JSON.stringify(chart.data)"
    )
    report = page.locator(".aw-report")
    expect(report).to_contain_text("Modeled Outcome Ranges")
    baseline_report = report.text_content()

    # Test the real copy button, including its browser clipboard fallback.
    copy_frame = page
    copy = copy_frame.get_by_role("button", name="Copy executive summary to clipboard")
    copy.click()
    expect(copy).to_have_text("Copied")

    seed = page.get_by_role("textbox", name="Reproducibility seed")
    set_number(seed, 12346)
    # Routine edits must leave the previous calculation displayed.
    expect(metadata).to_have_text(baseline)
    calculate.click()
    expect(metadata).to_contain_text("Seed 12,346", timeout=30_000)
    set_number(seed, 12345)
    calculate.click()
    expect(metadata).to_have_text(baseline, timeout=30_000)
    expect(report).to_contain_text(baseline_report)
    # Plotly lives in Marimo shadow roots; use the piercing locator while the
    # chart finishes updating after the new result metadata appears.
    for _ in range(300):
        if (
            page.locator(".js-plotly-plot").last.evaluate("chart => JSON.stringify(chart.data)")
            == baseline_chart
        ):
            break
        page.wait_for_timeout(100)
    else:
        raise AssertionError("Restoring the original seed must reproduce all chart data")

    page.get_by_role("radio", name="CDF", exact=True).check()
    expect(page.get_by_role("radio", name="CDF", exact=True)).to_be_checked()
    expect(page.locator(".js-plotly-plot")).to_have_count(3)

    p95 = page.get_by_role("textbox", name="P95 incidents/year")
    set_number(p95, 0)
    expect(calculate).to_be_disabled()
    set_number(p95, 10)
    expect(calculate).to_be_enabled()

    page.get_by_role("radio", name="Expert panel", exact=True).first.check()
    names = page.get_by_placeholder("Name this panelist")
    expect(names).to_have_count(2)
    page.get_by_role("button", name="Add panelist", exact=True).click()
    expect(names).to_have_count(3)
    names.first.fill("Browser test panelist")
    names.first.press("Tab")
    page.wait_for_timeout(1_000)
    page.get_by_role("button", name="Delete panelist", exact=True).last.click()
    expect(names).to_have_count(2)
    expect(names.first).to_have_value("Browser test panelist")
    calculate.click()
    expect(report).to_contain_text("Browser test panelist", timeout=30_000)

    page.get_by_role("radio", name="Threat scenarios", exact=True).first.check()
    scenario_names = page.get_by_placeholder("Name this threat scenario")
    expect(scenario_names).to_have_count(10, timeout=30_000)
    page.get_by_role("button", name="Add scenario", exact=True).click()
    expect(scenario_names).to_have_count(11)
    scenario_names.first.fill("Browser test scenario")
    scenario_names.first.press("Tab")
    page.wait_for_timeout(1_000)
    page.get_by_role("button", name="Remove", exact=True).last.click()
    expect(scenario_names).to_have_count(10, timeout=30_000)
    calculate.click()
    expect(report).to_contain_text("Browser test scenario", timeout=30_000)
    expect(metadata).not_to_have_text(baseline, timeout=30_000)
    expect(page.get_by_text("Decision range", exact=True)).to_be_visible()
    copy_frame.get_by_role("button", name="Copy executive summary to clipboard").click()
    expect(
        copy_frame.get_by_role("button", name="Copy executive summary to clipboard")
    ).to_have_text("Copied")


def test_saved_analysis_reopens_and_imports_without_calculating(page, pages_url):
    import json
    from pathlib import Path

    page.goto(pages_url)
    calculate = page.get_by_role("button", name="Calculate / Recalculate annual loss")
    expect(calculate).to_be_enabled(timeout=120_000)
    seed = page.get_by_role("textbox", name="Reproducibility seed")
    set_number(seed, 4123)
    p95 = page.get_by_role("textbox", name="P95 incidents/year", exact=True)
    set_number(p95, 17)
    calculate.click()
    expect(page.locator(".ald-meta")).to_contain_text("Seed 4,123", timeout=30_000)
    baseline = page.locator(".aw-report").text_content()
    with page.expect_download() as result:
        page.get_by_role("button", name="Download analysis", exact=True).click()
    backup = Path(result.value.path()).read_bytes()
    parsed = json.loads(backup)
    assert "results" not in parsed
    p95.fill("1e")
    page.reload()
    expect(p95).to_have_value("1e", timeout=120_000)
    expect(page.locator(".aw-results")).to_be_empty()
    expect(calculate).to_be_disabled()
    set_number(p95, 17)
    calculate.click()
    expect(page.locator(".aw-report")).to_have_text(baseline, timeout=30_000)
    page.get_by_label("Import backup file", exact=True).set_input_files(
        {"name": "saved.analysis.json", "mimeType": "application/json", "buffer": backup}
    )
    expect(page.get_by_role("combobox", name="Analysis", exact=True)).not_to_have_value(
        parsed["id"]
    )
    expect(page.locator(".aw-results")).to_be_empty()
    expect(calculate).to_be_enabled()
    calculate.click()
    expect(page.locator(".aw-report")).to_have_text(baseline, timeout=30_000)
    # Both calculation and preview responses update outputs without remounting inputs.
    handle = p95.element_handle()
    p95.fill("19")
    expect(p95).to_be_focused()
    page.wait_for_timeout(500)
    assert handle.evaluate("node => node.isConnected")
    expect(p95).to_be_focused()
    for width in (1440, 390):
        page.set_viewport_size({"width": width, "height": 1000})
        page.wait_for_function(
            "node => node.scrollWidth <= node.clientWidth + 1",
            arg=page.locator(".analysis-workspace").element_handle(),
        )
