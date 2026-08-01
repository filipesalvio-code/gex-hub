(() => {
  const charts = [...document.querySelectorAll('svg.recharts-surface')]
    .filter(s => (s.getAttribute('width')|0) > 100);
  const chart = charts[0];
  if (!chart) return JSON.stringify({err: 'no chart'});
  const texts = [...chart.querySelectorAll('text')].map(t => ({
    v: t.textContent.trim(), x: t.getAttribute('x'), y: t.getAttribute('y'),
    cls: (t.getAttribute('class') || '').slice(0, 50),
  })).filter(t => t.v);
  const curve = chart.querySelector('path.recharts-line-curve');
  const refLines = [...chart.querySelectorAll('.recharts-reference-line line, line.recharts-reference-line')].map(l => ({
    x1: l.getAttribute('x1'), x2: l.getAttribute('x2'), y1: l.getAttribute('y1'), y2: l.getAttribute('y2'),
    stroke: l.getAttribute('stroke'), dash: l.getAttribute('stroke-dasharray'),
  }));
  const refTexts = [...chart.querySelectorAll('.recharts-reference-line text, .recharts-reference-line *')].map(e => e.textContent && e.textContent.trim()).filter(Boolean).slice(0,10);
  const legend = [...document.querySelectorAll('.recharts-legend-wrapper *')].map(e => e.textContent && e.textContent.trim()).filter((v,i,a)=>v&&a.indexOf(v)===i).slice(0,20);
  return JSON.stringify({texts, curveD: curve ? curve.getAttribute('d') : null, refLines, refTexts, legend});
})()
