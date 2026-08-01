(async()=>{
const dlg=document.querySelector("[role=dialog], .MuiDialog-root, .MuiModal-root");
if(!dlg) return JSON.stringify({err:"no dialog"});
const wait=ms=>new Promise(r=>setTimeout(r,ms));
const batch=[];
let pages=0, stopped=null;
for(let i=0;i<10;i++){
  const items=[...dlg.querySelectorAll(".MuiListItemButton-root")].map(el=>(el.innerText||"").trim().replace(/\s+/g," "));
  batch.push(items); pages++;
  const back=[...dlg.querySelectorAll("button")].find(b=>/ArrowBackIcon/.test(b.innerHTML));
  if(!back){stopped="no-back";break}
  if(back.disabled){stopped="disabled";break}
  back.click(); await wait(800);
}
return JSON.stringify({pages, stopped, batch});
})()
