(() => {
  const text = (el) => (el ? (el.innerText || "").replace(/\s+/g, " ").trim() : "");
  const out = { url: location.href, title: document.title, captured_tab: null };

  // Selected tab
  const selTab = document.querySelector('.MuiTab-root[aria-selected="true"]');
  out.captured_tab = text(selTab);

  // Full visible body text (page is compact)
  out.full_text = (document.body.innerText || "").replace(/\n{3,}/g, "\n\n").trim();

  // DataGrid extraction (Key Daily Levels / any MUI grid visible)
  const grid = document.querySelector(".MuiDataGrid-root");
  if (grid) {
    const headers = Array.from(grid.querySelectorAll(".MuiDataGrid-columnHeader")).map((h) => ({
      field: h.getAttribute("data-field"),
      title: text(h.querySelector(".MuiDataGrid-columnHeaderTitle")) || text(h),
    }));
    const rows = Array.from(grid.querySelectorAll(".MuiDataGrid-row")).map((r) => {
      const cells = Array.from(r.querySelectorAll(".MuiDataGrid-cell")).map((c) => ({
        field: c.getAttribute("data-field"),
        value: text(c),
      }));
      return cells;
    });
    out.datagrid = { headers, rows, row_count: rows.length };
  } else {
    out.datagrid = null;
  }

  // Recharts legends + axes on visible chart(s)
  out.charts = Array.from(document.querySelectorAll(".recharts-wrapper, .recharts-responsive-container")).slice(0, 6).map((c) => {
    const legends = Array.from(c.querySelectorAll(".recharts-legend-item")).map((l) => text(l));
    const xAxis = Array.from(c.querySelectorAll(".recharts-xAxis .recharts-cartesian-axis-tick")).map((t) => text(t));
    const yAxis = Array.from(c.querySelectorAll(".recharts-yAxis .recharts-cartesian-axis-tick")).map((t) => text(t));
    const axisLabels = Array.from(c.querySelectorAll(".recharts-label")).map((t) => text(t));
    return { legends, xAxis: xAxis.slice(0, 30), yAxis: yAxis.slice(0, 30), axisLabels: axisLabels.slice(0, 10) };
  }).filter((c) => c.legends.length || c.xAxis.length || c.yAxis.length);

  // Chips (symbol selector) for context
  out.symbol_chips = Array.from(document.querySelectorAll(".MuiChip-root")).map((c) => text(c)).filter(Boolean);

  return JSON.stringify(out);
})()
