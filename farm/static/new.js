const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function syncArch() {
  const [target, arch] = $("#target").value.split("|");
  $("#archline").textContent = `${target} · ${arch}`;
  $("#archline").dataset.arch = arch;
  $("#archline").dataset.target = target;
}
$("#target").addEventListener("change", syncArch);
syncArch();

async function loadExisting() {
  try {
    const r = await fetch("/api/state");
    const d = await r.json();
    $("#existing").innerHTML = d.platforms
      .map((p) => `<div class="ex"><div class="n">${esc(p.name)} · ${esc(p.arch)}</div><div class="p">${esc(p.sdk || "—")}</div></div>`)
      .join("");
  } catch (e) {
    $("#existing").textContent = e.message;
  }
}

$("#create").addEventListener("click", async () => {
  const brands = [];
  if ($("#b-irz").checked) brands.push("irzOS");
  if ($("#b-dnx").checked) brands.push("dnxOS");
  const body = {
    name: $("#name").value.trim(),
    board: $("#board").value.trim(),
    target: $("#archline").dataset.target,
    arch: $("#archline").dataset.arch,
    release: $("#release").value.trim(),
    sdk: $("#sdk").value.trim(),
    feeds: $("#feeds").value.trim(),
    extras: $("#extras").value.trim(),
    brands,
  };
  try {
    const r = await fetch("/api/platforms", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok || !d.ok) throw new Error(d.error || r.statusText);
    location.href = `/platform/${encodeURIComponent(d.name)}`;
  } catch (e) {
    $("#err").textContent = e.message;
  }
});

loadExisting();
