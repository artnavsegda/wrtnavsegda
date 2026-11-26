const $ = (s) => document.querySelector(s);

function syncArch() {
  $("#arch").value = $("#target").value.split("|")[1];
}
$("#target").addEventListener("change", syncArch);
syncArch();

$("#create").addEventListener("click", async () => {
  const [target] = $("#target").value.split("|");
  const brands = [];
  if ($("#b-irz").checked) brands.push("irzOS");
  if ($("#b-dnx").checked) brands.push("dnxOS");
  const body = {
    name: $("#name").value.trim(),
    board: $("#board").value.trim(),
    target,
    arch: $("#arch").value,
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
