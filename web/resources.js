/* Read-only host telemetry. Browser/device and remote serverless GPU are distinct. */
(() => {
  const panel = document.querySelector("#resource-panel");
  if (!panel) return;
  if (matchMedia("(max-width: 700px)").matches) panel.open = false;
  const put = (id, text) => { document.getElementById(`resource-${id}`).textContent = text; };
  const valid = value => typeof value === "number" && Number.isFinite(value);
  const pct = value => valid(value) ? `${value.toFixed(1)}%` : "Unavailable";
  const gib = value => valid(value) ? (value / 1073741824).toFixed(1) : "—";
  let timer;
  async function refresh() {
    if (document.hidden) return;
    try {
      const response = await workspaceFetch("/api/telemetry", { signal: AbortSignal.timeout(5000) });
      if (!response.ok) throw new Error("Resources unavailable");
      const data = await response.json();
      if (Math.abs(Date.now()/1000 - data.sampled_at) > 20) throw new Error("Sensor readings are stale");
      const host = data.host, cpu = host.cpu || {}, ram = host.memory || {}, gpu = data.gpu;
      put("live", "Live · 3s");
      put("host", host.label || "Application host");
      put("ram", `${pct(ram.percent)} · ${gib(ram.used_bytes)}/${gib(ram.total_bytes)} GiB`);
      put("cpu", pct(cpu.percent));
      put("speed", valid(cpu.speed_mhz) ? `${(cpu.speed_mhz/1000).toFixed(2)} GHz` : "Unavailable");
      const temperature = gpu.available ? gpu.temperature_c : cpu.temperature_c;
      put("temp", valid(temperature) ? `${temperature.toFixed(0)}°C · ${gpu.available ? "GPU" : "host"}` : "Sensor unavailable");
      put("gpu", gpu.available ? pct(gpu.utilization_percent) : "Not exposed");
      put("vram", gpu.available ? `${pct(gpu.memory_percent)} · ${(gpu.memory_used_mb/1024).toFixed(1)}/${(gpu.memory_total_mb/1024).toFixed(1)} GiB` : "Not exposed");
      put("inference", `Inference · ${data.inference.label}`);
      put("note", gpu.available ? `${gpu.source}. Whole-host usage; per-job attribution is unavailable.` : data.inference.note);
      put("updated", `Updated ${new Date(data.sampled_at*1000).toLocaleTimeString()} · whole host`);
      panel.classList.remove("sensor-error");
    } catch (error) {
      put("live", "Offline");
      for (const id of ["ram", "cpu", "speed", "temp", "gpu", "vram"]) put(id, "Unavailable");
      put("updated", "No current reading");
      put("note", error.name === "TimeoutError" ? "Resource request timed out. Retrying…" : "Waiting for current sensor readings…");
      panel.classList.add("sensor-error");
    }
  }
  function start() { clearInterval(timer); refresh(); timer = setInterval(refresh, 3000); }
  document.addEventListener("visibilitychange", () => { if (document.hidden) clearInterval(timer); else start(); });
  start();
})();
