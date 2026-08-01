(() => {
  const chart = [...document.querySelectorAll('svg.recharts-surface')].filter(s => (s.getAttribute('width')|0) > 100)[0];
  const curve = chart.querySelector('path.recharts-line-curve');
  if (!curve) return JSON.stringify({err: 'no curve'});
  const L = curve.getTotalLength();
  const pts = [];
  const N = 220;
  for (let i = 0; i <= N; i++) {
    const p = curve.getPointAtLength((L * i) / N);
    pts.push([+p.x.toFixed(2), +p.y.toFixed(2)]);
  }
  return JSON.stringify({pts, totalLen: L});
})()
