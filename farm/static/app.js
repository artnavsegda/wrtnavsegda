const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const mmss = (n) => { n = Math.max(0, n|0); const m = Math.floor(n/60); return m + ":" + String(n%60).padStart(2,"0"); };
const dt = (s) => (s ? new Date(s).toLocaleString("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—");

let state = null;
let flavor = localStorage.getItem("farm.flavor") || "irz";
let cfgKind = "dist";
let logTimer = null;
let pollTimer = null;
const selected = new Set();

async function api(path, opts) {
  const r = await fetch(path, opts);
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || r.statusText);
  return data;
}

async function loadState() {
  state = await api("/api/state");
  if (!state.flavors.some((f) => f.name === flavor)) flavor = state.flavors[0]?.name || "irz";
  render();
  const running = state.builds.some((b) => b.status === "running");
  clearTimeout(pollTimer);
  pollTimer = setTimeout(loadState, running ? 3000 : 15000);
}

function render() {
  const farm = state.farm;
  $("#repostatus").textContent = `${farm.branch} · ${farm.head.slice(0, 9)} · ${farm.dirty ? "есть локальные изменения" : "чисто"} · ${farm.repo}`;
  $("#pulled").textContent = state.pull
    ? `апстрим проверен ${dt(state.pull.ts)} · позади ${state.pull.behind}`
    : "апстрим ещё не проверялся";

  const cur = state.flavors.find((f) => f.name === flavor) || state.flavors[0];
  $("#flavors").innerHTML = state.flavors
    .map((f) => `<button data-flavor="${esc(f.name)}" class="${f.name === flavor ? "on" : ""}">${esc(f.brand)} · /opkg/${esc(f.feed)}</button>`)
    .join("");
  $("#flavors").querySelectorAll("button").forEach((b) =>
    b.addEventListener("click", () => {
      flavor = b.dataset.flavor;
      localStorage.setItem("farm.flavor", flavor);
      render();
      loadPackages();
      loadConfig();
    })
  );

  $("#feedstat").textContent = cur.last_publish
    ? `опубликован ${dt(cur.last_publish.ts)} · ${cur.last_publish.packages} пакетов`
    : "фид ещё не публиковался";

  renderPlatforms();
  renderUpstream();
  renderBuilds();
  renderControls();
  renderPublish();
  loadPackages();
  loadConfig();
}

function renderPlatforms() {
  const head = `<div class="row head plat"><span>Платформа</span><span>Board</span><span>Arch / target</span><span>SDK</span><span>Статус</span></div>`;
  const rows = state.platforms
    .map((p) => {
      const sdk = p.sdk_ok ? `<span class="st ok">ok</span>` : `<span class="st ${p.status === "active" ? "err" : "mut"}">${p.status === "active" ? "нет" : "planned"}</span>`;
      const st = p.status === "active" ? `<span class="st mut">active</span>` : `<span class="st mut">planned</span>`;
      return `<div class="row plat"><span class="name">${esc(p.name)}</span><span class="mono">${esc(p.board)}</span>
        <span class="mono">${esc(p.arch)} · ${esc(p.target)}</span><span>${sdk}</span><span>${st}</span></div>`;
    })
    .join("");
  $("#platforms").innerHTML = head + rows;
  const active = state.platforms.filter((p) => p.status === "active").length;
  $("#platsum").textContent = `${active} активных · пакеты all, сборка на flavor`;
}

function renderUpstream() {
  const up = state.upstream;
  $("#uptop").textContent = up.base
    ? `HEAD ${up.head.slice(0, 9)} · сборка из ${up.base.slice(0, 9)} · ${up.commits.length} коммитов`
    : `HEAD ${up.head.slice(0, 9)} · опубликованной сборки ещё нет`;
  $("#commits").innerHTML = up.commits.length
    ? up.commits
        .map((c) => `<div class="commit${c.published ? " cur" : ""}"><span class="h">${esc(c.hash)}${c.published ? ' <span class="tagpub">в фиде</span>' : ""}${c.head ? ' <span class="taghead">HEAD</span>' : ""}</span><span>${esc(c.date)} · ${esc(c.subject)}</span></div>`)
        .join("")
    : `<div class="empty">Нет новых коммитов после опубликованной сборки.</div>`;
}

