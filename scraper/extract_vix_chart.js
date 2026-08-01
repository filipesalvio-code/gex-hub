(() => {
  const chart = [...document.querySelectorAll('svg.recharts-surface')].filter(s => (s.getAttribute('width')|0) > 100)[0];
  if (!chart) return JSON.stringify({err: 'no chart'});
  const texts = [...chart.querySelectorAll('text')].map(t => ({
    v: t.textContent.trim(), x: t.getAttribute('x'), y: t.getAttribute('y'),
    cls: (t.getAttribute('class') || '').slice(0, 50),
  })).filter(t => t.v);
  const curves = [...chart.querySelectorAll('path.recharts-line-curve')].map(p => ({
    cls: (p.getAttribute('class') || '').slice(0, 80),
    stroke: p.getAttribute('stroke'), dLen: (p.getAttribute('d')||'').length,
  }));
  const dots = [...chart.querySelectorAll('circle.recharts-dot')].map(c => ({
    cx: c.getAttribute('cx'), cy: c.getAttribute('cy'),
    cls: (c.getAttribute('class') || '').slice(0, 80), fill: c.getAttribute('fill'),
  }));
  const legend = [...document.querySelectorAll('.recharts-legend-wrapper *')].map(e => e.textContent && e.textContent.trim()).filter((v,i,a)=>v&&a.indexOf(v)===i).slice(0,20);
  return JSON.stringify({texts, curves, dots, legend});
})()
