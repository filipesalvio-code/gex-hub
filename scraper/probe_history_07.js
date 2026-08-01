(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const text = (el) => (el ? (el.textContent || "").replace(/\s+/g, " ").trim() : "");
  const tabs = Array.from(document.querySelectorAll(".MuiTab-root"));
  const t = tabs.find((el) => text(el) === "History");
  if (t) { t.click(); await sleep(3000); }
  const out = { selected: text(document.querySelector('.MuiTab-root[aria-selected="true"]')) };
  const grids = Array.from(document.querySelectorAll(".MuiDataGrid-root"));
  out.grids = grids.map((g) => ({
    aria_rowcount: g.getAttribute("aria-rowcount"),
    aria_colcount: g.getAttribute("aria-colcount"),
    visible_rows: g.querySelectorAll(".MuiDataGrid-row").length,
    pagination: text(g.querySelector(".MuiTablePagination-root")),
    first_header: text(g.querySelector(".MuiDataGrid-columnHeader")),
  }));
  return JSON.stringify(out);
})()
