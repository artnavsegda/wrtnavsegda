const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const short = (p) => String(p || "").replace(/^\/home\/[^/]+/, "~").replace(/^\/Users\/[^/]+/, "~");

let mode = "git";
let timer = null;
let started = "";

const PLANS = {
  git: [
    { text: "Клонировать ветку", time: "~4 мин", mark: "git clone" },
    { text: "make defconfig", time: "~2 мин", mark: "make defconfig" },
    { text: "toolchain и сборка SDK", time: "~4–8 ч", mark: "make -j" },
    { text: "Распаковать и добавить платформу", time: "сек", mark: "SDK собран" },
  ],
  archive: [
    { text: "Скачать SDK", time: "~1 мин", mark: "скачиваю" },
    { text: "Проверить sha256", time: "сек", mark: "sha256" },
    { text: "Распаковать", time: "~1 мин", mark: "распаков" },
    { text: "Добавить платформу", time: "сразу", mark: "добавлена" },
  ],
};

function parts() {
  const [target, arch] = $("#target").value.split("|");
  return { target, arch };
}

function render() {
  const { target, arch } = parts();
  const rel = $("#release").value.trim() || "24.10.2";
  $("#archline").textContent = `ramips/mt7620 · ramips/mt7621 · ipq40xx/generic · mediatek/filogic · x86/64 — выбран ${target} · ${arch}`;
  $("#urlpreview").textContent =
    `https://downloads.openwrt.org/releases/${rel}/targets/${target}/openwrt-sdk-${rel}-${target.replace("/", "-")}_…tar.zst`;
  $("#src-archive").style.display = mode === "archive" ? "" : "none";
  $("#src-git").style.display = mode === "git" ? "" : "none";
  $("#create").textContent = mode === "git" ? "Собрать SDK" : "Скачать и добавить";
  $("#gitrel").textContent = `→ OpenWrt ${rel}`;

  $("#plan").innerHTML = PLANS[mode]
    .map((s, i) => `<div><span class="t">${i + 1}</span><span>${esc(s.text)}</span><span class="d">${esc(s.time)}</span></div>`)
    .join("");
  $("#plannote").textContent =
    mode === "git"
      ? "Если не сойдётся target/arch или сборка упадёт — платформа не создаётся, причина в логе."
      : "Если target или arch не совпадут — добавление остановится, причина в логе.";
  $("#srccost").innerHTML =
    mode === "git"
      ? "<b>≈4–8 часов</b> для исходников из Git. Идёт на ферме в фоне: страницу можно закрыть. Альтернатива — готовый архив SDK: 2–3 минуты."
      : "<b>2–3 минуты</b>: архив скачается, sha256 проверится, SDK распакуется. Сборка из исходников — во вкладке «Исходники из Git».";
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
      .map((p) => `<div class="ex"><div class="n">${esc(p.name)} · ${esc(p.arch)}</div><div class="p">${esc(short(p.sdk) || "—")}</div></div>`)
      .join("");
  } catch (e) {
    $("#existing").textContent = e.message;
  }
}

function stepIcon(state) {
  if (state === "done") return "✓";
  if (state === "act") return "▸";
  return "·";
}

function renderSteps(log, finished) {
  const steps = PLANS[mode];
  const found = steps.map((s) => log.some((l) => l.includes(s.mark)));
  const firstMissing = found.indexOf(false);
  const done = finished === 0;
  $("#provsteps").innerHTML = steps
    .map((s, i) => {
      let st = "wait";
      if (done || (firstMissing === -1 && i < steps.length)) st = "done";
      else if (found[i]) st = "done";
      else if (i === firstMissing || (firstMissing === -1 && i === steps.length - 1)) st = "act";
      if (done) st = "done";
      const sub = st === "done" ? "готово" : st === "act" ? (finished === null ? "идёт" : "остановилось") : "ждёт";
      return `<div class="s3 ${st}"><span class="i">${stepIcon(st)}</span><span>${esc(s.text)}<small>${esc(sub)}</small></span><span class="tm">${esc(s.time)}</span></div>`;
    })
    .join("");
  const idx = done ? steps.length : firstMissing === -1 ? steps.length : firstMissing + 1;
  $("#provstep").textContent = `шаг ${Math.max(1, idx)} из ${steps.length}`;
  const cur = done ? null : steps[Math.min(firstMissing === -1 ? steps.length - 1 : firstMissing, steps.length - 1)];
  $("#provnow").textContent = done ? "готово" : cur ? cur.text : "подготовка…";
  $("#provlive").className = "live" + (finished === null ? "" : " done");
}

$("#create").addEventListener("click", async () => {
  const brands = [];
  if ($("#b-irz").checked) brands.push("irzOS");
  if ($("#b-dnx").checked) brands.push("dnxOS");
  const { target, arch } = parts();
  const name = $("#name").value.trim();
  const release = $("#release").value.trim();
  const body = {
    name,
    board: $("#board").value.trim(),
    target,
    arch,
    release,
    source: mode,
    repo: $("#repo").value.trim(),
    branch: $("#branch").value,
    brands,
  };
  try {
    const r = await fetch("/api/platforms", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok || !d.ok) throw new Error(d.error || r.statusText);
    started = new Date().toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
    $("#addform").style.display = "none";
    $("#prov").style.display = "";
    $("#pagehead").textContent = `${name} · SDK ${mode === "git" ? "собирается" : "скачивается"}`;
    $("#pagesub").textContent =
      `${target} · ${arch} · ${mode === "git" ? "ветка " + body.branch : "готовый архив"} → OpenWrt ${release} · начато ${started}`;
    renderSteps([], null);
    poll(name);
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
      const lines = d.lines || [];
      const el = $("#provlog");
      const bottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 20;
      el.textContent = lines.join("\n") || "…";
      if (bottom) el.scrollTop = el.scrollHeight;

      const doneLine = lines.find((l) => l.startsWith("EXIT:"));
      const code = doneLine ? Number(doneLine.slice(5)) : null;
      renderSteps(lines, code);
      if (doneLine) {
        clearInterval(timer);
        if (code === 0) {
          $("#provnow").textContent = "готово";
          $("#provstep").textContent = "открываю платформу…";
          $("#provsteps").querySelectorAll(".s3").forEach((x) => {
            x.classList.remove("wait", "act"); x.classList.add("done");
          });
          setTimeout(() => { location.href = `/platform/${encodeURIComponent(name)}`; }, 1200);
        } else {
          $("#provnow").textContent = "не получилось";
          $("#provstep").textContent = "платформа не создана";
        }
      }
    } catch (e) {
      $("#provlog").textContent = e.message;
    }
  };
  tick();
  timer = setInterval(tick, 2000);
}

render();
loadExisting();
