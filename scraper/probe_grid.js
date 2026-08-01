(() => {
  const grid = document.querySelector('.MuiDataGrid-root');
  if (!grid) return JSON.stringify({err: 'no grid'});
  const scroller = grid.querySelector('.MuiDataGrid-virtualScroller');
  const render = grid.querySelector('.MuiDataGrid-virtualScrollerRenderZone');
  return JSON.stringify({
    scrollW: scroller.scrollWidth, scrollH: scroller.scrollHeight,
    clientW: scroller.clientWidth, clientH: scroller.clientHeight,
    renderW: render ? render.style.width : null, renderH: render ? render.style.height : null,
    nRowsDom: grid.querySelectorAll('.MuiDataGrid-row').length,
    nColsDom: grid.querySelectorAll('.MuiDataGrid-columnHeader').length,
    nCellsDom: grid.querySelectorAll('[role=gridcell]').length,
  });
})()
