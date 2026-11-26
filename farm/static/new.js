const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
let mode = "archive";
let timer = null;

function parts() {
  const [target, arch] = $("#target").value.split("|");
  return { target, arch };
}

function render() {
  const { target, arch } = parts();
  $("#archline").textContent = `${target} · ${arch}`;
  const rel = $("#release").value.trim() || "24.10.2";
  const name = target.replace("/", "-");
  $("#urlpreview").textContent =
    `https://downloads.openwrt.org/releases/${rel}/targets/${target}/openwrt-sdk-${rel}-${name}_…tar.zst`;
  $("#src-archive").style.display = mode === "archive" ? "" : "none";
  $("#src-git").style.display = mode === "git" ? "" : "none";
  $("#longbuild").style.display = mode === "git" ? "" : "none";
  $("#create").textContent = mode === "git" ? "Собрать SDK" : "Скачать и добавить";
  $("#plan").innerHTML = mode === "git"
    ? `<div><span class="t">1</span><span>Клонировать ветку</span><span class="d">~4 мин</span></div>
       <div><span class="t">2</span><span>toolchain</span><span class="d">~1,5 ч</span></div>
       <div><span class="t">3</span><span>Собрать SDK</span><span class="d">~3 ч</span></div>
       <div><span class="t">4</span><span>Распаковать и добавить платформу</span><span class="d">сразу</span></div>`
    : `<div><span class="t">1</span><span>Скачать SDK</span><span class="d">~1 мин</span></div>
       <div><span class="t">2</span><span>Проверить sha256</span><span class="d">сек</span></div>
       <div><span class="t">3</span><span>Распаковать</span><span class="d">~1 мин</span></div>
       <div><span class="t">4</span><span>Добавить платформу</span><span class="d">сразу</span></div>`;
  $("#plannote").textContent = mode === "git"
    ? "Если в SDK не окажется scripts/feeds или сборка упадёт — платформа не создаётся, причина в логе."
    : "Если target или arch не совпадут — добавление остановится, причина в логе.";
}

$("#srctabs").querySelectorAll("button").forEach((b) =>
  b.addEventListener("click", () => {
    mode = b.dataset.src;
    $("#srctabs").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
    render();
  })
);
$("#target").addEventListener("change", render);
$("#release").addEventListener("input", render);

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
  const { target, arch } = parts();
  const body = {
    name: $("#name").value.trim(),
    board: $("#board").value.trim(),
    target,
    arch,
    release: $("#release").value.trim(),
    source: mode,
    repo: $("#repo").value.trim(),
    branch: $("#branch").value.trim(),
    brands,
  };
  try {
    const r = await fetch("/api/platforms", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok || !d.ok) throw new Error(d.error || r.statusText);
    $("#form").style.display = "none";
    $("#progress").style.display = "";
    $("#ptitle").textContent = mode === "git"
      ? `Собираю SDK для ${d.name}…`
      : `Скачиваю SDK для ${d.name}…`;
    poll(d.name);
  } catch (e) {
    $("#err").textContent = e.message;
  }
});

function poll(name) {
  clearInterval(timer);
  const tick = async () => {
    try {
      const r = await fetch(`/api/platform/${encodeURIComponent(name)}/oplog?op=provision`);
      const d = await r.json();
      const el = $("#plog");
      const bottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 20;
      el.textContent = (d.lines || []).join("\n") || "…";
      if (bottom) el.scrollTop = el.scrollHeight;
      const done = (d.lines || []).find((l) => l.startsWith("EXIT:"));
      if (done) {
        clearInterval(timer);
        if (done === "EXIT:0") {
          $("#pnote").textContent = "Готово, открываю платформу…";
          location.href = `/platform/${encodeURIComponent(name)}`;
        } else {
          $("#ptitle").textContent = "Не получилось";
          $("#pnote").textContent = "Причина — в логе выше. Платформа не создана.";
        }
      }
    } catch (e) {
      $("#plog").textContent = e.message;
    }
  };
  tick();
  timer = setInterval(tick, 2000);
}

render();
loadExisting();
