(() => {
  const tabs = [...document.querySelectorAll('.MuiTab-root')];
  const t = tabs.find(x => x.innerText.trim() === 'VIX Term Structure');
  if (!t) return JSON.stringify({err: 'tab not found'});
  t.click();
  return new Promise(done => setTimeout(() => {
    const out = {url: location.href};
    const active = document.querySelector('.MuiTab-root.Mui-selected');
    out.activeTab = active ? active.innerText.trim() : null;
    out.bodyText = document.body.innerText.slice(0, 4000);
    out.grids = document.querySelectorAll('.MuiDataGrid-root').length;
    const charts = [...document.querySelectorAll('svg.recharts-surface')].map(s => ({
      w: s.getAttribute('width'), h: s.getAttribute('height'),
      nCurves: s.querySelectorAll('path.recharts-line-curve').length,
      nDots: s.querySelectorAll('circle.recharts-dot').length,
    }));
    out.charts = charts;
    done(JSON.stringify(out));
  }, 4000));
})()
