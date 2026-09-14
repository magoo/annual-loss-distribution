"""Browser counterpart of the portable document contract; tested against Python."""

SCHEMA_MODULE = r"""
export const PREFIX = "security-org-planning-annual-loss:analyses:v1:";
const RECORD = PREFIX + "analysis:", CHECKPOINT = PREFIX + "checkpoint:", ACTIVE = PREFIX + "active";
const FORMAT = "security-annual-loss-analysis", LIBRARY_FORMAT = "security-annual-loss-library";
const DISTRIBUTIONS = ["lognormal", "pert", "pareto"], FIELDS = ["p50", "p95", "min", "mode", "max"];
const newId = () => typeof crypto.randomUUID === "function" ? crypto.randomUUID() :
  [...crypto.getRandomValues(new Uint8Array(16))].map(byte => byte.toString(16).padStart(2, "0")).join("");
const clone = value => JSON.parse(JSON.stringify(value));
const object = value => value !== null && typeof value === "object" && !Array.isArray(value);
const require = (condition, message) => { if (!condition) throw new Error(message); };
const keys = (value, expected, label) => require(object(value) &&
  Object.keys(value).sort().join("|") === [...expected].sort().join("|"), label + ": unexpected or missing fields");
const identifier = value => typeof value === "string" && /^[a-z0-9][a-z0-9-]{0,100}$/.test(value);
const finite = value => typeof value === "number" && Number.isFinite(value);
const safeInteger = (value, minimum = 0) => Number.isSafeInteger(value) && value >= minimum;
export const rowKey = id => (typeof id === "string" ? "string:" : "integer:") + id;
export const parameterFields = method => method === "pert" ? ["min", "mode", "max"] : method === "odds" ? ["odds"] : ["p50", "p95"];
const parameterDefaults = section => Object.fromEntries(FIELDS.map((f,i) => [f,
  (section === "frequency" ? [1,10,0,1,10] : [50000,500000,1000,50000,500000])[i]]));

export function editableFields(doc) {
  const fields = new Map([["seed", [doc, "seed", true]]]);
  for (const section of ["frequency", "cost"]) {
    for (const [distribution, params] of Object.entries(doc[section].direct))
      for (const field of Object.keys(params)) fields.set(`${section}:direct:${distribution}:${field}`, [params, field, true]);
    for (const row of doc[section].panel.rows)
      for (const field of ["name", ...FIELDS]) fields.set(`${section}:panel:${row.id}:${field}`, [row, field, field !== "name"]);
  }
  for (const row of doc.scenarios.rows) for (const field of Object.keys(row))
    if (!["id", "frequency_method", "cost_dist_type"].includes(field))
      fields.set(`scenario:${rowKey(row.id)}:${field}`, [row, field, field !== "name"]);
  return fields;
}
export function activeFields(doc) {
  const fields = new Set(["seed"]);
  if (doc.workflow.frequency_mode === "scenario") {
    for (const row of doc.scenarios.rows) {
      const prefix = `scenario:${rowKey(row.id)}:`;
      fields.add(prefix + "name");
      for (const [section, method] of [["frequency", row.frequency_method], ["cost", row.cost_dist_type]])
        for (const field of parameterFields(method)) fields.add(prefix + section + "_" + field);
    }
  } else for (const section of ["frequency", "cost"]) {
    const distribution = doc[section].distribution;
    if (doc.workflow[section + "_mode"] === "direct")
      for (const field of parameterFields(distribution)) fields.add(`${section}:direct:${distribution}:${field}`);
    else for (const row of doc[section].panel.rows)
      for (const field of ["name", ...parameterFields(distribution)]) fields.add(`${section}:panel:${row.id}:${field}`);
  }
  return fields;
}
export function selectMode(workflow, section, mode) {
  require(["frequency", "cost"].includes(section) && ["direct", "panel", "scenario"].includes(mode), "Invalid mode selection");
  const next = clone(workflow), other = section === "frequency" ? "cost" : "frequency";
  if (mode === "scenario") { next.frequency_mode = next.cost_mode = "scenario"; }
  else {
    if (workflow.frequency_mode === "scenario") next[other + "_mode"] = workflow["remembered_" + other + "_mode"];
    next[section + "_mode"] = next["remembered_" + section + "_mode"] = mode;
  }
  return next;
}
export function validateDocument(doc) {
  require(object(doc) && doc.format === FORMAT, "Not an annual-loss analysis");
  keys(doc, ["format", "version", "model_version", "id", "name", "created_at", "updated_at", "seed", "view", "workflow", "frequency", "cost", "scenarios", "drafts"], "Analysis");
  require(doc.version === 1, "Unsupported analysis format version; original preserved");
  require(doc.model_version === 1, "Unsupported model version; original preserved");
  require(identifier(doc.id), "Invalid analysis ID");
  require(typeof doc.name === "string" && doc.name.trim(), "Analysis needs a name");
  for (const field of ["created_at", "updated_at"]) {
    require(typeof doc[field] === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(doc[field]) &&
      Number(doc[field].slice(0, 4)) >= 1 && Number.isFinite(Date.parse(doc[field])) && new Date(doc[field]).toISOString() === doc[field], "Invalid " + field);
  }
  require(safeInteger(doc.seed), "Seed must be a non-negative safe integer");
  keys(doc.view, ["chart", "focus_percentile", "confidence_level"], "View settings");
  require(["pdf", "cdf"].includes(doc.view.chart), "Unsupported chart view");
  require(finite(doc.view.focus_percentile) && doc.view.focus_percentile >= 95 && doc.view.focus_percentile <= 99.9, "Outcome percentile must be between 95 and 99.9");
  require(safeInteger(doc.view.confidence_level, 50) && doc.view.confidence_level <= 95, "Central range must be between 50 and 95");
  keys(doc.workflow, ["frequency_mode", "cost_mode", "remembered_frequency_mode", "remembered_cost_mode"], "Workflow");
  for (const section of ["frequency", "cost"]) {
    const mode = doc.workflow[section + "_mode"], remembered = doc.workflow["remembered_" + section + "_mode"];
    require(["direct", "panel", "scenario"].includes(mode) && ["direct", "panel"].includes(remembered), "Invalid workflow mode");
    require(mode === "scenario" || mode === remembered, "Remembered mode must match active mode");
  }
  require((doc.workflow.frequency_mode === "scenario") === (doc.workflow.cost_mode === "scenario"), "Scenario modes must be linked");
  for (const section of ["frequency", "cost"]) {
    const source = doc[section]; keys(source, ["distribution", "direct", "panel"], section);
    require(DISTRIBUTIONS.includes(source.distribution), "Unsupported distribution");
    keys(source.direct, DISTRIBUTIONS, "Direct estimates");
    for (const [distribution, params] of Object.entries(source.direct)) {
      keys(params, parameterFields(distribution), "Direct parameters");
      require(Object.values(params).every(finite), "Invalid direct parameter type");
    }
    const panel = source.panel; keys(panel, ["rows", "next_id"], "Panel");
    require(Array.isArray(panel.rows) && panel.rows.length >= 2, "Panel requires at least two experts");
    const ids = new Set(); let maximum = 0;
    for (const row of panel.rows) {
      keys(row, ["id", "name", ...FIELDS], "Panelist");
      require(safeInteger(row.id, 1) && !ids.has(row.id), "Invalid or duplicate panelist ID");
      ids.add(row.id); maximum = Math.max(maximum, row.id);
      require(typeof row.name === "string", "Invalid panelist name");
      require(FIELDS.every(field => finite(row[field])), "Invalid panel parameter type");
    }
    require(safeInteger(panel.next_id, 1) && panel.next_id > maximum, "Invalid panel next_id");
  }
  keys(doc.scenarios, ["rows", "next_id"], "Scenarios");
  require(Array.isArray(doc.scenarios.rows) && doc.scenarios.rows.length, "At least one scenario is required");
  const ids = new Set(), numeric = ["frequency_odds", ...["frequency", "cost"].flatMap(s => FIELDS.map(f => s + "_" + f))];
  let maximum = 0;
  for (const row of doc.scenarios.rows) {
    keys(row, ["id", "name", "frequency_method", "cost_dist_type", ...numeric], "Scenario");
    require((safeInteger(row.id, 1) || identifier(row.id)) && !ids.has(rowKey(row.id)), "Invalid or duplicate scenario ID");
    ids.add(rowKey(row.id)); if (typeof row.id === "number") maximum = Math.max(maximum, row.id);
    require(typeof row.name === "string", "Invalid scenario name");
    require([...DISTRIBUTIONS, "odds"].includes(row.frequency_method), "Unsupported frequency method");
    require(DISTRIBUTIONS.includes(row.cost_dist_type), "Unsupported cost distribution");
    require(numeric.every(field => finite(row[field])), "Invalid scenario parameter type");
  }
  require(safeInteger(doc.scenarios.next_id, 1) && doc.scenarios.next_id > maximum, "Invalid scenario next_id");
  require(object(doc.drafts), "Invalid drafts");
  const allowed = editableFields(doc);
  require(Object.entries(doc.drafts).every(([path, value]) => allowed.has(path) && typeof value === "string"), "Invalid draft field");
  return doc;
}
export function parseBackup(text) {
  require(new TextEncoder().encode(text).length <= 10 * 1024 * 1024, "Backup exceeds 10 MiB");
  const value = JSON.parse(text.replace(/^\uFEFF/, "")); let docs;
  if (object(value) && value.format === LIBRARY_FORMAT) {
    keys(value, ["format", "version", "analyses"], "Library");
    require(value.version === 1, "Unsupported library version");
    require(Array.isArray(value.analyses) && value.analyses.length, "Library contains no analyses");
    docs = value.analyses;
  } else docs = [value];
  docs.forEach(validateDocument);
  require(new Set(docs.map(doc => doc.id)).size === docs.length, "Duplicate analysis IDs"); return docs;
}
function sorted(value) {
  if (Array.isArray(value)) return value.map(sorted);
  if (object(value)) return Object.fromEntries(Object.keys(value).sort().map(key => [key, sorted(value[key])]));
  return value;
}
export function serializeBackup(docs, library = false) {
  require(docs.length && (library || docs.length === 1), "Choose analyses to download");
  docs.forEach(validateDocument);
  require(new Set(docs.map(doc => doc.id)).size === docs.length, "Duplicate analysis IDs");
  return JSON.stringify(sorted(library ? {format: LIBRARY_FORMAT, version: 1,
    analyses: [...docs].sort((a,b) => a.id.localeCompare(b.id))} : docs[0]), null, 2) + "\n";
}
export function commitField(doc, path) {
  if (!Object.hasOwn(doc.drafts, path)) return false;
  const target = editableFields(doc).get(path); if (!target) return false;
  const [parent, field, numeric] = target, raw = doc.drafts[path];
  if (numeric && (!/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(raw.trim()) || !finite(Number(raw)))) return false;
  const value = numeric ? Number(raw) : raw;
  if (path === "seed" && !safeInteger(value)) return false;
  parent[field] = value; delete doc.drafts[path]; return true;
}
"""
