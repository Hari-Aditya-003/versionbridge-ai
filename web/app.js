const run = document.querySelector("#run");
const probe = document.querySelector("#probe");
const logs = document.querySelector("#logs");
const probeLog = document.querySelector("#probe-log");
const statusLine = document.querySelector("#status");
const state = document.querySelector("#state");
const download = document.querySelector("#download");
const patchPanel = document.querySelector("#patch-panel");
const steps = [...document.querySelectorAll(".steps li")];
const profile = document.querySelector("#profile");
const projectTitle = document.querySelector("#project-title");
const repository = document.querySelector("#repository");
const ref = document.querySelector("#ref");
const sandboxes = document.querySelector("#sandboxes");
const sandboxRows = new Map();
const patchDownload = document.querySelector("#download-patch");
const historyList = document.querySelector("#history-list");
const historyFilter = document.querySelector("#history-filter");
let report;
let runs = [];
let runEvents = [];

document.querySelector("#source").addEventListener("submit", event => {
  event.preventDefault();
  if (!run.disabled) execute(false);
});

fetch("/api/config").then(response => response.json()).then(config => {
  repository.disabled = ref.disabled = !config.public_import;
  document.querySelector("#source-note").textContent = config.public_import
    ? `${config.mode} · Python / pytest profiles`
    : `${config.mode} · this deployment runs the bundled project`;
}).catch(() => {
  document.querySelector("#source-note").textContent = "Repair settings are unavailable.";
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

function showResult(event) {
  report = event;
  steps.forEach(step => step.className = "done");
  state.textContent = "VERIFIED";
  statusLine.textContent = `Verified · ${event.provider} · exit ${event.baseline_exit_code} → ${event.verification_exit_code}`;
  patchPanel.querySelector("summary").textContent = "View verified patch";
  document.querySelector("#patch").textContent = event.diff;
  patchPanel.hidden = download.hidden = patchDownload.hidden = false;
}

function showRejected(event) {
  patchPanel.querySelector("summary").textContent = "Inspect rejected candidate";
  document.querySelector("#patch").textContent = event.diff;
  patchPanel.hidden = download.hidden = false;
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
        if (event.event === "project") projectTitle.textContent = event.title;
        if (event.event === "sandbox") showSandbox(event);
        if (event.event === "rejected") showRejected(event);
        if (event.event === "log") appendLog(logs, `[${event.label}]\n${event.text}\n`);
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
    const response = await fetch("/api/history");
    if (!response.ok) throw new Error("Could not load history.");
    runs = await response.json();
    showHistory();
  } catch {
    historyList.textContent = "Could not load run history.";
  }
}

historyFilter.addEventListener("change", showHistory);
loadHistory();

async function streamEvents(path, onEvent, settings = {}) {
  const response = await fetch(path, { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(settings) });
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
  patchPanel.open = false;
  steps.forEach(step => step.className = "");
}

async function execute(isProbe) {
  run.disabled = probe.disabled = profile.disabled = true;
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
    await streamEvents(isProbe ? "/api/containment" : "/api/repair", event => {
      if (!isProbe) runEvents.push(event);
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
      if (event.event === "contained") appendLog(target, `✓ ${event.message}\n`);
      if (event.event === "result") showResult(event);
    }, isProbe ? {} : { repository: repository.value.trim(), ref: ref.value.trim(), profile: profile.value });
  } catch (error) {
    appendLog(target, `\n${error.message}\n`);
    if (!isProbe) {
      state.textContent = "UNVERIFIED";
      download.hidden = !runEvents.length;
      statusLine.textContent = error.message;
      steps.find(step => step.classList.contains("active"))?.classList.remove("active");
    }
  } finally {
    run.disabled = probe.disabled = profile.disabled = false;
    if (!isProbe) loadHistory();
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

let queued = false;
window.addEventListener("scroll", () => {
  if (queued) return;
  queued = true;
  requestAnimationFrame(() => {
    document.documentElement.style.setProperty("--shift", `${Math.min(window.scrollY, 700) * 0.21}px`);
    queued = false;
  });
}, { passive: true });

const reveals = new IntersectionObserver(entries => {
  for (const entry of entries) {
    if (entry.isIntersecting) {
      entry.target.classList.add("arriving");
      reveals.unobserve(entry.target);
    }
  }
}, { threshold: 0.15 });

document.querySelectorAll("main .section").forEach(section => reveals.observe(section));
