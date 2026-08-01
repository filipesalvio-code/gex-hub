(() => {
  const out = {title: document.title, url: location.href};
  // header strip: VIX / WTI / Gold labels
  const grab = (label) => {
    const els = [...document.querySelectorAll('*')].filter(e =>
      e.children.length === 0 && e.innerText && e.innerText.trim() === label);
    return els.map(e => {
      let p = e.parentElement;
      for (let i = 0; i < 3 && p; i++) {
        const t = p.innerText.trim();
        if (t && t !== label) return t.slice(0, 120);
        p = p.parentElement;
      }
      return null;
    })[0];
  };
  out.vix = grab('^VIX:');
  out.wti = grab('WTI:');
  out.gold = grab('Gold:');
  // SPX price + zscore card
  const priceBtn = [...document.querySelectorAll('button')].map(b => b.innerText.trim())
    .filter(t => /^\d{3,5}\.\d{2}$/.test(t));
  out.spxPriceButtons = priceBtn;
  const text = document.body.innerText;
  const m = text.match(/Implied Vol Z-Score\s*\n?\s*(-?[\d.]+)/);
  out.ivZScore = m ? m[1] : null;
  const d = text.match(/(\d{4}-\d{2}-\d{2})\s*\n?\s*-\s*(-?[\d.]+)/);
  out.asOfDate = d ? d[1] : null;
  out.asOfDelta = d ? d[2] : null;
  const ts = text.match(/(Mon|Tue|Wed|Thu|Fri|Sat|Sun) [A-Z][a-z]{2} \d{1,2} [\d:]+ \w+ \d{4}/);
  out.pageTimestamp = ts ? ts[0] : null;
  // active tab
  const active = document.querySelector('.MuiTab-root.Mui-selected');
  out.activeTab = active ? active.innerText.trim() : null;
  return JSON.stringify(out);
})()
