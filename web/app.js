async function workspaceFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = sessionStorage.getItem("versionbridge-access-token");
  if (token) headers.set("Authorization", "Bearer " + token);
  const response = await fetch(path, { ...options, headers });
  if (response.status === 401) {
    document.querySelector("#access").hidden = false;
    document.querySelector("#access-status").textContent = "A valid workspace token is required.";
  }
  return response;
}

const run = document.querySelector("#run");
const cancelRun = document.querySelector("#cancel-run");
const probe = document.querySelector("#probe");
const logs = document.querySelector("#logs");
const probeLog = document.querySelector("#probe-log");
const statusLine = document.querySelector("#status");
const state = document.querySelector("#state");
const download = document.querySelector("#download");
const testPanel = document.querySelector("#test-panel");
const patchPanel = document.querySelector("#patch-panel");
const steps = [...document.querySelectorAll(".steps li")];
const profile = document.querySelector("#profile");
const projectTitle = document.querySelector("#project-title");
const loadExample = document.querySelector("#load-example");
const scopedOption = document.querySelector("#scoped-option");
const pythonTarget = document.querySelector("#python-target");
const filename = document.querySelector("#filename");
const functionName = document.querySelector("#function");
const repository = document.querySelector("#repository");
const ref = document.querySelector("#ref");
const sandboxes = document.querySelector("#sandboxes");
const sandboxRows = new Map();
const patchDownload = document.querySelector("#download-patch");
const historyList = document.querySelector("#history-list");
const historyFilter = document.querySelector("#history-filter");
const jobKey = "versionbridge-active-job";
let queueEnabled = false;
let publicImport = false;
let activeJob;
const markdownDownload = document.querySelector("#download-markdown");
let report;
let runs = [];
let runEvents = [];

document.querySelector("#source").addEventListener("submit", event => {
  event.preventDefault();
  if (!run.disabled) execute(false);
});

workspaceFetch("/api/config").then(response => response.json()).then(config => {
  publicImport = config.public_import;
  updateScope();
  loadExample.hidden = !config.public_import;
  scopedOption.hidden = scopedOption.disabled = !config.scoped_repair;
  document.querySelector("#source-note").textContent = config.public_import
    ? `${config.mode} · pinned GitHub imports for Python profiles`
    : `${config.mode} · this deployment runs bundled projects`;
  queueEnabled = config.job_queue;
  document.querySelector("#access").hidden = !config.auth_required || Boolean(sessionStorage.getItem("versionbridge-access-token"));
  loadUsage();
  if (queueEnabled && sessionStorage.getItem(jobKey) && !run.disabled) {
    execute(sessionStorage.getItem("versionbridge-active-task") === "containment", sessionStorage.getItem(jobKey));
  }
}).catch(() => {
  document.querySelector("#source-note").textContent = "Repair settings are unavailable.";
});

document.querySelector("#access-form").addEventListener("submit", async event => {
  event.preventDefault();
  sessionStorage.setItem("versionbridge-access-token", document.querySelector("#access-token").value);
  const response = await workspaceFetch("/api/stats");
  if (response.ok) location.reload();
});

async function loadUsage() {
  try {
    const [statsResponse, budgetResponse] = await Promise.all([
      workspaceFetch("/api/stats"), workspaceFetch("/api/budget")
    ]);
    if (!statsResponse.ok || !budgetResponse.ok) throw new Error("Usage requires workspace access.");
    const stats = await statsResponse.json();
    document.querySelector("#stat-runs").textContent = stats.retained_runs;
    document.querySelector("#stat-verified").textContent = stats.verified;
    document.querySelector("#stat-unverified").textContent = stats.unverified;
    const budget = await budgetResponse.json();
    document.querySelector("#budget-note").textContent =
      `Inference allowance · $${budget.reserved_usd.toFixed(2)} reserved of $${budget.limit_usd.toFixed(2)} · ${budget.requests_today}/${budget.daily_request_limit} requests today. Hosting charges are separate.`;
  } catch (error) {
    document.querySelector("#budget-note").textContent = error.message;
  }
}

