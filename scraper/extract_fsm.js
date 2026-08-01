(async () => {
  const grid = document.querySelector('.MuiDataGrid-root');
  if (!grid) return JSON.stringify({err: 'no MUI grid'});
  const scroller = grid.querySelector('.MuiDataGrid-virtualScroller');
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const cols = {}; // field -> {colIndex, header}
  const rows = {}; // data-rowindex -> {cells: {field: value}}
  const capture = () => {
    grid.querySelectorAll('.MuiDataGrid-columnHeader[data-field]').forEach(h => {
      const f = h.getAttribute('data-field');
      cols[f] = cols[f] || {};
      cols[f].header = (h.querySelector('.MuiDataGrid-columnHeaderTitle') || h).innerText.trim();
      cols[f].colIndex = Number(h.getAttribute('aria-colindex'));
    });
    grid.querySelectorAll('.MuiDataGrid-row').forEach(r => {
      const ri = r.getAttribute('data-rowindex') ?? r.getAttribute('data-id') ?? r.getAttribute('aria-rowindex');
      rows[ri] = rows[ri] || {cells: {}};
      r.querySelectorAll('[role=gridcell][data-field]').forEach(c => {
        rows[ri].cells[c.getAttribute('data-field')] = c.innerText.trim();
      });
    });
  };
  const maxX = Math.max(0, scroller.scrollWidth - scroller.clientWidth);
  const maxY = Math.max(0, scroller.scrollHeight - scroller.clientHeight);
  const stepX = Math.max(200, scroller.clientWidth * 0.7);
  const stepY = Math.max(100, scroller.clientHeight * 0.7);
  const xSteps = [];
  for (let x = 0; x < maxX; x += stepX) xSteps.push(x);
  xSteps.push(maxX);
  const ySteps = [];
  for (let y = 0; y < maxY; y += stepY) ySteps.push(y);
  ySteps.push(maxY);
  for (const y of ySteps) {
    for (const x of xSteps) {
      scroller.scrollTo(x, y);
      await sleep(350);
      capture();
    }
  }
  scroller.scrollTo(0, 0);
  await sleep(300);
  capture();
  // sort columns by colIndex
  const colList = Object.entries(cols).sort((a, b) => a[1].colIndex - b[1].colIndex)
    .map(([f, c]) => ({field: f, header: c.header, colIndex: c.colIndex}));
  const rowList = Object.entries(rows).sort((a, b) => Number(a[0]) - Number(b[0]))
    .map(([ri, r]) => ({rowIndex: Number(ri), cells: r.cells}));
  return JSON.stringify({
    title: document.title, url: location.href,
    grid: {cols: colList, rows: rowList, nCols: colList.length, nRows: rowList.length,
           scrollWidth: scroller.scrollWidth, scrollHeight: scroller.scrollHeight}
  });
})()
