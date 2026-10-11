(()=>{
 const root=document.getElementById('roadStandardCoverage');if(!root)return;
 const el=(tag,txt)=>{const n=document.createElement(tag);if(txt!==undefined)n.textContent=txt;return n};
 const fmt=(n,dec=1)=>Number(n).toLocaleString('sv-SE',{minimumFractionDigits:dec,maximumFractionDigits:dec});
 fetch('data/nvdb-road-standard-coverage.json').then(r=>{if(!r.ok)throw Error('data saknas');return r.json()}).then(data=>{
  root.replaceChildren();root.append(el('h2','Datatäckning: vägbredd och körfält'));
  root.append(el('p','Andel av bilvägnätet där NVDB:s attribut går att knyta till exakt samma väggeometri. Saknad uppgift räknas inte som noll.'));
  const table=el('table'),head=el('tr');['Kommun','Bilvägnät','Vägbredd känd','Körfält kända'].forEach(s=>head.append(el('th',s)));table.append(head);
  const all=data.municipalities;let total=0,width=0,lanes=0;
  for(const m of all){const tr=el('tr');[m.name,fmt(m.total,0)+' km',fmt(100*m.width/m.total)+' %',fmt(100*m.lanes/m.total)+' %'].forEach(s=>tr.append(el('td',s)));table.append(tr);total+=m.total;width+=m.width;lanes+=m.lanes}
  const tr=el('tr');['Luleå FA-region',fmt(total,0)+' km',fmt(100*width/total)+' %',fmt(100*lanes/total)+' %'].forEach(s=>tr.append(el('td',s)));table.append(tr);
  const sc=el('div');sc.style.overflowX='auto';sc.append(table);root.append(sc);
  const c=el('div');c.className='controls';const lab=el('label','Vägbreddsfördelning, kommun '),sel=el('select');
  all.forEach(m=>{const opt=el('option',m.name);opt.value=m.code;sel.append(opt)});lab.append(sel);c.append(lab);root.append(c);
  const chart=el('div');root.append(chart);
  function update(){
   const m=all.find(x=>x.code===sel.value)||all[0];chart.replaceChildren();
   chart.append(el('h3','Registrerade vägsträckor i '+m.name+' ('+fmt(m.width,0)+' km)'));
   const top=Math.max(...Object.values(m.widthBands));
   for(const [category,v] of Object.entries(m.widthBands)){
    chart.append(el('div',category+' — '+fmt(v,1)+' km ('+fmt(100*v/m.width)+' % av dokumenterad bredd)'));
    const track=el('div');track.style.cssText='height:15px;background:#e9edf2;border-radius:8px;overflow:hidden;margin:4px 0 10px';
    const bar=el('div');bar.style.cssText='background:#5c839c;height:100%;width:'+fmt(v/top*100,2).replace(',','.')+'%';track.append(bar);chart.append(track);
   }
  }sel.addEventListener('change',update);update();
  const note=el('p','Preliminär NVDB-analys, körning '+data.run_id+'. Breddfördelningen avser ENDAST vägsträckor med registrerad bredd. Den får inte generaliseras till hela bilvägnätet. Avrundade kilometer kan ge små summaskillnader.');note.className='source-note';root.append(note);
 }).catch(()=>{root.textContent='Datatäckningen för vägbredd kunde inte laddas.'});
})();