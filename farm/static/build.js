const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const dt = (s) => (s ? new Date(s).toLocaleString("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—");
const id = location.pathname.split("/").filter(Boolean).pop();
let timer = null;

async function api(p) {
  const r = await fetch(p);
  const d = await r.json();
  if (!r.ok) throw new Error(d.error || r.statusText);
  return d;
}

function row(k, v) {
  return `<div class="platrow"><span class="k">${esc(k)}</span><span class="v">${esc(v || "—")}</span></div>`;
}

async function load() {
  const m = await api(`/api/builds/${id}`);
  if (!m.exists) {
    $("#btitle").textContent = `Сборка #${id}`;
    $("#bsub").textContent = "манифеста нет (сборка не дошла до артефактов)";
    $("#bmeta").textContent = "";
    return;
  }
  $("#btitle").textContent = `Сборка #${m.id} · ${m.flavor}`;
  $("#bsub").textContent = `${m.platform} · ${m.release} · начата ${dt(m.started)} · ${m.status}`;
  $("#bstate").textContent = m.status;
  $("#bstate").className = "st " + (m.status === "ok" ? "ok" : m.status === "running" ? "warn" : "err");
  $("#bmeta").innerHTML = [
    row("flavor", `${m.flavor} · ${m.brand}`),
    row("фид", m.feed),
    row("платформа", `${m.platform} · ${m.sdk && m.sdk.arch}`),
    row("release", m.release),
    row("коммит упаковки", m.refs && m.refs.repo_head),
    row("donyx split", m.refs && m.refs.halo_pinned),
    row("buildbot", m.buildbot && m.buildbot.path),
    row("SDK", m.sdk && m.sdk.path),
    row("проверки", (m.checks || []).map((c) => `${c.name}: ${c.ok ? "ok" : "!"}`).join(" · ")),
  ].join("");
  const pkgs = m.packages || [];
  $("#bcount").textContent = `${pkgs.length} пакетов`;
  $("#bpackages").innerHTML =
    `<div class="row head brow"><span>Пакет</span><span>Версия</span><span>Arch</span><span>Размер</span><span>Источник</span></div>` +
    pkgs.map((p) => `<div class="row brow"><span class="pkg">${esc(p.name)}</span><span class="mono">${esc(p.version)}</span>
      <span class="mono">${esc(p.arch)}</span><span class="mono">${Math.round((p.size || 0) / 1024)} КБ</span>
      <span class="mono">${esc(p.source_branch)} ${esc(p.source_commit)}</span></div>`).join("");
  const log = await api(`/api/builds/${id}/log`);
  $("#blog").textContent = log.lines.join("\n") || "лога нет";
  $("#blogmeta").textContent = m.status === "running" ? "обновляется" : "завершена";
  clearInterval(timer);
  if (m.status === "running") timer = setInterval(refreshLog, 2000);
}

async function refreshLog() {
  try {
    const r = await api(`/api/builds/${id}/log`);
    const el = $("#blog");
    const bottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 20;
    el.textContent = r.lines.join("\n");
    if (bottom) el.scrollTop = el.scrollHeight;
  } catch (e) {}
}

load().catch((e) => { $("#btitle").textContent = `ошибка: ${e.message}`; });
