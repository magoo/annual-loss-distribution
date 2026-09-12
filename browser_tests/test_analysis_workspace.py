"""Browser storage, schema parity and editor actions, without waiting on Python.

This harness runs the production browser module in a shadow root. Its worker
bridge can be held or reordered to exercise crashes and slow/stale responses.
The exported Pages workflow is separately tested with the real Python runtime.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from playwright.sync_api import expect

from annual_loss.analysis_browser import BROWSER_MODULE
from annual_loss.analysis_document import make_document, validate_document
from annual_loss.workflow_state import WorkflowModeState

PREFIX = "security-org-planning-annual-loss:analyses:v1:"
DB = "security-org-planning-annual-loss-analyses"


@pytest.fixture
def open_workspace(page, pages_url):
    def open_(target=page, *, auto_response=True):
        target.route(
            "**/__analysis_test__",
            lambda route: route.fulfill(
                content_type="text/html", body="<html><body></body></html>"
            ),
        )
        target.goto(pages_url + "__analysis_test__")
        target.evaluate(
            """async ({source, defaults, autoResponse}) => {
          window.analysisModule = await import(URL.createObjectURL(new Blob([
            'const Plotly = {react: async () => {}, purge: () => {}};\\n' + source
          ], {type: 'text/javascript'})));
          const values = {defaults, guidance: {frequency: 'Frequency guidance', cost: 'Cost guidance'}, request: {}, response: {}};
          const listeners = new Set(); window.requests = []; window.autoResponse = autoResponse;
          window.testModel = {
            get: key => values[key], set: (key, value) => {values[key] = value},
            save_changes: () => {
              const request = structuredClone(values.request); window.requests.push(request);
              if (window.autoResponse) queueMicrotask(() => window.respond({analysis_id: request.analysis.id,
                activation: request.activation, token: request.token, action: request.action,
                errors: {}, previews: {}, panels: {}, loss: null}));
            },
            on: (event, callback) => listeners.add(callback), off: (event, callback) => listeners.delete(callback)
          };
          window.respond = response => {values.response = response; for (const callback of listeners) callback()};
          const host = document.createElement('div'); document.body.append(host);
          const root = host.attachShadow({mode:'open'}), el = document.createElement('div'); root.append(el);
          window.cleanupWorkspace = window.analysisModule.default.render({model:window.testModel, el});
        }""",
            {"source": BROWSER_MODULE, "defaults": make_document(), "autoResponse": auto_response},
        )
        expect(target.get_by_role("textbox", name="Reproducibility seed")).to_be_visible()
        expect(target.get_by_role("button", name="New", exact=True)).to_be_enabled()
        return target

    return open_


def saved(page):
    expect(page.locator(".aw-status")).to_have_attribute("data-saved", "true")


def analysis_id(page):
    return page.get_by_role("combobox", name="Analysis", exact=True).input_value()


def stored(page):
    return page.evaluate(
        "key => JSON.parse(localStorage.getItem(key))", PREFIX + "analysis:" + analysis_id(page)
    )


def download(page, name="Download analysis"):
    with page.expect_download() as result:
        page.get_by_role("button", name=name, exact=True).click()
    return Path(result.value.path()).read_text()


def rename(page, name):
    page.once("dialog", lambda dialog: dialog.accept(name))
    page.get_by_role("button", name="Rename", exact=True).click()
    expect(
        page.get_by_role("combobox", name="Analysis", exact=True).locator("option:checked")
    ).to_have_text(name)
    saved(page)


def test_raw_typing_survives_reload_while_worker_is_stalled(page, open_workspace):
    open_workspace(auto_response=False)
    value = page.get_by_role("textbox", name="P95 incidents/year", exact=True)
    value.fill("1e")
    assert stored(page)["drafts"]["frequency:direct:lognormal:p95"] == "1e"
    # The raw edit is journaled before a commit, timer, worker response or unload.
    first = analysis_id(page)
    open_workspace(auto_response=False)
    assert analysis_id(page) == first
    expect(value).to_have_value("1e")
    expect(page.get_by_role("button", name="Calculate / Recalculate annual loss")).to_be_disabled()
    value.fill("17")
    value.press("Enter")
    saved(page)
    assert stored(page)["frequency"]["direct"]["lognormal"]["p95"] == 17


def test_named_library_duplicates_imports_and_previous_session(page, open_workspace):
    open_workspace()
    saved(page)
    rename(page, "Company A")
    original = analysis_id(page)
    value = page.get_by_role("textbox", name="P95 incidents/year", exact=True)
    value.fill("22")
    value.press("Enter")
    saved(page)
    backup = download(page)
    assert json.loads(backup)["name"] == "Company A"
    assert download(page) == backup
    open_workspace()
    saved(page)
    value.fill("23")
    value.press("Enter")
    saved(page)
    page.get_by_role("button", name="Duplicate", exact=True).click()
    saved(page)
    assert analysis_id(page) != original
    assert stored(page)["frequency"]["direct"]["lognormal"]["p95"] == 23
    page.get_by_role("combobox", name="Analysis", exact=True).select_option(original)
    saved(page)
    page.get_by_role("button", name="Recover previous session", exact=True).click()
    saved(page)
    assert analysis_id(page) != original
    assert stored(page)["frequency"]["direct"]["lognormal"]["p95"] == 22
    page.get_by_label("Import backup file", exact=True).set_input_files(
        {"name": "a.json", "mimeType": "application/json", "buffer": backup.encode()}
    )
    saved(page)
    expect(
        page.get_by_role("combobox", name="Analysis", exact=True).locator("option")
    ).to_have_count(4)
    assert json.loads(download(page))["name"] == "Company A (2)"
    library = json.loads(download(page, "Back up all analyses"))
    assert len(library["analyses"]) == 4 and len({d["id"] for d in library["analyses"]}) == 4


def test_hidden_modes_and_structural_edits_preserve_drafts_and_ids(page, open_workspace):
    open_workspace()
    p95 = page.get_by_role("textbox", name="P95 incidents/year", exact=True)
    p95.fill("31")
    p95.press("Enter")
    distribution = page.get_by_role("combobox", name="Frequency distribution", exact=True)
    distribution.select_option("pert")
    page.get_by_role("textbox", name="Minimum incidents/year", exact=True).fill("-")
    distribution.select_option("pareto")
    p95.fill("73")
    p95.press("Enter")
    distribution.select_option("lognormal")
    expect(p95).to_have_value("31")
    page.get_by_role("radio", name="Expert panel", exact=True).first.check()
    names = page.get_by_placeholder("Name this panelist")
    names.first.fill("Expert draft")
    page.get_by_role("button", name="Add panelist", exact=True).click()
    expect(names).to_have_count(3)
    expect(names.first).to_have_value("Expert draft")
    page.get_by_role("button", name="Delete panelist", exact=True).last.click()
    expect(names).to_have_count(2)
    assert stored(page)["frequency"]["panel"]["next_id"] == 4
    page.get_by_role("radio", name="Threat scenarios", exact=True).first.check()
    expect(page.get_by_role("radio", name="Threat scenarios", exact=True).last).to_be_checked()
    page.get_by_role("button", name="Add scenario", exact=True).click()
    page.get_by_role("button", name="Remove", exact=True).last.click()
    assert stored(page)["scenarios"]["next_id"] == 12
    saved(page)
    open_workspace()
    saved(page)
    page.get_by_role("radio", name="Direct estimate", exact=True).last.check()
    expect(page.get_by_role("radio", name="Expert panel", exact=True).first).to_be_checked()
    page.get_by_role("radio", name="Direct estimate", exact=True).first.check()
    distribution.select_option("pert")
    expect(page.get_by_role("textbox", name="Minimum incidents/year", exact=True)).to_have_value(
        "-"
    )
    distribution.select_option("pareto")
    expect(p95).to_have_value("73")


def test_multitab_lock_takeover_and_independent_duplicates(page, open_workspace):
    open_workspace()
    saved(page)
    other = page.context.new_page()
    open_workspace(other)
    expect(other.get_by_role("textbox", name="Reproducibility seed")).to_be_disabled()
    other.get_by_role("button", name="Duplicate", exact=True).click()
    saved(other)
    expect(other.get_by_role("textbox", name="Reproducibility seed")).to_be_enabled()
    original = analysis_id(page)
    other.get_by_role("combobox", name="Analysis", exact=True).select_option(original)
    expect(other.get_by_role("textbox", name="Reproducibility seed")).to_be_disabled()
    page.close()
    other.get_by_role("button", name="Retry saving / Edit here", exact=True).click()
    expect(other.get_by_role("textbox", name="Reproducibility seed")).to_be_enabled()
    other.close()


@pytest.mark.parametrize("api", ["localStorage", "indexedDB", "locks", "quota"])
def test_unavailable_storage_keeps_downloadable_work_across_switches(page, open_workspace, api):
    if api == "locks":
        page.add_init_script(
            "Object.defineProperty(navigator, 'locks', {get() {throw new Error('Blocked locks')}})"
        )
    elif api == "quota":
        page.add_init_script(
            "Storage.prototype.setItem = function() {throw new DOMException('Full', 'QuotaExceededError')}"
        )
    else:
        page.add_init_script(
            f"Object.defineProperty(window, '{api}', {{get() {{throw new Error('Blocked storage')}}}})"
        )
    open_workspace()
    page.get_by_role("textbox", name="P95 incidents/year", exact=True).fill("1e")
    expect(page.locator(".aw-status")).to_contain_text("Not saved")
    original = analysis_id(page)
    page.get_by_role("button", name="Duplicate", exact=True).click()
    expect(
        page.get_by_role("combobox", name="Analysis", exact=True).locator("option")
    ).to_have_count(2)
    page.get_by_role("combobox", name="Analysis", exact=True).select_option(original)
    expect(page.get_by_role("textbox", name="P95 incidents/year", exact=True)).to_have_value("1e")
    backup = json.loads(download(page, "Back up all analyses"))
    assert len(backup["analyses"]) == 2
    assert all(d["drafts"]["frequency:direct:lognormal:p95"] == "1e" for d in backup["analyses"])


def test_corrupt_original_preserved_and_checkpoint_recovered(page, open_workspace):
    open_workspace()
    saved(page)
    original = analysis_id(page)
    open_workspace()
    saved(page)
    field = page.get_by_role("textbox", name="P95 incidents/year", exact=True)
    field.fill("29")
    field.press("Enter")
    saved(page)
    raw = '{"format":"security-annual-loss-analysis","version":999}'
    page.evaluate(
        "({key, raw}) => localStorage.setItem(key,raw)",
        {"key": PREFIX + "analysis:" + original, "raw": raw},
    )
    open_workspace()
    expect(page.get_by_role("button", name="Download original", exact=True)).to_be_visible()
    assert download(page, "Download original") == raw
    page.get_by_role("button", name="Recover checkpoint", exact=True).click()
    saved(page)
    assert stored(page)["frequency"]["direct"]["lognormal"]["p95"] == 10
    assert page.evaluate("key => localStorage.getItem(key)", PREFIX + "analysis:" + original) == raw


def test_durable_restore_and_confirmed_deletion_do_not_resurrect(page, open_workspace):
    open_workspace()
    saved(page)
    field = page.get_by_role("textbox", name="P95 incidents/year", exact=True)
    field.fill("39")
    field.press("Enter")
    saved(page)
    original = analysis_id(page)
    key = PREFIX + "analysis:" + original
    raw = page.evaluate("key => localStorage.getItem(key)", key)
    page.evaluate("key => localStorage.removeItem(key)", key)
    open_workspace()
    saved(page)
    assert analysis_id(page) == original
    expect(field).to_have_value("39")
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Delete", exact=True).click()
    saved(page)
    assert analysis_id(page) != original
    # Simulate a crash after the durable tombstone but before local removal.
    page.evaluate("({key,raw}) => localStorage.setItem(key,raw)", {"key": key, "raw": raw})
    open_workspace()
    saved(page)
    assert page.evaluate("key => localStorage.getItem(key)", key) is None


def test_stale_responses_and_python_updates_do_not_replace_typing(page, open_workspace):
    open_workspace(auto_response=False)
    page.wait_for_function("window.requests.length > 0")
    old = page.evaluate("window.requests.at(-1)")
    field = page.get_by_role("textbox", name="P95 incidents/year", exact=True)
    field.fill("1e")
    page.wait_for_function("window.requests.length > 1")
    latest = page.evaluate("window.requests.at(-1)")
    page.evaluate(
        "response => window.respond(response)",
        {
            "analysis_id": old["analysis"]["id"],
            "activation": old["activation"],
            "token": old["token"],
            "action": "preview",
            "errors": {"model": "STALE RESULT"},
            "previews": {},
            "panels": {},
            "loss": None,
        },
    )
    expect(page.get_by_text("STALE RESULT")).to_have_count(0)
    page.evaluate(
        "response => window.respond(response)",
        {
            "analysis_id": latest["analysis"]["id"],
            "activation": latest["activation"],
            "token": latest["token"],
            "action": "preview",
            "errors": {},
            "previews": {},
            "panels": {},
            "loss": None,
        },
    )
    expect(field).to_have_value("1e")
    expect(field).to_be_focused()
    page.get_by_role("button", name="Duplicate", exact=True).click()
    saved(page)
    page.evaluate(
        "response => window.respond(response)",
        {
            "analysis_id": old["analysis"]["id"],
            "activation": old["activation"],
            "token": old["token"],
            "action": "calculate",
            "errors": {"model": "WRONG ANALYSIS"},
            "previews": {},
            "panels": {},
            "loss": None,
        },
    )
    expect(page.get_by_text("WRONG ANALYSIS")).to_have_count(0)


def test_import_validates_every_record_before_creating_anything(page, open_workspace):
    open_workspace()
    saved(page)
    before = stored(page)
    good, bad = make_document(), make_document()
    bad["scenarios"]["rows"] = []
    data = json.dumps(
        {"format": "security-annual-loss-library", "version": 1, "analyses": [good, bad]}
    )
    page.get_by_label("Import backup file", exact=True).set_input_files(
        {"name": "bad.json", "mimeType": "application/json", "buffer": data.encode()}
    )
    expect(page.locator(".aw-warning")).to_contain_text("At least one scenario")
    expect(
        page.get_by_role("combobox", name="Analysis", exact=True).locator("option")
    ).to_have_count(1)
    assert stored(page) == before


def test_python_browser_schema_and_mode_transition_agreement(page, open_workspace):
    open_workspace()
    valid = make_document()
    documents = [valid]
    for path, value in [
        ("seed", -1),
        ("seed", True),
        ("version", False),
        ("model_version", 2),
        ("format", "security-budget"),
        ("frequency.direct.lognormal.p50", -1),
        ("cost.direct.pert.min", None),
        ("scenarios.next_id", 1),
        ("workflow.cost_mode", "scenario"),
        ("created_at", "2026-02-30T00:00:00.000Z"),
        ("drafts", {"seed": "1e"}),
        ("drafts", {"missing": "1e"}),
    ]:
        doc = deepcopy(valid)
        target = doc
        parts = path.split(".")
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
        documents.append(doc)
    expected = []
    for doc in documents:
        try:
            validate_document(doc)
            expected.append(True)
        except (TypeError, ValueError):
            expected.append(False)
    assert (
        page.evaluate(
            "docs => docs.map(doc => {try {analysisModule.validateDocument(doc);return true} catch (_) {return false}})",
            documents,
        )
        == expected
    )
    state = WorkflowModeState()
    for section, mode in [
        ("frequency", "panel"),
        ("cost", "scenario"),
        ("cost", "panel"),
        ("frequency", "scenario"),
        ("frequency", "direct"),
    ]:
        from dataclasses import asdict

        browser = page.evaluate(
            "({state,section,mode}) => analysisModule.selectMode(state,section,mode)",
            {"state": asdict(state), "section": section, "mode": mode},
        )
        state = state.select(section, mode)
        assert browser == asdict(state)


def test_durable_transaction_failure_never_claims_saved(page, open_workspace):
    page.add_init_script("""const original = IDBDatabase.prototype.transaction;
      IDBDatabase.prototype.transaction = function(...args) {
        const tx = original.apply(this, args);
        if (args[1] === 'readwrite') queueMicrotask(() => tx.abort());
        return tx;
      };""")
    open_workspace()
    field = page.get_by_role("textbox", name="P95 incidents/year", exact=True)
    field.fill("1e")
    expect(page.locator(".aw-status")).to_contain_text("Not saved")
    assert stored(page)["drafts"]["frequency:direct:lognormal:p95"] == "1e"
    assert json.loads(download(page))["drafts"]["frequency:direct:lognormal:p95"] == "1e"


def test_failed_edits_conflicting_with_another_tab_become_separate_copy(page, open_workspace):
    open_workspace()
    saved(page)
    original = analysis_id(page)
    other = page.context.new_page()
    open_workspace(other)
    page.evaluate(
        """key => {
      const set = Storage.prototype.setItem;
      Storage.prototype.setItem = function(k,v) {
        if (k === key) throw new DOMException('Full', 'QuotaExceededError');
        return set.call(this,k,v);
      };
    }""",
        PREFIX + "analysis:" + original,
    )
    page.get_by_role("textbox", name="P95 incidents/year", exact=True).fill("1e")
    expect(page.locator(".aw-status")).to_contain_text("Not saved")
    page.get_by_role("button", name="Duplicate", exact=True).click()
    saved(page)
    other.get_by_role("button", name="Retry saving / Edit here", exact=True).click()
    saved(other)
    value = other.get_by_role("textbox", name="P95 incidents/year", exact=True)
    value.fill("99")
    value.press("Enter")
    saved(other)
    other.close()
    page.get_by_role("combobox", name="Analysis", exact=True).select_option(original)
    saved(page)
    assert analysis_id(page) != original
    expect(page.locator(".aw-warning")).to_contain_text("separate copy")
    expect(page.get_by_role("textbox", name="P95 incidents/year", exact=True)).to_have_value("1e")
    assert (
        page.evaluate(
            "key => JSON.parse(localStorage.getItem(key)).frequency.direct.lognormal.p95",
            PREFIX + "analysis:" + original,
        )
        == 99
    )


def test_checkpoint_write_failure_preserves_prior_current_record_and_retry(page, open_workspace):
    open_workspace()
    saved(page)
    original = analysis_id(page)
    open_workspace()
    saved(page)
    before = stored(page)
    page.evaluate(
        """prefix => {
      window.originalSet = Storage.prototype.setItem;
      Storage.prototype.setItem = function(key,value) {
        if (key.startsWith(prefix)) throw new DOMException('Checkpoint full','QuotaExceededError');
        return window.originalSet.call(this,key,value);
      };
    }""",
        PREFIX + "checkpoint:",
    )
    page.get_by_role("textbox", name="P95 incidents/year", exact=True).fill("1e")
    expect(page.locator(".aw-status")).to_contain_text("Not saved")
    assert stored(page) == before
    page.evaluate("() => { Storage.prototype.setItem = window.originalSet; }")
    page.get_by_role("button", name="Retry saving / Edit here", exact=True).click()
    saved(page)
    assert analysis_id(page) == original
    assert stored(page)["drafts"]["frequency:direct:lognormal:p95"] == "1e"
    checkpoint = page.evaluate(
        "key => JSON.parse(localStorage.getItem(key))", PREFIX + "checkpoint:" + original
    )
    assert checkpoint == before


def test_cancelled_delete_preserves_analysis_and_backup(page, open_workspace):
    open_workspace()
    saved(page)
    before = download(page)
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.get_by_role("button", name="Delete", exact=True).click()
    saved(page)
    assert download(page) == before


def test_import_library_reserves_names_and_retains_unsaved_members(page, open_workspace):
    page.add_init_script(
        "Storage.prototype.setItem = function() {throw new DOMException('Full','QuotaExceededError')}"
    )
    open_workspace()
    docs = [make_document("Company"), make_document("Company")]
    content = json.dumps({"format": "security-annual-loss-library", "version": 1, "analyses": docs})
    page.get_by_label("Import backup file", exact=True).set_input_files(
        {"name": "library.json", "mimeType": "application/json", "buffer": content.encode()}
    )
    expect(
        page.get_by_role("combobox", name="Analysis", exact=True).locator("option")
    ).to_have_count(3)
    recovered = json.loads(download(page, "Back up all analyses"))["analyses"]
    assert sorted(doc["name"] for doc in recovered) == ["Analysis 1", "Company", "Company (2)"]
    assert not set(doc["id"] for doc in docs).intersection(doc["id"] for doc in recovered)


def test_browser_process_crash_recovers_durable_drafts(page, open_workspace, tmp_path):
    import os
    import signal
    import subprocess

    engine = page.context.browser.browser_type
    if engine.name != "chromium":
        pytest.skip("Process termination uses Chromium CDP process inventory")
    profile = str(tmp_path / "isolated-crash-profile")
    context = engine.launch_persistent_context(profile)
    try:
        target = context.pages[0]
        open_workspace(target)
        target.get_by_role("textbox", name="P95 incidents/year", exact=True).fill("1e")
        saved(target)
        original = analysis_id(target)
        cdp = context.browser.new_browser_cdp_session()
        pid = next(
            process["id"]
            for process in cdp.send("SystemInfo.getProcessInfo")["processInfo"]
            if process["type"] == "browser"
        )
        command = subprocess.check_output(["ps", "-p", str(pid), "-o", "command="], text=True)
        assert profile in command  # Never terminate a browser outside the isolated test profile.
        with context.expect_event("close"):
            os.kill(pid, signal.SIGKILL)
    finally:
        context.close()
    reopened = engine.launch_persistent_context(profile)
    try:
        target = reopened.pages[0]
        open_workspace(target)
        assert analysis_id(target) == original
        expect(target.get_by_role("textbox", name="P95 incidents/year", exact=True)).to_have_value(
            "1e"
        )
        saved(target)
    finally:
        reopened.close()


def test_queued_writes_cannot_overwrite_new_owner_after_pagehide(page, open_workspace):
    open_workspace()
    saved(page)
    original = analysis_id(page)
    other = page.context.new_page()
    open_workspace(other)
    page.evaluate("""() => {
      window.heldCompletions = [];
      const descriptor = Object.getOwnPropertyDescriptor(IDBTransaction.prototype, 'oncomplete');
      Object.defineProperty(IDBTransaction.prototype, 'oncomplete', {
        ...descriptor, set(fn) {
          const tx = this;
          descriptor.set.call(tx, event => {
            if (tx.mode === 'readwrite') window.heldCompletions.push(() => fn.call(tx,event));
            else fn.call(tx,event);
          });
        }
      });
      const control = document.querySelector('div').shadowRoot.querySelector('[data-field="frequency:direct:lognormal:p95"]');
      control.value = '27'; control.dispatchEvent(new Event('input'));
      control.value = '39'; control.dispatchEvent(new Event('input'));
    }""")
    page.wait_for_function("heldCompletions.length > 0")
    page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide', {persisted:true}))")
    other.get_by_role("button", name="Retry saving / Edit here", exact=True).click()
    saved(other)
    value = other.get_by_role("textbox", name="P95 incidents/year", exact=True)
    value.fill("99")
    value.press("Enter")
    saved(other)
    page.evaluate("() => { for (const finish of heldCompletions.splice(0)) finish(); }")
    # Wait for the old queue to settle, then read the actual durable database.
    expect(page.locator(".aw-status")).not_to_contain_text("Saving in this browser")
    value = other.evaluate(
        """async ({dbName,key}) => {
      const db = await new Promise((resolve,reject) => {const r=indexedDB.open(dbName);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)});
      const doc = await new Promise((resolve,reject) => {const tx=db.transaction('records','readonly'),r=tx.objectStore('records').get(key);tx.oncomplete=()=>resolve(JSON.parse(r.result.value));tx.onerror=()=>reject(tx.error)});
      db.close();return doc;
    }""",
        {"dbName": DB, "key": PREFIX + "analysis:" + original},
    )
    assert value["frequency"]["direct"]["lognormal"]["p95"] == 99
    other.close()


def test_unreadable_durable_only_original_is_discoverable(page, open_workspace):
    open_workspace()
    saved(page)
    original = analysis_id(page)
    raw = '{"format":"security-annual-loss-analysis","version":999}'
    page.evaluate(
        """async ({dbName,key,raw}) => {
      const db = await new Promise(resolve => {const r=indexedDB.open(dbName);r.onsuccess=()=>resolve(r.result)});
      await new Promise((resolve,reject) => {
        const tx=db.transaction('records','readwrite',{durability:'strict'});
        tx.objectStore('records').put({value:raw},key);tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error);
      });
      db.close(); localStorage.removeItem(key);
    }""",
        {"dbName": DB, "key": PREFIX + "analysis:" + original, "raw": raw},
    )
    open_workspace()
    expect(page.get_by_role("button", name="Download original", exact=True)).to_be_visible()
    assert download(page, "Download original") == raw
