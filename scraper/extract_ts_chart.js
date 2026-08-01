(() => {
  const svgs = [...document.querySelectorAll('svg.recharts-surface')];
  const chart = svgs.sort((a, b) => (b.getAttribute('width')|0) - (a.getAttribute('width')|0))[0];
  if (!chart) return JSON.stringify({err: 'no chart'});
  const texts = [...chart.querySelectorAll('text')].map(t => ({
    v: t.textContent.trim(), x: t.getAttribute('x'), y: t.getAttribute('y'),
    cls: (t.getAttribute('class') || '').slice(0, 60),
  })).filter(t => t.v);
  const circles = [...chart.querySelectorAll('circle')].map(c => ({
    cx: c.getAttribute('cx'), cy: c.getAttribute('cy'), r: c.getAttribute('r'),
    fill: c.getAttribute('fill'), cls: (c.getAttribute('class') || '').slice(0, 60),
  }));
  const curve = chart.querySelector('path.recharts-line-curve');
  return JSON.stringify({texts, circles, curveD: curve ? curve.getAttribute('d') : null});
})()
