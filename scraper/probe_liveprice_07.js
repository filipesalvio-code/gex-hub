(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const text = (el) => (el ? (el.textContent || "").replace(/\s+/g, " ").trim() : "");

  // go to Live Price & SG Levels
  const tabs = Array.from(document.querySelectorAll(".MuiTab-root"));
  const t = tabs.find((el) => text(el) === "Live Price & SG Levels");
  if (t) { t.click(); await sleep(3000); }

  const out = { selected: text(document.querySelector('.MuiTab-root[aria-selected="true"]')) };

  // enumerate all svg/canvas elements with ancestry hints
  out.graphics = Array.from(document.querySelectorAll("svg, canvas")).slice(0, 30).map((el) => {
    let p = el, chain = [];
    for (let i = 0; i < 5 && p; i++) {
      const cls = (p.className && p.className.baseVal !== undefined ? p.className.baseVal : p.className) || "";
      chain.push(`${p.tagName}.${String(cls).split(/\s+/).slice(0, 3).join(".")}`);
      p = p.parentElement;
    }
    return { tag: el.tagName, w: el.clientWidth || el.getAttribute("width"), h: el.clientHeight || el.getAttribute("height"), chain: chain.join(" < ") };
  });

  // highcharts / lightweight-charts detection
  out.libs = {
    highcharts: !!document.querySelector(".highcharts-container"),
    lightweight: !!document.querySelector("[class*=tv-lightweight-charts]"),
    plotly: !!document.querySelector(".js-plotly-plot"),
    recharts: document.querySelectorAll(".recharts-responsive-container").length,
  };

  // text near the chart region: find element containing 'Show key levels' and dump its parent's innerText
  const anchor = Array.from(document.querySelectorAll("*")).find((el) => el.children.length === 0 && /Show key levels/.test(text(el)));
  if (anchor) {
    let p = anchor;
    for (let i = 0; i < 6 && p; i++) p = p.parentElement;
    out.chartRegionText = p ? (p.innerText || "").slice(0, 1500) : null;
  }

  // any svg text content dump (labels) for non-recharts svgs
  out.svgTexts = Array.from(document.querySelectorAll("svg")).map((svg) => {
    const txts = Array.from(svg.querySelectorAll("text")).map((t) => text(t)).filter(Boolean);
    return txts.length ? txts.slice(0, 60) : null;
  }).filter(Boolean).slice(0, 6);

  return JSON.stringify(out);
})()
