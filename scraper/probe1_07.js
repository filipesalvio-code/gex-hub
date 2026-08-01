(() => {
  // Broad structural outline of the Equity Hub page
  const text = (el) => (el.innerText || "").replace(/\s+/g, " ").trim();
  const out = { url: location.href, title: document.title };

  // Top-level visible containers
  const bodyTextLen = (document.body.innerText || "").length;
  out.bodyTextLen = bodyTextLen;

  // Find candidate cards / widgets by common class hints
  const counts = {};
  document.querySelectorAll("[class]").forEach((el) => {
    const cls = el.className && el.className.baseVal !== undefined ? "" : String(el.className);
    cls.split(/\s+/).forEach((c) => {
      if (/card|metric|stat|level|table|grid|chart|tab|panel|tile|hub/i.test(c)) {
        counts[c] = (counts[c] || 0) + 1;
      }
    });
  });
  out.classHints = Object.entries(counts).sort((a,b)=>b[1]-a[1]).slice(0, 40);

  // All tables with row counts
  out.tables = Array.from(document.querySelectorAll("table")).map((t, i) => ({
    i,
    rows: t.querySelectorAll("tr").length,
    head: text(t.querySelector("thead") || t.querySelector("tr")).slice(0, 200),
  }));

  // Tabs
  out.tabs = Array.from(document.querySelectorAll('[role="tab"], button, [class*="tab"]'))
    .map((el) => text(el))
    .filter((t) => t && t.length < 40)
    .slice(0, 40);

  // First 2500 chars of body text for a quick smell test
  out.bodySample = (document.body.innerText || "").slice(0, 2500);

  return JSON.stringify(out);
})()
