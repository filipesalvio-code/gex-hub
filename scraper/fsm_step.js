(() => {
  const grid = document.querySelector('.MuiDataGrid-root');
  const scroller = grid.querySelector('.MuiDataGrid-virtualScroller');
  const X = __X__, Y = __Y__;
  return new Promise(done => {
    scroller.scrollLeft = X;
    scroller.scrollTop = Y;
    scroller.dispatchEvent(new Event('scroll', {bubbles: true}));
    setTimeout(() => {
      const cols = {};
      grid.querySelectorAll('.MuiDataGrid-columnHeader[data-field]').forEach(h => {
        cols[h.getAttribute('data-field')] = {
          header: (h.querySelector('.MuiDataGrid-columnHeaderTitle') || h).innerText.trim(),
          colIndex: Number(h.getAttribute('aria-colindex')),
        };
      });
      const rows = {};
      grid.querySelectorAll('.MuiDataGrid-row').forEach(r => {
        const ri = r.getAttribute('data-rowindex') ?? r.getAttribute('aria-rowindex');
        rows[ri] = rows[ri] || {cells: {}};
        r.querySelectorAll('[role=gridcell][data-field]').forEach(c => {
          rows[ri].cells[c.getAttribute('data-field')] = c.innerText.trim();
        });
      });
      done(JSON.stringify({x: X, y: Y, cols, rows}));
    }, 400);
  });
})()
