(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const text = (el) => (el ? (el.textContent || "").replace(/\s+/g, " ").trim() : "");
  const tabs = Array.from(document.querySelectorAll(".MuiTab-root"));
  const t = tabs.find((el) => text(el) === "History");
  if (t) { t.click(); await sleep(2500); }

  // find the history grid: the one whose first header is "Trade Date"
  const grids = Array.from(document.querySelectorAll(".MuiDataGrid-root"));
  const grid = grids.find((g) => text(g.querySelector(".MuiDataGrid-columnHeader")).includes("Trade Date")) || grids[0];
  const headers = Array.from(grid.querySelectorAll(".MuiDataGrid-columnHeader")).map((h) => h.getAttribute("data-field") || text(h));

  const scroller = grid.querySelector(".MuiDataGrid-virtualScroller");
  const seen = new Map();
  const collect = () => {
    Array.from(grid.querySelectorAll(".MuiDataGrid-row")).forEach((r) => {
      const cells = Array.from(r.querySelectorAll(".MuiDataGrid-cell")).map((c) => text(c));
      if (cells.length && cells[0]) seen.set(cells[0], cells);
    });
  };
  collect();
  if (scroller) {
    const step = Math.max(200, Math.floor(scroller.clientHeight * 0.9));
    let last = -1, same = 0;
    while (same < 4) {
      scroller.scrollTop += step;
      await sleep(350);
      collect();
      if (scroller.scrollTop === last) same++; else same = 0;
      last = scroller.scrollTop;
      if (scroller.scrollTop > 200000) break; // safety
    }
    scroller.scrollTop = 0;
  }
  await sleep(300); collect();
  return JSON.stringify({
    url: location.href, title: document.title,
    grid_headers: headers,
    total_collected: seen.size,
    rows: Array.from(seen.values()),
    scrollHeight: scroller ? scroller.scrollHeight : null,
  });
})()