function renderBuilds() {
  const head = `<div class="row head bld"><span>#</span><span>Flavor</span><span>Платформа</span><span>Начата</span><span>Статус</span><span></span></div>`;
  const rows = state.builds
    .map((b) => {
      let st;
      if (b.status === "ok") st = `<span class="st ok">ok</span>`;
      else if (b.status === "running") {
        const l = b.live || {};
        st = `<span class="st warn">идёт ${l.current || 0}/${l.total || 0} · ${mmss(l.elapsed || 0)} · +${l.idle || 0}с</span>`;
      } else if (b.status === "dry-run") st = `<span class="st mut">dry-run</span>`;
      else st = `<span class="st err">${esc(b.status)}</span>`;
      const pub = b.published ? ` · опубликовано` : "";
      return `<div class="row bld"><span class="mono">${b.id}</span><span>${esc(b.flavor)}</span><span class="mono">${esc(b.platform)}</span>
        <span class="mono">${dt(b.started)}</span><span>${st}${pub}</span>
        <span><button data-log="${b.id}">Лог</button></span></div>`;
    })
    .join("");
  $("#builds").innerHTML = head + (rows || `<div class="empty">Сборок ещё нет.</div>`);
  $("#builds").querySelectorAll("[data-log]").forEach((b) => b.addEventListener("click", () => openLog(b.dataset.log)));
}

function renderControls() {
  const running = state.builds.some((b) => b.status === "running");
  $("#stop").disabled = !running;
  $("#build").disabled = running;
  $("#buildpublish").disabled = running;
  $("#stop").title = running ? "" : "нет идущей сборки";
}

function updateSelectionButton() {
  const running = state.builds.some((b) => b.status === "running");
  const btn = $("#rebuild");
  if (!btn) return;
  btn.textContent = selected.size ? `Собрать выбранные · ${selected.size}` : "Собрать выбранные";
  btn.disabled = selected.size === 0 || running;
  btn.title = running ? "идёт сборка — дождитесь её окончания" : "";
}

function renderPublish() {
  const b = state.builds[0];
  $("#publish").disabled = !b || b.status !== "ok" || b.published;
  $("#publish").onclick = b ? () => publishBuild(b.id) : null;
}

async function loadPackages() {
  try {
    const data = await api(`/api/packages?flavor=${encodeURIComponent(flavor)}`);
    $("#feedname").textContent = `· /opkg/${data.feed}`;
    const head = `<div class="row head pkg"><span>Пакет</span><span>Версия в фиде</span><span>Arch</span><span>Статус</span><span>Сборка</span></div>`;
    const rows = data.packages
      .map((p) => {
        const st = p.status === "ок" ? `<span class="st ok">ок</span>` : p.status === "новый" ? `<span class="st warn">новый</span>` : `<span class="st mut">${esc(p.status)}</span>`;
        let bs = `<span class="st mut">—</span>`;
        if (p.build_state === "built") bs = `<span class="st ok">собран</span>`;
        else if (p.build_state === "building") bs = `<span class="st info"><span class="spin"></span>собирается</span>`;
        else if (p.build_state === "pending") bs = `<span class="st mut">в очереди</span>`;
        const sel = selected.has(p.name) ? " sel" : "";
        const clickable = p.dir ? " clickable" : "";
        return `<div class="row pkg${sel}${clickable}" data-name="${esc(p.name)}" data-dir="${esc(p.dir || "")}"><span class="name">${esc(p.name)}</span><span class="mono">${esc(p.version || "—")}</span>
          <span class="mono">${esc(p.arch)}</span><span>${st}</span><span>${bs}</span></div>`;
      })
      .join("");
    $("#packages").innerHTML = head + (rows || `<div class="empty">Фид пуст.</div>`);
    $("#packages").querySelectorAll("[data-name]").forEach((row) =>
      row.addEventListener("click", () => {
        const name = row.dataset.name;
        if (!row.dataset.dir) { toast(`${name}: arch-extra, собирается не из фида`); return; }
        if (selected.has(name)) selected.delete(name); else selected.add(name);
        row.classList.toggle("sel");
        updateSelectionButton();
      })
    );
    updateSelectionButton();
  } catch (e) {
    $("#packages").innerHTML = `<div class="empty">${esc(e.message)}</div>`;
  }
}

