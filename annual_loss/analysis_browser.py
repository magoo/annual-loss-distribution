"""Browser-local library and persistent annual-loss editor.

Storage lifecycle adapted from security-org-planning's budget_browser.py. The
portable schema is shared separately so browser/Python parity can be tested.
"""

from .analysis_schema import SCHEMA_MODULE

BROWSER_MODULE = (
    SCHEMA_MODULE
    + r"""
function browserLocks() { try { return navigator.locks || null; } catch (_) { return null; } }
export class AnalysisLibrary {
  constructor(storage) {
    this.storage = storage;
    this.volatile = new Map();
    this.issues = [];
    this.error = storage ? "" : "Browser storage is unavailable.";
  }
  scan() {
    const docs = new Map();
    this.issues = [];
    if (this.storage) {
      try {
        const storageKeys = [];
        for (let i = 0; i < this.storage.length; i++) storageKeys.push(this.storage.key(i));
        for (const key of storageKeys.filter(key => key && key.startsWith(RECORD))) {
          const raw = this.storage.getItem(key);
          try {
            const doc = validateDocument(JSON.parse(raw));
            require(key === RECORD + doc.id, "Record ID does not match its storage key");
            docs.set(doc.id, doc);
          } catch (error) { this.issues.push({key, raw, message: error.message}); }
        }
        // A checkpoint remains discoverable even if its primary record is missing.
        for (const key of storageKeys.filter(key => key && key.startsWith(CHECKPOINT))) {
          const id = key.slice(CHECKPOINT.length);
          if (!storageKeys.includes(RECORD + id)) this.issues.push({
            key: RECORD + id, raw: "", message: "The analysis record is missing; a recovery checkpoint remains."
          });
        }
      } catch (error) { this.error = error.message; }
    }
    for (const [id, doc] of this.volatile) docs.set(id, doc);
    return [...docs.values()].sort((a,b) => a.name.localeCompare(b.name) || a.id.localeCompare(b.id));
  }
  load(id) {
    if (this.volatile.has(id)) return clone(this.volatile.get(id));
    require(this.storage, "Browser storage is unavailable");
    const doc = validateDocument(JSON.parse(this.storage.getItem(RECORD + id)));
    require(doc.id === id, "Record ID does not match its storage key");
    return doc;
  }
  checkpoint(id) {
    require(this.storage, "Browser storage is unavailable");
    const doc = validateDocument(JSON.parse(this.storage.getItem(CHECKPOINT + id)));
    require(doc.id === id, "Checkpoint ID does not match");
    return doc;
  }
  save(doc, baseline) {
    this.volatile.set(doc.id, clone(doc));
    try {
      require(this.storage, "Browser storage is unavailable");
      validateDocument(doc);
      if (baseline) this.storage.setItem(CHECKPOINT + doc.id, JSON.stringify(baseline));
      this.storage.setItem(RECORD + doc.id, JSON.stringify(doc));
      this.error = "";
      return true;
    } catch (error) { this.error = error.message; return false; }
  }
  uniqueName(requested, exceptId = null) {
    const names = new Set(this.scan().filter(doc => doc.id !== exceptId).map(doc => doc.name.toLowerCase()));
    const base = requested.trim() || "Analysis";
    let name = base, i = 2;
    while (names.has(name.toLowerCase())) name = base + " (" + i++ + ")";
    return name;
  }
  copy(doc, requested) {
    const now = new Date().toISOString();
    return {...clone(doc), id: newId(), name: this.uniqueName(requested), created_at: now, updated_at: now};
  }
}

function openDurableStore() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("security-org-planning-annual-loss-analyses", 1);
    request.onupgradeneeded = () => request.result.createObjectStore("records");
    request.onerror = () => reject(request.error);
    request.onblocked = () => reject(new Error("Close older app tabs to finish opening crash recovery storage."));
    request.onsuccess = () => resolve(request.result);
  });
}
function durableWrite(db, entries) {
  return new Promise((resolve, reject) => {
    if (!db) { reject(new Error("Crash recovery storage is unavailable")); return; }
    const tx = db.transaction("records", "readwrite", {durability: "strict"});
    if (tx.durability !== "strict") { tx.abort(); reject(new Error("Strict durable storage is unavailable")); return; }
    for (const [key, value] of entries) tx.objectStore("records").put(value, key);
    tx.oncomplete = resolve;
    tx.onerror = () => reject(tx.error || new Error("Browser storage transaction failed"));
    tx.onabort = () => reject(tx.error || new Error("Crash recovery write was interrupted"));
  });
}
async function restoreDurableStore(db, storage) {
  const entries = await new Promise((resolve, reject) => {
    const tx = db.transaction("records", "readonly");
    const keys = tx.objectStore("records").getAllKeys(), values = tx.objectStore("records").getAll();
    tx.oncomplete = () => resolve(keys.result.map((key, i) => [key, values.result[i]]));
    tx.onerror = () => reject(tx.error || new Error("Browser storage transaction failed"));
    tx.onabort = () => reject(tx.error || new Error("Crash recovery read was interrupted"));
  });
  for (const [key, entry] of entries) {
    if (typeof key !== "string" || !object(entry)) continue;
    if (key === ACTIVE) {
      if (storage.getItem(key) === null && typeof entry.value === "string") storage.setItem(key, entry.value);
      continue;
    }
    const prefix = key.startsWith(RECORD) ? RECORD : key.startsWith(CHECKPOINT) ? CHECKPOINT : null;
    if (!prefix) continue;
    const id = key.slice(prefix.length);
    if (!identifier(id)) continue;
    // Startup recovery must not overwrite a live writer in another tab.
    await browserLocks().request(PREFIX + "lock:" + id, {ifAvailable: true}, async lock => {
      if (!lock) return;
      // Reread the durable entry under the lock: the initial scan may be stale.
      const latest = await new Promise((resolve, reject) => {
        const tx = db.transaction("records", "readonly"), read = tx.objectStore("records").get(key);
        tx.oncomplete = () => resolve(read.result); tx.onerror = () => reject(tx.error || new Error("Browser storage transaction failed"));
        tx.onabort = () => reject(tx.error || new Error("Crash recovery read was interrupted"));
      });
      if (!object(latest)) return;
      if (latest.deleted === true) { storage.removeItem(key); return; }
      let recovered, existing;
      const raw = storage.getItem(key);
      try {
        recovered = validateDocument(JSON.parse(latest.value));
        require(recovered.id === id, "Crash recovery ID does not match");
        if (raw !== null) existing = validateDocument(JSON.parse(raw));
      } catch (_) {
        // A durable-only unreadable original must remain discoverable in the
        // recovery UI too. Never replace an existing local original with it.
        if (raw === null && typeof latest.value === "string") storage.setItem(key, latest.value);
        return;
      }
      if (existing && existing.updated_at >= recovered.updated_at) return;
      storage.setItem(key, latest.value);
    });
  }
}

function download(name, content) {
  const url = URL.createObjectURL(new Blob([content], {type: "application/json"}));
  const link = document.createElement("a");
  link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function filename(name) { return (name.replace(/[^a-z0-9._-]+/gi, "-").replace(/^-|-$/g, "") || "analysis") + ".analysis.json"; }
function button(label, action, parent) {
  const el = document.createElement("button");
  el.type = "button"; el.textContent = label; el.addEventListener("click", action);
  parent.append(el); return el;
}

function render({model, el}) {
  el.classList.add("analysis-workspace");
  let storage;
  try { storage = window.localStorage; void storage.length; } catch (_) { storage = null; }
  const library = new AnalysisLibrary(storage), defaults = clone(model.get("defaults"));
  let current = null, baseline = null, checkpointSaved = false, editable = false;
  let release = null, lockTask = Promise.resolve(), generation = 0, disposed = false, busy = false;
  let token = "", emitTimer = null, saved = false, warning = "", storageWarning = "", activation = "", awaiting = false, lastResponse = null;
  let currentPersisted = false;
  const baselines = new Map(), checkpointed = new Set();
  const lastStored = new Map();
  let durable = null, durableError = "", pendingWrite = Promise.resolve(), saving = false;
  el.innerHTML = '<section class="ald-surface aw-library" aria-label="Saved analyses">' +
    '<h2>Your analyses</h2><div class="aw-actions"><label>Analysis <select aria-label="Analysis"></select></label></div>' +
    '<div class="aw-backups"></div><p class="aw-status" role="status" aria-live="polite"></p>' +
    '<p class="aw-note">Saved only in this browser profile. Clearing site data can remove these analyses. Download a backup to keep elsewhere.</p>' +
    '<p class="aw-warning" role="alert"></p><div class="aw-issues"></div></section>' +
    '<div class="aw-editor"></div><p class="aw-pending" role="status"></p>';
  const selector = el.querySelector("select"), actions = el.querySelector(".aw-actions");
  const backups = el.querySelector(".aw-backups"), status = el.querySelector(".aw-status");
  const alert = el.querySelector(".aw-warning"), editor = el.querySelector(".aw-editor");
  const pending = el.querySelector(".aw-pending"), issues = el.querySelector(".aw-issues");
  const controls = {};

  function message(value) { warning = value; updateStatus(); }
  function updateStatus() {
    status.textContent = !current ? "Loading saved analyses…" : busy ? "Updating analyses…" : !editable
      ? "Viewing this analysis · another tab may be editing it"
      : saving ? "Saving in this browser…"
      : saved ? "Saved in this browser · " + new Date(current.updated_at).toLocaleString()
      : "Not saved in this browser · download a backup";
    status.dataset.saved = String(saved && !busy && !saving);
    const otherUnsaved = [...library.volatile.keys()].filter(id => !current || id !== current.id).length;
    alert.textContent = [warning, storageWarning, otherUnsaved
      ? otherUnsaved + " other analyses are not saved. Back up all analyses before closing."
      : ""].filter(Boolean).join(" ");
    controls.rename.disabled = busy || !editable;
    controls.delete.disabled = busy || !editable;
    controls.retry.disabled = busy || !current;
    let hasCheckpoint = false;
    try { hasCheckpoint = current && storage && storage.getItem(CHECKPOINT + current.id) !== null; } catch (_) {}
    controls.recover.disabled = busy || !hasCheckpoint;
    controls.recover.title = hasCheckpoint ? "Create a copy of the previous session" : "Available after editing a previously saved analysis";
    controls.duplicate.disabled = busy || !current;
    controls.download.disabled = !current;
    controls.new.disabled = busy;
    controls.import.disabled = busy;
    selector.disabled = busy;
  }
  function activeDrafts() {
    const active = activeFields(current);
    return Object.keys(current.drafts).some(path => active.has(path));
  }
  function publish(immediate = false, action = "preview") {
    if (!current) return;
    token = newId(); awaiting = true;
    clearTimeout(emitTimer);
    // Inputs stay in the browser; only explicit snapshots cross the worker bridge.
    const request = {analysis: clone(current), activation, token, action};
    const send = () => {
      if (disposed || request.activation !== activation || request.token !== token) return;
      model.set("request", request); model.save_changes();
    };
    if (immediate) send(); else emitTimer = setTimeout(send, 180);
    updateCalculation();
  }
  function updateCalculation() {
    const calculate = editor.querySelector('[data-action="calculate"]');
    if (calculate) calculate.disabled = !current || awaiting || activeDrafts() ||
      Boolean(lastResponse && Object.keys(lastResponse.errors).length);
    pending.textContent = awaiting ? "Updating this analysis…" : "";
  }
  function acceptResponse() {
    const response = model.get("response");
    if (!current || !response || response.analysis_id !== current.id ||
        response.activation !== activation || response.token !== token) return;
    awaiting = false; lastResponse = response;
    renderResponse(response); updateCalculation();
  }

  function remember() {
    if (!storage || !current || !currentPersisted) return;
    try { storage.setItem(ACTIVE, current.id); } catch (_) { /* Analysis record is already safe. */ }
  }
  function save() {
    if (!current || !editable) return;
    current.updated_at = new Date(Math.max(Date.now(), Date.parse(current.updated_at) + 1)).toISOString();
    if (!release) {
      library.volatile.set(current.id, clone(current)); saved = false;
      message("Safe browser saving is unavailable. This session stays in memory; download a backup.");
      return;
    }
    const checkpoint = !checkpointSaved ? baseline : null;
    saved = false;
    const localSaved = library.save(current, checkpoint);
    if (localSaved) {
      currentPersisted = true; remember();
      const snapshot = clone(current), serialized = JSON.stringify(snapshot);
      lastStored.set(current.id, serialized);
      const entries = [[RECORD + current.id, {value: serialized}],
        [ACTIVE, {value: current.id}]];
      if (checkpoint) entries.push([CHECKPOINT + current.id, {value: JSON.stringify(checkpoint)}]);
      saving = true;
      const writerLease = release;
      pendingWrite = pendingWrite.then(() => {
        // A pagehide/disposal can release ownership before a queued transaction
        // starts. Such a write must never run behind the next tab's newer save.
        require(writerLease && writerLease === release, "Editing ownership changed before the durable copy completed");
        return durableWrite(durable, entries);
      }).then(() => {
        checkpointed.add(snapshot.id);
        if (library.volatile.get(snapshot.id)?.updated_at === snapshot.updated_at) library.volatile.delete(snapshot.id);
        if (current && current.id === snapshot.id && current.updated_at === snapshot.updated_at) {
          checkpointSaved = true; saved = true; saving = false; storageWarning = ""; updateStatus();
        }
      }).catch(error => {
        if (current && current.id === snapshot.id && current.updated_at === snapshot.updated_at) {
          saving = false;
          storageWarning = "Crash recovery save failed. A local recovery copy may still be available; download a backup. " + (durableError || error.message);
          library.volatile.set(current.id, snapshot);
          updateStatus();
        }
      });
    } else {
      saving = false;
      storageWarning = "Autosave failed. Your work is still here; download a backup. " + library.error;
    }
    updateStatus();
  }
  function refreshLibrary() {
    const docs = library.scan();
    if (current && !docs.some(doc => doc.id === current.id)) docs.push(current);
    selector.replaceChildren();
    for (const doc of docs) {
      const option = document.createElement("option");
      option.value = doc.id; option.textContent = doc.name; selector.append(option);
    }
    selector.value = current ? current.id : "";
    issues.replaceChildren();
    for (const issue of library.issues) {
      const row = document.createElement("div"), text = document.createElement("p");
      text.textContent = "A saved analysis could not be opened. " + issue.message;
      row.append(text);
      button("Download original", () => download("unreadable-analysis.json", issue.raw || ""), row);
      button("Recover checkpoint", () => run(async () => {
        const restored = library.checkpoint(issue.key.slice(RECORD.length));
        await activate(library.copy(restored, restored.name + " recovered"), true);
      }), row);
      issues.append(row);
    }
  }
  async function run(action) {
    if (busy) return;
    busy = true; updateStatus();
    try { await action(); } catch (error) { message(error.message); }
    finally { busy = false; if (!disposed) { refreshLibrary(); updateStatus(); } }
  }
  async function activate(doc, isNew = false) {
    const gen = ++generation;
    if (current && !saved && editable) library.volatile.set(current.id, clone(current));
    clearTimeout(emitTimer);
    editable = false;
    for (const input of editor.querySelectorAll("input:not([type=checkbox]), select, button")) input.disabled = true;
    // Finish durable writes while still holding the previous analysis's lock.
    await pendingWrite;
    if (release) release();
    release = null; saving = false;
    await lockTask;
    if (disposed || gen !== generation) return;
    activation = newId(); awaiting = false; lastResponse = null;
    current = clone(doc); baseline = isNew ? null : clone(doc);
    checkpointSaved = checkpointed.has(doc.id); currentPersisted = false; saved = false;
    try { currentPersisted = Boolean(storage && storage.getItem(RECORD + doc.id) !== null); } catch (_) {}
    warning = ""; storageWarning = "";
    const canCoordinate = storage && browserLocks();
    let conflictCopy = null;
    if (!canCoordinate) {
      editable = true; saved = false;
      warning = "Safe browser saving is unavailable. This session stays in memory; download a backup.";
      library.volatile.set(current.id, clone(current));
    } else {
      await new Promise(resolve => {
        lockTask = browserLocks().request(PREFIX + "lock:" + doc.id, {ifAvailable: true}, async lock => {
          if (disposed || gen !== generation || !lock) { resolve(); return; }
          // Read after taking the lock, never write the earlier selector snapshot.
          if (!isNew && library.volatile.has(doc.id)) {
            const raw = storage.getItem(RECORD + doc.id);
            const expected = lastStored.get(doc.id) || null;
            if (raw !== expected) {
              library.volatile.delete(doc.id);
              conflictCopy = library.copy(current, current.name + " unsaved copy");
              library.volatile.set(conflictCopy.id, conflictCopy);
              resolve(); return;
            }
          }
          if (!isNew && !library.volatile.has(doc.id)) {
            try { current = library.load(doc.id); baseline = clone(current); lastStored.set(doc.id, JSON.stringify(current)); }
            catch (error) {
              warning = "The saved record changed and could not be reopened. " + error.message;
              saved = false; resolve(); return;
            }
          }
          editable = true;
          if (!baselines.has(current.id)) baselines.set(current.id, baseline);
          baseline = baselines.get(current.id);
          await new Promise(unlock => { release = unlock; resolve(); });
        }).catch(error => {
          editable = true; saved = false;
          library.volatile.set(current.id, clone(current));
          warning = "Safe browser saving is unavailable. Download a backup. " + error.message;
          resolve();
        });
      });
    }
    if (disposed || gen !== generation) return;
    if (conflictCopy) {
      await activate(conflictCopy, true);
      message("Another tab changed the original analysis. Your unsaved edits were preserved in a separate copy.");
      return;
    }
    if (editable && (isNew || library.volatile.has(current.id))) save();
    else if (editable && release) {
      saved = false; saving = true; updateStatus();
      try {
        await durableWrite(durable, [
          [RECORD + current.id, {value: JSON.stringify(current)}],
          [ACTIVE, {value: current.id}],
        ]);
        saved = true; library.volatile.delete(current.id);
      } catch (error) {
        storageWarning = "Crash recovery save failed. Download a backup. " + (durableError || error.message);
        library.volatile.set(current.id, clone(current));
      }
      saving = false;
    }
    if (!editable && !warning) warning = "This analysis is open in another tab. Close that tab and choose Retry saving / Edit here, or duplicate this analysis.";
    if (!currentPersisted) library.volatile.set(current.id, clone(current));
    remember(); refreshLibrary(); renderEditor(); updateStatus(); publish(true);
  }
  const distributionOptions = [["lognormal", "Lognormal"], ["pert", "PERT"], ["pareto", "Pareto"]];
  const methodOptions = [["odds", "1 in N years"], ["lognormal", "Lognormal (P50 / P95)"],
    ["pert", "PERT (minimum / likely / maximum)"], ["pareto", "Pareto (P50 / P95)"]];
  const modes = [["direct", "Direct estimate"], ["panel", "Expert panel"], ["scenario", "Threat scenarios"]];
  const fieldLabels = {
    frequency: {odds: "One incident every N years", p50: "P50 median incidents/year", p95: "P95 incidents/year",
      min: "Minimum incidents/year", mode: "Most likely incidents/year", max: "Maximum incidents/year"},
    cost: {p50: "P50 median cost ($)", p95: "P95 cost ($)", min: "Minimum cost ($)", mode: "Most likely cost ($)", max: "Maximum cost ($)"}
  };
  let plotQueue = Promise.resolve(), lastLoss = null, plotGeneration = 0;
  function node(tag, text = "", className = "") {
    const element = document.createElement(tag); element.className = className;
    if (text) element.textContent = text; return element;
  }
  function heading(title, description = "") {
    const element = node("div", "", "ald-panel-heading");
    element.append(node("strong", title), node("span", description)); return element;
  }
  function step(number, title, description) {
    const element = node("header", "", "ald-step-header");
    element.append(node("span", "Step " + number, "ald-kicker"), node("h2", title), node("p", description)); return element;
  }
  function rawValue(path, value) { return Object.hasOwn(current.drafts, path) ? current.drafts[path] : String(value); }
  function input(path, label, placeholder = "") {
    const [parent, field, numeric] = editableFields(current).get(path);
    const wrapper = node("label", "", "aw-field"); wrapper.append(node("span", label));
    const control = node("input"); control.type = "text"; control.value = rawValue(path, parent[field]);
    control.dataset.field = path; control.setAttribute("aria-label", label); control.placeholder = placeholder;
    if (numeric) control.inputMode = "decimal";
    control.autocomplete = "off"; control.disabled = !editable;
    const error = node("span", "", "aw-field-error"); error.dataset.errorFor = path;
    const syncDraft = () => {
      const draft = Object.hasOwn(current.drafts, path);
      control.classList.toggle("aw-draft", draft);
      error.textContent = draft ? "Unfinished edit saved with this analysis. Press Enter to apply." : "";
    };
    control.addEventListener("input", () => {
      if (!editable) return;
      current.drafts[path] = control.value; syncDraft(); save(); publish();
    });
    const commit = () => {
      if (!editable || !Object.hasOwn(current.drafts, path)) return;
      if (commitField(current, path)) { syncDraft(); save(); publish(true); }
      else {
        control.setAttribute("aria-invalid", "true");
        error.textContent = path === "seed" ? "Enter a non-negative whole-number seed (up to 9007199254740991)." : "Finish this number. Your typing is saved.";
      }
    };
    control.addEventListener("blur", commit);
    control.addEventListener("keydown", event => {
      if (event.key === "Enter" && !event.ctrlKey && !event.metaKey) { event.preventDefault(); commit(); }
    });
    syncDraft(); wrapper.append(control, error); return wrapper;
  }
  function select(label, options, selected, change) {
    const wrapper = node("label", "", "aw-field"); wrapper.append(node("span", label));
    const control = node("select"); control.setAttribute("aria-label", label); control.disabled = !editable;
    for (const [value, text] of options) { const option = node("option", text); option.value = value; control.append(option); }
    control.value = selected;
    control.addEventListener("change", () => { if (editable) change(control.value); });
    wrapper.append(control); return wrapper;
  }
  function radios(label, options, selected, change) {
    const group = node("fieldset", "", "aw-radios"); group.append(node("legend", label));
    for (const [value, text] of options) {
      const wrapper = node("label"), control = node("input"); control.type = "radio";
      control.name = activation + ":" + label; control.value = value; control.checked = value === selected; control.disabled = !editable;
      control.addEventListener("change", () => { if (editable && control.checked) change(value); });
      wrapper.append(control, document.createTextNode(text)); group.append(wrapper);
    }
    return group;
  }
  function changed(structure = false, action = "preview") {
    save(); if (structure) renderInputs(); publish(true, action);
  }
  function slider(label, field, min, max, increment) {
    const wrapper = node("label", "", "aw-field"), value = node("output", String(current.view[field]));
    wrapper.append(node("span", label), value);
    const control = node("input"); control.type = "range"; control.min = min; control.max = max; control.step = increment;
    control.value = current.view[field]; control.disabled = !editable; control.setAttribute("aria-label", label);
    control.addEventListener("input", () => {
      if (!editable) return;
      current.view[field] = Number(control.value); value.textContent = control.value; save(); publish(false, "view");
    }); wrapper.append(control); return wrapper;
  }
  function group(title, children) {
    const element = node("div", "", "ald-scenario-group");
    element.append(node("span", title, "ald-scenario-group-label"), ...children); return element;
  }
  function parameters(section, method, path) {
    const element = node("div", "", "aw-parameters");
    for (const field of parameterFields(method)) element.append(input(path + field, fieldLabels[section][field]));
    return element;
  }
  function removeDrafts(prefix) {
    for (const key of Object.keys(current.drafts)) if (key.startsWith(prefix)) delete current.drafts[key];
  }
  function panelEditor(section) {
    const panel = current[section].panel, distribution = current[section].distribution;
    const element = node("div", "", "ald-panel-editor");
    element.append(node("p", "Add or delete panelists below. At least two valid expert estimates are averaged parameter-by-parameter."));
    const list = node("div", "", "ald-panelist-list"); list.setAttribute("role", "list");
    for (const row of panel.rows) {
      const prefix = `${section}:panel:${row.id}:`, article = node("article", "", "ald-panelist-row" + (panel.rows.length > 2 ? " ald-panelist-row--with-actions" : ""));
      article.setAttribute("role", "listitem"); article.dataset.rowId = row.id;
      article.append(input(prefix + "name", "Panelist name", "Name this panelist"), parameters(section, distribution, prefix));
      if (panel.rows.length > 2) button("Delete panelist", () => {
        panel.rows = panel.rows.filter(item => item.id !== row.id); removeDrafts(prefix); changed(true);
      }, article).disabled = !editable;
      list.append(article);
    }
    element.append(list);
    button("Add panelist", () => {
      if (!safeInteger(panel.next_id + 1)) { message("No further panelist IDs are available."); return; }
      const id = panel.next_id++; panel.rows.push({id, name: "Panelist " + id, ...parameterDefaults(section)}); changed(true);
    }, element).disabled = !editable;
    const analytics = node("div", "", "aw-panel-analytics"); analytics.dataset.panel = section; element.append(analytics); return element;
  }
  function scenarioEditor() {
    const element = node("section", "", "ald-surface ald-scenario-editor");
    element.append(heading("Shared threat scenarios", "Each row pairs its frequency with its cost; annual losses sum across all rows."));
    const list = node("div", "", "ald-scenario-list"); list.setAttribute("role", "list");
    for (const [index, row] of current.scenarios.rows.entries()) {
      const prefix = `scenario:${rowKey(row.id)}:`, article = node("article", "", "ald-scenario-row ald-scenario-row--two-models" +
        (current.scenarios.rows.length > 1 ? " ald-scenario-row--with-actions" : ""));
      article.setAttribute("role", "listitem"); article.dataset.rowId = rowKey(row.id);
      article.append(group("Scenario " + (index + 1), [input(prefix + "name", "Scenario name", "Name this threat scenario")]));
      for (const section of ["frequency", "cost"]) {
        const field = section === "frequency" ? "frequency_method" : "cost_dist_type";
        const controls = [select(section === "frequency" ? "Frequency method" : "Cost distribution",
          section === "frequency" ? methodOptions : methodOptions.slice(1), row[field], value => { row[field] = value; changed(true); }),
          parameters(section, row[field], prefix + section + "_")];
        article.append(group(section === "frequency" ? "Frequency" : "Cost", controls));
      }
      if (current.scenarios.rows.length > 1) button("Remove", () => {
        current.scenarios.rows = current.scenarios.rows.filter(item => item.id !== row.id); removeDrafts(prefix); changed(true);
      }, article).disabled = !editable;
      list.append(article);
    }
    element.append(list);
    button("Add scenario", () => {
      if (!safeInteger(current.scenarios.next_id + 1)) { message("No further scenario IDs are available."); return; }
      const id = current.scenarios.next_id++, row = {id, name: "New scenario " + id, frequency_method: "odds", frequency_odds: 10, cost_dist_type: "lognormal"};
      for (const section of ["frequency", "cost"]) for (const [field, value] of Object.entries(parameterDefaults(section))) row[section + "_" + field] = value;
      current.scenarios.rows.push(row); changed(true);
    }, element).disabled = !editable;
    return element;
  }
  function renderInputs() {
    for (const section of ["frequency", "cost"]) {
      const container = editor.querySelector(`[data-inputs="${section}"]`);
      const source = current[section], mode = current.workflow[section + "_mode"], card = node("section", "", "ald-surface ald-input-card");
      card.append(heading("Model inputs", "Choose an elicitation source and shape for this distribution."),
        radios((section === "frequency" ? "Frequency" : "Cost") + " input source", modes, mode,
          value => { current.workflow = selectMode(current.workflow, section, value); changed(true); }));
      if (mode !== "scenario") card.append(select((section === "frequency" ? "Frequency" : "Cost") + " distribution", distributionOptions,
        source.distribution, value => { source.distribution = value; changed(true); }));
      if (mode === "direct") card.append(parameters(section, source.distribution, `${section}:direct:${source.distribution}:`));
      else if (mode === "panel") card.append(panelEditor(section));
      else card.append(node("p", "Scenario mode links Frequency and Cost. Configure the paired models in the shared editor below Frequency."));
      container.replaceChildren(card);
      if (mode === "scenario" && section === "frequency") container.append(scenarioEditor());
      editor.querySelector(`[data-preview-title="${section}"]`).textContent = (mode === "scenario" ? "Scenario" : distributionOptions.find(o => o[0] === source.distribution)[1]) + " preview";
    }
  }
  function renderEditor() {
    ++plotGeneration; lastLoss = null;
    for (const chart of editor.querySelectorAll(".js-plotly-plot")) Plotly.purge(chart);
    editor.replaceChildren();
    const toolbar = node("section", "", "ald-surface ald-toolbar aw-toolbar");
    toolbar.append(heading("View controls", "Updates every preview and result chart."),
      radios("Chart view", [["pdf", "Histogram"], ["cdf", "CDF"]], current.view.chart, value => { current.view.chart = value; changed(false, "view"); }),
      slider("Outcome percentile", "focus_percentile", 95, 99.9, 0.1), slider("Central range (%)", "confidence_level", 50, 95, 1));
    editor.append(toolbar);
    const feedback = node("div", "", "aw-model-errors"); feedback.setAttribute("role", "alert"); editor.append(feedback);
    for (const [index, section] of ["frequency", "cost"].entries()) {
      const shell = node("section", "", "aw-section"); shell.dataset.section = section;
      shell.append(step(index + 1, section === "frequency" ? "Frequency" : "Cost", model.get("guidance")[section]));
      const inputs = node("div", "", "aw-inputs"); inputs.dataset.inputs = section;
      const preview = node("section", "", "ald-surface ald-preview-card"), title = heading("", "Inspect the modeled shape before calculating annual loss.");
      title.querySelector("strong").dataset.previewTitle = section;
      const chart = node("div", "", "aw-chart"); chart.dataset.chart = section;
      const statement = node("p", "Complete valid inputs to render this preview.", "ald-insight"); statement.dataset.statement = section;
      preview.append(title, chart, statement); shell.append(inputs, preview); editor.append(shell);
    }
    const calculateSection = node("section", "", "aw-section"); calculateSection.dataset.section = "calculate";
    calculateSection.append(step(3, "Calculate annual loss", "Run the annual model when the inputs look right. Later edits will not change the result until you explicitly recalculate."));
    const run = node("section", "", "ald-surface ald-input-card");
    run.append(heading("Simulation run", "Set a seed, then snapshot the current valid inputs."), input("seed", "Reproducibility seed"));
    const calculate = button("Calculate / Recalculate annual loss", () => publish(true, "calculate"), run);
    calculate.dataset.action = "calculate"; calculate.className = "aw-primary";
    const results = node("div", "", "aw-results"); calculateSection.append(run, results); editor.append(calculateSection);
    renderInputs(); updateCalculation();
  }
  function renderChart(element, figure) {
    const generation = plotGeneration;
    // Serialize Plotly DOM updates; neither results nor plots may touch input nodes.
    plotQueue = plotQueue.then(async () => {
      if (disposed || generation !== plotGeneration || !element.isConnected) return;
      if (!figure) { if (element.classList.contains("js-plotly-plot")) Plotly.purge(element); element.replaceChildren(); return; }
      await Plotly.react(element, figure.data, figure.layout, {displaylogo: false, responsive: true});
      const root = el.getRootNode();
      if (root instanceof ShadowRoot && !root.querySelector(".aw-plotly-styles")) {
        const style = node("style", "", "aw-plotly-styles");
        style.textContent = [...document.querySelectorAll('style[id^="plotly.js-style"]')].flatMap(s => [...(s.sheet?.cssRules || [])].map(r => r.cssText)).join("\n"); root.append(style);
      }
    }).catch(error => { message("Chart could not be displayed: " + error.message); });
  }
  function renderResponse(response) {
    ++plotGeneration;
    const errors = response.errors || {}, feedback = editor.querySelector(".aw-model-errors");
    feedback.replaceChildren();
    if (Object.keys(errors).length) {
      feedback.append(node("strong", "Resolve these inputs before calculating:"));
      const list = node("ul"); for (const [path, message] of Object.entries(errors)) list.append(node("li", path + ": " + message)); feedback.append(list);
    }
    for (const input of editor.querySelectorAll("input[data-field]")) {
      const error = errors[input.dataset.field];
      input.setAttribute("aria-invalid", String(Boolean(error)));
      input.closest("label").querySelector(".aw-field-error").textContent = error ||
        (Object.hasOwn(current.drafts, input.dataset.field) ? "Unfinished edit saved with this analysis." : "");
    }
    for (const section of ["frequency", "cost"]) {
      const preview = response.previews[section];
      renderChart(editor.querySelector(`[data-chart="${section}"]`), preview?.figure);
      editor.querySelector(`[data-statement="${section}"]`).textContent = preview?.statement || "Complete valid inputs to render this preview.";
      const analytics = editor.querySelector(`[data-panel="${section}"]`);
      if (analytics) {
        analytics.replaceChildren(); const rows = response.panels[section] || [];
        if (rows.length) {
          const table = node("table"), head = node("tr"); for (const key of Object.keys(rows[0])) head.append(node("th", key));
          table.append(head); for (const row of rows) { const tr = node("tr"); for (const value of Object.values(row)) tr.append(node("td", String(value))); table.append(tr); } analytics.append(table);
        }
      }
    }
    if (response.loss) renderLoss(response.loss);
  }
  function renderLoss(loss) {
    const results = editor.querySelector(".aw-results");
    if (!lastLoss) {
      const range = node("section", "", "ald-surface ald-result-card"); range.append(heading("Decision range", "Central modeled annual-loss outcomes."), node("div", "", "aw-stats"));
      const plot = node("section", "", "ald-surface ald-result-card"), chart = node("div", "", "aw-chart"); chart.dataset.chart = "loss";
      plot.append(chart, node("p", "", "ald-meta"));
      const narrative = node("section", "", "ald-narrative"); narrative.append(node("h3", "Modeled outcome ranges"), node("ul"));
      const report = node("section", "", "ald-surface ald-report-card"), details = node("details");
      details.append(node("summary", "Executive Summary"), node("pre", "", "aw-report")); report.append(details);
      const copy = button("Copy", async () => {
        try {
          try { await navigator.clipboard.writeText(lastLoss.summary); }
          catch (_) {
            const area = node("textarea"); area.value = lastLoss.summary; area.style.cssText = "position:fixed;left:-9999px;top:0";
            el.append(area); area.select(); const copied = document.execCommand("copy"); area.remove();
            if (!copied) throw new Error("Clipboard unavailable");
          }
          copy.textContent = "Copied";
        } catch (_) { copy.textContent = "Try again"; }
      }, report); copy.setAttribute("aria-label", "Copy executive summary to clipboard");
      results.append(range, plot, narrative, report);
    }
    lastLoss = loss;
    const stats = results.querySelector(".aw-stats"); stats.replaceChildren();
    for (const stat of loss.stats) { const item = node("div"); item.append(node("span", stat.label), node("strong", stat.value)); stats.append(item); }
    renderChart(results.querySelector('[data-chart="loss"]'), loss.figure);
    results.querySelector(".ald-meta").textContent = loss.meta;
    results.querySelector(".aw-report").textContent = loss.summary;
    const narrative = results.querySelector(".ald-narrative ul"); narrative.replaceChildren(...loss.narrative.map(text => node("li", text)));
  }
  editor.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault(); const calculate = editor.querySelector('[data-action="calculate"]');
      if (calculate && !calculate.disabled) calculate.click();
    }
  });

  controls.new = button("New", () => run(async () => {
    const name = window.prompt("Name for the new analysis", library.uniqueName("Analysis"));
    if (name !== null) await activate(library.copy(defaults, name), true);
  }), actions);
  controls.rename = button("Rename", () => run(async () => {
    const name = window.prompt("Analysis name", current.name);
    if (name !== null && name.trim()) { current.name = library.uniqueName(name, current.id); save(); publish(true); }
  }), actions);
  controls.duplicate = button("Duplicate", () => run(async () => {
    const copy = library.copy(current, current.name + " copy"); await activate(copy, true);
  }), actions);
  controls.delete = button("Delete", () => run(async () => {
    if (!window.confirm('Delete "' + current.name + '" and its recovery checkpoint? Download a backup first if you want to keep it.')) return;
    if (currentPersisted) require(release && storage && durable, "Restore browser saving before deleting this saved analysis.");
    // Tombstones commit before local removal, so a crash cannot resurrect a deletion.
    if (release && storage) {
      await pendingWrite;
      await durableWrite(durable, [
        [RECORD + current.id, {deleted: true}],
        [CHECKPOINT + current.id, {deleted: true}],
      ]);
      storage.removeItem(RECORD + current.id);
      storage.removeItem(CHECKPOINT + current.id);
    }
    library.volatile.delete(current.id);
    current = null; saved = false;
    const docs = library.scan();
    await activate(docs[0] || library.copy(defaults, "Analysis 1"), !docs.length);
  }), actions);
  controls.download = button("Download analysis", () => download(filename(current.name), serializeBackup([current])), backups);
  controls.all = button("Back up all analyses", () => {
    try {
      const docs = library.scan();
      if (current) {
        const index = docs.findIndex(doc => doc.id === current.id);
        if (index < 0) docs.push(current); else docs[index] = current;
      }
      download("annual-loss-analyses.json", serializeBackup(docs, true));
      if (library.issues.length) message("Readable analyses were downloaded. Use Download original below to keep unreadable records too.");
    } catch (error) { message(error.message); }
  }, backups);
  const file = document.createElement("input");
  file.type = "file"; file.accept = ".json,application/json"; file.hidden = true;
  file.setAttribute("aria-label", "Import backup file"); backups.append(file);
  controls.import = button("Import backup", () => file.click(), backups);
  file.addEventListener("change", () => run(async () => {
    try {
      if (!file.files.length) return;
      require(file.files[0].size <= 10 * 1024 * 1024, "Backup exceeds 10 MiB");
      const docs = parseBackup(await file.files[0].text());
      // Validate the complete file before any library mutation. New IDs never replace existing analyses.
      const copies = [];
      for (const doc of docs) {
        const copy = library.copy(doc, doc.name);
        library.volatile.set(copy.id, copy); copies.push(copy);
      }
      for (const copy of copies) {
        if (storage && browserLocks()) {
          await browserLocks().request(PREFIX + "lock:" + copy.id, async () => {
            if (library.save(copy, null)) {
              lastStored.set(copy.id, JSON.stringify(copy));
              try { await durableWrite(durable, [[RECORD + copy.id, {value: JSON.stringify(copy)}]]); library.volatile.delete(copy.id); }
              catch (error) { library.volatile.set(copy.id, copy); durableError = error.message; }
            }
          });
        }
      }
      await activate(library.load(copies[0].id));
      if (copies.some(copy => library.volatile.has(copy.id))) message("Some imported analyses could not be saved in this browser. They remain available this session; back up all analyses before closing.");
    } finally { file.value = ""; }
  }));
  controls.recover = button("Recover previous session", () => run(async () => {
    const checkpoint = library.checkpoint(current.id);
    await activate(library.copy(checkpoint, current.name + " recovered"), true);
  }), backups);
  controls.retry = button("Retry saving / Edit here", () => run(async () => {
    try { storage = window.localStorage; void storage.length; library.storage = storage; } catch (_) {}
    if (storage && browserLocks() && !durable) {
      try { durable = await openDurableStore(); durableError = ""; } catch (error) { durableError = error.message; }
    }
    await activate(clone(current));
  }), backups);
  selector.addEventListener("change", () => run(() => activate(library.load(selector.value))));
  const onStorage = event => {
    if (!event.key || event.key.startsWith(PREFIX)) {
      refreshLibrary();
      if (current && (!event.key || event.key === RECORD + current.id) && event.newValue === null) {
        saved = false;
        if (editable) library.volatile.set(current.id, clone(current));
        message("This analysis was removed from browser storage. Your open copy is still here; download it or duplicate it.");
      }
      if (current && !editable && event.key === RECORD + current.id && event.newValue) {
        try { current = library.load(current.id); activation = newId(); lastResponse = null; renderEditor(); publish(true); } catch (error) { message(error.message); }
      }
    }
  };
  const onPageHide = () => {
    clearTimeout(emitTimer);
    if (release) release();
    release = null; editable = false;
  };
  const onPageShow = event => {
    if (event.persisted && current) run(() => activate(current));
  };
  window.addEventListener("storage", onStorage);
  window.addEventListener("pagehide", onPageHide);
  window.addEventListener("pageshow", onPageShow);
  let resizeFrame = null, lastWidth = 0;
  const resizeObserver = new ResizeObserver(() => {
    if (disposed || el.clientWidth === lastWidth) return;
    lastWidth = el.clientWidth; cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(() => {
      for (const chart of editor.querySelectorAll(".js-plotly-plot"))
        if (chart.clientWidth && chart.clientHeight) Plotly.Plots.resize(chart).catch(() => {});
    });
  });
  resizeObserver.observe(el);
  model.on("change:response", acceptResponse);
  run(async () => {
    if (storage && browserLocks()) {
      try {
        durable = await openDurableStore();
        await restoreDurableStore(durable, storage);
      } catch (error) { durableError = error.message; }
    }
    const docs = library.scan();
    let active;
    try { active = storage && storage.getItem(ACTIVE); } catch (_) {}
    const chosen = docs.find(doc => doc.id === active) || docs[0];
    await activate(chosen || library.copy(defaults, "Analysis 1"), !chosen);
    if (library.issues.length) message("Some saved records need recovery. Their original data has been preserved below.");
  });
  return () => {
    disposed = true; generation++; clearTimeout(emitTimer);
    if (release) release();
    release = null; editable = false;
    window.removeEventListener("storage", onStorage);
    window.removeEventListener("pagehide", onPageHide);
    window.removeEventListener("pageshow", onPageShow);
    model.off("change:response", acceptResponse);
    resizeObserver.disconnect(); cancelAnimationFrame(resizeFrame);
    for (const chart of editor.querySelectorAll(".js-plotly-plot")) Plotly.purge(chart);
  };
}
export default {render};
"""
)
