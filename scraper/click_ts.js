(() => {
  const tabs = [...document.querySelectorAll('.MuiTab-root')];
  const t = tabs.find(x => x.innerText.trim() === 'Term Structure');
  if (!t) return JSON.stringify({err: 'tab not found'});
  t.click();
  return new Promise(done => setTimeout(() => {
    const out = {url: location.href, title: document.title};
    const active = document.querySelector('.MuiTab-root.Mui-selected');
    out.activeTab = active ? active.innerText.trim() : null;
    out.bodyText = document.body.innerText.slice(0, 3000);
    out.svgCount = document.querySelectorAll('svg').length;
    out.canvasCount = document.querySelectorAll('canvas').length;
    out.tableCount = document.querySelectorAll('table').length;
    out.gridCount = document.querySelectorAll('.MuiDataGrid-root').length;
    done(JSON.stringify(out));
  }, 4000));
})()
