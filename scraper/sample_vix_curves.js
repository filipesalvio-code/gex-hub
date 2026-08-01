(() => {
  const chart = [...document.querySelectorAll('svg.recharts-surface')].filter(s => (s.getAttribute('width')|0) > 100)[0];
  const out = {series: {}, dots: [...chart.querySelectorAll('circle.recharts-dot')].map(c => ({
    cx: +(+c.getAttribute('cx')).toFixed(2), cy: +(+c.getAttribute('cy')).toFixed(2),
    stroke: c.getAttribute('stroke'), fill: c.getAttribute('fill')}))};
  [...chart.querySelectorAll('path.recharts-line-curve')].forEach(p => {
    const stroke = p.getAttribute('stroke');
    const L = p.getTotalLength();
    if (!L) return;
    const pts = [];
    const N = 200;
    for (let i = 0; i <= N; i++) {
      const q = p.getPointAtLength((L * i) / N);
      pts.push([+q.x.toFixed(2), +q.y.toFixed(2)]);
    }
    out.series[stroke] = pts;
  });
  return JSON.stringify(out);
})()
