(() => {
  const grid = document.querySelector('.MuiDataGrid-root');
  const scroller = grid.querySelector('.MuiDataGrid-virtualScroller');
  scroller.scrollLeft = 3900;  // around colIndex ~40 (7075 area)
  scroller.scrollTop = 309;
  scroller.dispatchEvent(new Event('scroll', {bubbles: true}));
  return new Promise(done => setTimeout(() => {
    const out = {row18: {}, row8_8150: null};
    // scroll to 8150 (last col) too far for one shot; check row18 here
    grid.querySelectorAll('.MuiDataGrid-row').forEach(r => {
      const ri = r.getAttribute('data-rowindex');
      if (ri === '18') {
        r.querySelectorAll('[role=gridcell][data-field]').forEach(c => {
          out.row18[c.getAttribute('data-field')] = c.innerText.trim();
        });
      }
    });
    // now jump to far right for 8150 check
    scroller.scrollLeft = 9587;
    scroller.dispatchEvent(new Event('scroll', {bubbles: true}));
    setTimeout(() => {
      grid.querySelectorAll('.MuiDataGrid-row').forEach(r => {
        const ri = r.getAttribute('data-rowindex');
        if (ri === '8') {
          const c = r.querySelector('[role=gridcell][data-field="8150"]');
          out.row8_8150 = c ? JSON.stringify(c.innerText) : 'CELL_NOT_IN_DOM';
        }
      });
      scroller.scrollLeft = 0; scroller.scrollTop = 0;
      scroller.dispatchEvent(new Event('scroll', {bubbles: true}));
      done(JSON.stringify(out));
    }, 600);
  }, 700));
})()
