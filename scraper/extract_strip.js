(() => {
  // find the header strip container holding VIX/WTI/Gold
  const labels = ['VIX', 'WTI', 'Gold'];
  const out = {};
  for (const lab of labels) {
    const els = [...document.querySelectorAll('*')].filter(e =>
      e.children.length <= 1 && e.innerText && e.innerText.trim().replace(/^\^/, '').startsWith(lab));
    const rec = els.map(e => {
      // walk up to find a small container with both label and value
      let p = e;
      for (let i = 0; i < 4 && p; i++) {
        const t = p.innerText.trim();
        if (t.length < 80 && /[\d.]+/.test(t)) return t;
        p = p.parentElement;
      }
      return null;
    }).find(v => v);
    out[lab] = rec || null;
  }
  return JSON.stringify(out);
})()
