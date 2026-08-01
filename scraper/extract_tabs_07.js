(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const text = (el) => (el ? (el.textContent || "").replace(/\s+/g, " ").trim() : "");

  const clickTab = async (label) => {
    const tabs = Array.from(document.querySelectorAll(".MuiTab-root"));
    const t = tabs.find((el) => text(el) === label);
    if (!t) return false;
    t.click();
    await sleep(2500);
    return true;
  };

  const grab = () => {
    const sel = document.querySelector('.MuiTab-root[aria-selected="true"]');
    const charts = Array.from(
      document.querySelectorAll(".recharts-responsive-container")
    ).map((c) => ({
      legends: Array.from(c.querySelectorAll(".recharts-legend-item")).map((l) => text(l)),
      xTicks: Array.from(c.querySelectorAll(".recharts-xAxis .recharts-cartesian-axis-tick-value, .recharts-xAxis text")).map((t) => text(t)).filter(Boolean),
      yTicks: Array.from(c.querySelectorAll(".recharts-yAxis .recharts-cartesian-axis-tick-value, .recharts-yAxis text")).map((t) => text(t)).filter(Boolean),
      refLineLabels: Array.from(c.querySelectorAll(".recharts-reference-line text, .recharts-label")).map((t) => text(t)).filter(Boolean),
    })).filter((c) => c.legends.length || c.xTicks.length || c.yTicks.length);

    // Any visible MUI grid rows
    const grid = document.querySelector(".MuiDataGrid-root");
    let gridData = null;
    if (grid) {
      const headers = Array.from(grid.querySelectorAll(".MuiDataGrid-columnHeader")).map((h) =>
        text(h.querySelector(".MuiDataGrid-columnHeaderTitle")) || h.getAttribute("data-field") || text(h)
      ).filter((x) => x !== "");
      const rows = Array.from(grid.querySelectorAll(".MuiDataGrid-row")).map((r) =>
        Array.from(r.querySelectorAll(".MuiDataGrid-cell")).map((c) => text(c))
      );
      gridData = { headers, rows };
    }

    // tab-specific main text (center panel): grab text after nav header
    const main = document.querySelector("main") || document.body;
    const mainText = (main.innerText || "").replace(/\n{3,}/g, "\n").trim();
    return { selected_tab: text(sel), charts, grid: gridData, main_text: mainText.slice(0, 4000) };
  };

  const results = {};
  const tabLabels = ["Put & Call Impact", "Live Price & SG Levels", "Composite View", "Risk Reversal", "History"];
  for (const label of tabLabels) {
    const ok = await clickTab(label);
    if (!ok) { results[label] = { error: "tab not found" }; continue; }
    results[label] = grab();
  }

  // restore default tab
  await clickTab("Put & Call Impact");
  return JSON.stringify({ url: location.href, title: document.title, tabs: results });
})()