async function loadConfig() {
  const el = $("#cfg");
  el.textContent = "…";
  try {
    const data = await api(`/api/config?flavor=${encodeURIComponent(flavor)}&variant=${cfgKind}`);
    if (data.error) throw new Error(data.error);
    el.textContent = data.text;
    $("#cfgmeta").textContent = `buildbot ${data.buildbot.path} · ${data.buildbot.version}`;
    $("#download").href = `/api/feed?flavor=${encodeURIComponent(flavor)}&kind=${cfgKind}`;
  } catch (e) {
    el.textContent = e.message;
    $("#cfgmeta").textContent = "";
  }
}

function openLog(id, open = true) {
  const dlg = $("#logdlg");
  $("#logtitle").textContent = `Лог · сборка #${id}`;
  if (open) dlg.showModal();
  const tick = async () => {
    try {
      const data = await api(`/api/builds/${id}/log`);
      const el = $("#log");
      const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 20;
      el.textContent = data.lines.join("\n") || "лога нет";
      if (atBottom) el.scrollTop = el.scrollHeight;
    } catch (e) {
      $("#log").textContent = e.message;
    }
  };
  clearInterval(logTimer);
  tick();
  logTimer = setInterval(tick, 2000);
}

function toast(text, error = false) {
  const el = $("#pulled");
  el.textContent = text;
  el.style.color = error ? "var(--red)" : "";
  setTimeout(() => { el.style.color = ""; }, 6000);
}

async function pull() {
  const btn = $("#pull");
  btn.disabled = true;
  toast("git pull…");
  try {
    const r = await api("/api/pull", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    toast(r.output.split("\n")[0] || "готово", !r.ok);
    await loadState();
  } catch (e) {
    toast(e.message, true);
  } finally {
    btn.disabled = false;
  }
}

async function startBuild(publish, packages = []) {
  const body = { flavor, publish, packages };
  selected.clear();
  toast(publish ? "сборка и публикация запущены…" : "сборка запущена…");
  try {
    await api("/api/build", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    setTimeout(loadState, 1500);
  } catch (e) {
    toast(e.message, true);
  }
}

async function stopBuild() {
  if (!confirm("Остановить идущую сборку?")) return;
  try {
    const r = await api("/api/stop", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ flavor }) });
    toast(r.ok ? `сборка #${r.build} остановлена` : `не остановилась: ${r.error}`, !r.ok);
    await loadState();
  } catch (e) {
    toast(e.message, true);
  }
}

async function publishBuild(id) {
  toast(`публикация сборки #${id}…`);
  try {
    const r = await api("/api/publish", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ build: id }) });
    toast(r.ok ? `опубликовано: ${r.output.split("\n").slice(-2)[0]}` : `ошибка: ${r.output}`, !r.ok);
    await loadState();
  } catch (e) {
    toast(e.message, true);
  }
}

$("#pull").addEventListener("click", pull);
$("#build").addEventListener("click", () => startBuild(false));
$("#buildpublish").addEventListener("click", () => startBuild(true));
$("#rebuild").addEventListener("click", () => startBuild(false, [...selected]));
$("#stop").addEventListener("click", stopBuild);
$("#logclose").addEventListener("click", () => { clearInterval(logTimer); $("#logdlg").close(); });
$("#logdlg").addEventListener("close", () => clearInterval(logTimer));

$("#cfgtabs").querySelectorAll("button").forEach((b) =>
  b.addEventListener("click", () => {
    cfgKind = b.dataset.kind;
    $("#cfgtabs").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
    loadConfig();
  })
);

$("#copy").addEventListener("click", async () => {
  const text = $("#cfg").textContent;
  try {
    await navigator.clipboard.writeText(text);
    toast("конфиг скопирован");
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
    toast("конфиг скопирован");
  }
});

loadState().catch((e) => { $("#repostatus").textContent = `ошибка: ${e.message}`; });
