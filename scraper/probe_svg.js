(() => {
  const svgs = [...document.querySelectorAll('svg')];
  const info = svgs.map(s => ({
    cls: (s.getAttribute('class') || '').slice(0, 60),
    w: s.getAttribute('width'), h: s.getAttribute('height'),
    viewBox: s.getAttribute('viewBox'),
    nPaths: s.querySelectorAll('path').length,
    nCircles: s.querySelectorAll('circle').length,
    nTexts: s.querySelectorAll('text').length,
  }));
  // find biggest svg (the chart)
  const big = svgs.map((s, i) => ({i, n: s.querySelectorAll('path').length + s.querySelectorAll('circle').length}))
    .sort((a, b) => b.n - a.n)[0];
  const chart = svgs[big.i];
  const texts = [...chart.querySelectorAll('text')].map(t => t.textContent.trim()).filter(Boolean);
  const paths = [...chart.querySelectorAll('path')].map(p => ({
    cls: (p.getAttribute('class') || '').slice(0, 50),
    stroke: p.getAttribute('stroke'),
    dLen: (p.getAttribute('d') || '').length,
  })).filter(p => p.dLen > 50).slice(0, 10);
  return JSON.stringify({svgInfo: info, bigIndex: big.i, chartCls: (chart.getAttribute('class') || '').slice(0, 80), chartTexts: texts, longPaths: paths});
})()