function showInventory(event) {
  document.querySelector("#inventory").textContent = JSON.stringify(event, null, 2);
  document.querySelector("#inventory-panel").hidden = false;
}

function updateScope() {
  const scoped = profile.value === "python";
  const bundled = ["go", "rust", "java", "cpp", "postgresql", "typescript", "javascript", "sqlite", "algorithm"].includes(profile.value);
  repository.disabled = ref.disabled = !publicImport || bundled;
  if (bundled) repository.value = ref.value = "";
  pythonTarget.hidden = filename.disabled = functionName.disabled = !scoped;
}

profile.addEventListener("change", updateScope);
loadExample.addEventListener("click", () => {
  profile.value = "pandas";
  updateScope();
  repository.value = "https://github.com/Hari-Aditya-003/versionbridge-ai";
  ref.value = "274b7ba6ec8fd8d418f686f37538517d4f87ca82";
});

function showSandbox(event) {
  let row = sandboxRows.get(event.name);
  if (!row) {
    row = document.createElement("div");
    row.className = "runtime-entry";
    if (!sandboxRows.size) sandboxes.textContent = "";
    sandboxes.append(row);
    sandboxRows.set(event.name, row);
  }
  if (event.location) row.dataset.context = `${event.location} / ${event.runtime} · ${event.limits}`;
  row.textContent = `${event.name.slice(-12)} · ${event.status} · ${row.dataset.context || ""}`;
  if (event.exit_code !== undefined) row.textContent += ` · exit ${event.exit_code}`;
}

function showTestOutcomes(event) {
  if (!event.baseline_tests || !event.verification_tests) return;
  const before = Object.entries(event.baseline_tests);
  const after = new Map(Object.entries(event.verification_tests));
  const lines = [];
  for (const [id, outcome] of before) {
    lines.push(`${outcome} → ${after.get(id) || "missing"} · ${id}`);
    after.delete(id);
  }
  for (const [id, outcome] of after) lines.push(`new → ${outcome} · ${id}`);
  document.querySelector("#test-outcomes").textContent = lines.join("\n");
  testPanel.hidden = false;
}

function showResult(event) {
  showTestOutcomes(event);
  markdownDownload.hidden = false;
  report = event;
  steps.forEach(step => step.className = "done");
  state.textContent = "VERIFIED";
  statusLine.textContent = `Verified · ${event.provider} · exit ${event.baseline_exit_code} → ${event.verification_exit_code}`;
  if (event.verification_tests) {
    const outcomes = Object.values(event.verification_tests);
    const passed = outcomes.filter(outcome => outcome === "passed").length;
    const skipped = outcomes.length - passed;
    statusLine.textContent += ` · ${passed} passed${skipped ? `, ${skipped} skipped` : ""}`;
  }
  patchPanel.querySelector("summary").textContent = "View verified patch";
  document.querySelector("#patch").textContent = event.diff;
  patchPanel.hidden = download.hidden = patchDownload.hidden = false;
}

function showRejected(event) {
  showTestOutcomes(event);
  markdownDownload.hidden = false;
  patchPanel.querySelector("summary").textContent = "Inspect rejected candidate";
  document.querySelector("#patch").textContent = event.diff;
  patchPanel.hidden = download.hidden = false;
  if (event.rejection_reason) appendLog(logs, `[Verification gate] ${event.rejection_reason}\n`);
}

function showHistory() {
  const selected = historyFilter.value;
  const visible = runs.filter(item => selected === "All" || item.status === selected);
  historyList.textContent = visible.length ? "" : "No matching repairs.";
  for (const item of visible) {
    const button = document.createElement("button");
    button.className = "history-row";
    for (const value of [item.project, new Date(item.created).toLocaleString(), item.status]) {
      const cell = document.createElement("span");
      cell.textContent = value;
      button.append(cell);
    }
    button.addEventListener("click", () => {
      if (run.disabled) return;
      resetRepair();
      runEvents = item.evidence;
      for (const event of item.evidence) {
        if (event.event === "diagnosis") appendLog(logs, `[Diagnosis · ${event.provider}]\n${event.text}\n`);
        if (event.event === "inventory") showInventory(event);
        if (event.event === "project") projectTitle.textContent = event.title;
        if (event.event === "sandbox") showSandbox(event);
        if (event.event === "rejected") showRejected(event);
        if (event.event === "log") appendLog(logs, `[${event.label}]\n${event.text}\n`);
        if (event.event === "contained") {
          state.textContent = "CONTAINED";
          statusLine.textContent = event.message;
          download.hidden = false;
        }
        if (event.event === "result") showResult(event);
        if (event.event === "error") {
          state.textContent = "UNVERIFIED";
          statusLine.textContent = event.message;
          download.hidden = false;
        }
      }
      location.hash = "workspace";
    });
    historyList.append(button);
  }
}

