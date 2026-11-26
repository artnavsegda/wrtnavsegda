const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const name = decodeURIComponent(location.pathname.split("/").filter(Boolean).pop() || "");

let data = null;
let opTimer = null;

async function api(path, opts) {
  const r = await fetch(path, opts);
  const body = await r.json();
  if (!r.ok) throw new Error(body.error || r.statusText);
  return body;
}

function toast(text) {
  const el = $("#psaved");
  el.textContent = text;
  setTimeout(() => { if (el.textContent === text) el.textContent = ""; }, 6000);
}

async function load() {
  data = await api(`/api/platform/${encodeURIComponent(name)}`);
  $("#pname").textContent = `Платформа · ${data.name}`;
  $("#psub").textContent = `${data.board} · ${data.arch} · ${data.target} · OpenWrt ${data.release}`;
  const sdk = data.sdk_ok ? `<span class="st ok">SDK на месте</span>` : `<span class="st err">SDK нет</span>`;
  const git = data.sdk_git ? ` · git` : ` · не git`;
  $("#pstate").innerHTML = `${sdk}<span class="muted">${git}</span>`;
  $("#sdk").value = data.sdk;
  $("#feeds").value = data.feeds;
  $("#extras").value = (data.extras || []).join(", ");
  $("#image_tree").value = data.image_tree;
  $("#dotconfig").value = data.config || "";
  $("#cfgpath").textContent = data.config_path ? `${data.config_path} · ${(data.config || "").split("\n").length} строк` : "нет .config";
  renderOps();
}

function renderOps() {
  const labels = { feeds_update: "feeds update", feeds_install: "feeds install", feeds_list: "feeds list", sdk_pull: "git pull SDK", image: "собрать образ" };
  $("#ops").innerHTML = data.ops
    .map((op) => `<div class="oprow"><button data-op="${op.id}" ${op.ok ? "" : "disabled"}>${esc(labels[op.id] || op.title)}</button>
      <span class="muted">${esc(op.title)}</span></div>`)
    .join("");
  $("#ops").querySelectorAll("[data-op]").forEach((b) => b.addEventListener("click", () => runOp(b.dataset.op)));
}

async function runOp(op) {
  $("#oplog").textContent = "…";
  $("#opstate").textContent = op;
  try {
    const r = await api(`/api/platform/${encodeURIComponent(name)}/op`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ op }),
    });
    if (r.error) { $("#oplog").textContent = r.error; $("#opstate").textContent = "ошибка"; return; }
    if (r.output !== undefined) {
      $("#oplog").textContent = r.output || "(пусто)";
      $("#opstate").textContent = r.ok ? "готово" : "ошибка";
      return;
    }
    poll(op);
  } catch (e) {
    $("#oplog").textContent = e.message;
    $("#opstate").textContent = "ошибка";
  }
}

function poll(op) {
  clearInterval(opTimer);
  const tick = async () => {
    try {
      const r = await api(`/api/platform/${encodeURIComponent(name)}/oplog?op=${encodeURIComponent(op)}`);
      const el = $("#oplog");
      const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 20;
      el.textContent = r.lines.join("\n") || "…";
      if (atBottom) el.scrollTop = el.scrollHeight;
      const done = r.lines.some((l) => l.startsWith("EXIT:"));
      $("#opstate").textContent = done ? "готово" : "идёт";
      if (done) clearInterval(opTimer);
    } catch (e) {
      $("#oplog").textContent = e.message;
      clearInterval(opTimer);
    }
  };
  tick();
  opTimer = setInterval(tick, 1500);
}

$("#savepaths").addEventListener("click", async () => {
  try {
    const r = await api(`/api/platform/${encodeURIComponent(name)}/paths`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sdk: $("#sdk").value, feeds: $("#feeds").value,
        extras: $("#extras").value, image_tree: $("#image_tree").value,
      }),
    });
    toast(`сохранено: ${r.saved}`);
    await load();
  } catch (e) { toast(e.message); }
});

$("#saveconfig").addEventListener("click", async () => {
  try {
    const r = await api(`/api/platform/${encodeURIComponent(name)}/config`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: $("#dotconfig").value }),
    });
    toast(r.ok ? `записан ${r.path}` : r.error);
  } catch (e) { toast(e.message); }
});

load().catch((e) => { $("#pname").textContent = `ошибка: ${e.message}`; });
