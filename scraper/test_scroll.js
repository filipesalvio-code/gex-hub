(() => {
  const grid = document.querySelector('.MuiDataGrid-root');
  const scroller = grid.querySelector('.MuiDataGrid-virtualScroller');
  scroller.scrollLeft = 4000;
  scroller.dispatchEvent(new Event('scroll', {bubbles: true}));
  return new Promise(done => setTimeout(() => {
    const heads = [...grid.querySelectorAll('.MuiDataGrid-columnHeader[data-field]')]
      .map(h => ({f: h.getAttribute('data-field'), ci: h.getAttribute('aria-colindex')}));
    done(JSON.stringify({scrollLeftNow: scroller.scrollLeft, heads}));
  }, 700));
})()