async function loadHistory() {
  try {
    const response = await workspaceFetch("/api/history");
    if (!response.ok) throw new Error("Could not load history.");
    runs = await response.json();
    showHistory();
    loadUsage();
  } catch {
    historyList.textContent = "Could not load run history.";
  }
}

historyFilter.addEventListener("change", showHistory);
loadHistory();

async function streamEvents(path, onEvent, settings = {}) {
  const response = await workspaceFetch(path, { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(settings) });
  if (!response.ok || !response.body) {
    throw new Error(response.status === 429 ? "A sandbox run is already in progress." : "Could not start the sandbox.");
  }
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let pending = "";
  let completed = false;
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      pending += value;
      const lines = pending.split("\n");
      pending = lines.pop();
      for (const line of lines) {
        const event = JSON.parse(line);
        if (event.event === "error") {
          onEvent(event);
          throw new Error(event.message);
        }
        completed ||= event.event === "result" || event.event === "contained";
        onEvent(event);
      }
    }
    if (!completed) throw new Error("The execution stream ended before verification completed.");
  } finally {
    await reader.cancel();
  }
}

function appendLog(target, text) {
  target.textContent += text;
  target.scrollTop = target.scrollHeight;
}

function resetRepair() {
  logs.textContent = "";
  report = undefined;
  runEvents = [];
  sandboxRows.clear();
  sandboxes.textContent = "Waiting for sandbox dispatch…";
  patchPanel.hidden = download.hidden = patchDownload.hidden = true;
  patchPanel.open = testPanel.open = false;
  testPanel.hidden = markdownDownload.hidden = true;
  document.querySelector("#inventory-panel").hidden = true;
  steps.forEach(step => step.className = "");
}

async function followJob(onEvent, settings, resumeId) {
  activeJob = resumeId;
  if (!activeJob) {
    const response = await workspaceFetch("/api/jobs", {
      method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify(settings)
    });
    if (!response.ok) throw new Error(response.status === 429 ? "The repair queue is full." : "Could not queue the repair.");
    ({ id: activeJob } = await response.json());
    sessionStorage.setItem(jobKey, activeJob);
    sessionStorage.setItem("versionbridge-active-task", settings.task);
  }
  cancelRun.hidden = false;
  let cursor = 0;
  for (;;) {
    const response = await workspaceFetch(`/api/jobs/${activeJob}?cursor=${cursor}`);
    if (response.status === 404) sessionStorage.removeItem(jobKey);
    if (!response.ok) throw new Error("Could not load the repair job.");
    const job = await response.json();
    cursor = job.cursor;
    for (const event of job.events) onEvent(event);
    cancelRun.disabled = job.state === "cancelling";
    if (job.state === "queued") statusLine.textContent = "Queued for a sandbox.";
    if (job.state === "cancelling") statusLine.textContent = "Cancelling after the current step.";
    if (["queued", "running", "cancelling"].includes(job.state)) {
      await new Promise(resolve => setTimeout(resolve, 750));
      continue;
    }
    sessionStorage.removeItem(jobKey);
    if (job.state === "verified" || job.state === "contained") return;
    const message = job.events.find(event => event.event === "error")?.message;
    const labels = { cancelled: "Repair cancelled.", interrupted: "Repair interrupted by a server restart." };
    const failure = new Error(message || labels[job.state] || "Verification did not complete.");
    failure.jobState = job.state;
    throw failure;
  }
}

cancelRun.addEventListener("click", async () => {
  if (!activeJob) return;
  cancelRun.disabled = true;
  try {
    const response = await workspaceFetch(`/api/jobs/${activeJob}`, { method: "POST" });
    if (!response.ok && response.status !== 409) throw new Error("Could not request cancellation.");
  } catch (error) {
    statusLine.textContent = error.message;
    cancelRun.disabled = false;
  }
});

async function execute(isProbe, resumeId) {
  run.disabled = probe.disabled = profile.disabled = loadExample.disabled = true;
  if (isProbe) {
    probeLog.textContent = "Starting containment probe…\n";
  } else {
    resetRepair();
    state.textContent = "RUNNING";
    statusLine.textContent = "Starting repair…";
    steps.forEach(step => step.className = "");
  }
  const target = isProbe ? probeLog : logs;
  try {
    const onEvent = event => {
      if (!isProbe) runEvents.push(event);
      if (event.event === "diagnosis") appendLog(target, `[Diagnosis · ${event.provider}]\n${event.text}\n`);
      if (event.event === "inventory") showInventory(event);
      if (event.event === "project") projectTitle.textContent = event.title;
      if (event.event === "rejected") showRejected(event);
      if (event.event === "sandbox") {
        if (isProbe) appendLog(target, `› Sandbox ${event.name.slice(-12)} · ${event.status} · ${event.location || `exit ${event.exit_code}`}\n`);
        else showSandbox(event);
      }
      if (event.event === "stage") {
        appendLog(target, `› ${event.message}\n`);
        if (!isProbe) {
          statusLine.textContent = event.message;
          steps.forEach((step, index) => step.className = index === event.step ? "active" : index < event.step ? "done" : "");
        }
      }
      if (event.event === "log") appendLog(target, `\n[${event.label}]\n${event.text}\n`);
      if (event.event === "contained") {
        appendLog(target, `✓ ${event.message}\n`);
        state.textContent = "CONTAINED";
        statusLine.textContent = event.message;
      }
      if (event.event === "result") showResult(event);
    };
    const settings = { repository: repository.value.trim(), ref: ref.value.trim(), profile: profile.value,
      filename: filename.value.trim(), function: functionName.value.trim(),
      attempts: Number(document.querySelector("#attempts").value) };
    if (queueEnabled) await followJob(onEvent, { ...settings, task: isProbe ? "containment" : "repair" }, resumeId);
    else await streamEvents(isProbe ? "/api/containment" : "/api/repair", onEvent, isProbe ? {} : settings);
  } catch (error) {
    appendLog(target, `\n${error.message}\n`);
    if (!isProbe) {
      state.textContent = "UNVERIFIED";
      if (error.jobState === "cancelled" || error.jobState === "interrupted") {
        state.textContent = error.jobState.toUpperCase();
      }
      download.hidden = !runEvents.length;
      statusLine.textContent = error.message;
      steps.find(step => step.classList.contains("active"))?.classList.remove("active");
    }
  } finally {
    activeJob = undefined;
    cancelRun.hidden = true;
    cancelRun.disabled = false;
    run.disabled = probe.disabled = profile.disabled = loadExample.disabled = false;
    loadHistory();
  }
}

run.addEventListener("click", () => execute(false));
probe.addEventListener("click", () => execute(true));
function saveFile(content, mimeType, filename) {
  const url = URL.createObjectURL(new Blob([content], { type: mimeType }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

download.addEventListener("click", () => {
  saveFile(JSON.stringify({ result: report, events: runEvents }, null, 2), "application/json",
    `versionbridge-${report?.id || "unverified"}.json`);
});

patchDownload.addEventListener("click", () => {
  if (report) saveFile(report.diff, "text/plain", `versionbridge-${report.id}.patch`);
});

markdownDownload.addEventListener("click", async () => {
  const evidence = [...runEvents].reverse().find(event => ["result", "rejected"].includes(event.event));
  if (!evidence) return;
  try {
    const response = await workspaceFetch(`/api/runs/${evidence.id}/report.md`);
    if (!response.ok) throw new Error("The report could not be downloaded.");
    saveFile(await response.text(), "text/markdown", `versionbridge-${evidence.id}.md`);
  } catch (error) {
    statusLine.textContent = error.message;
  }
});
