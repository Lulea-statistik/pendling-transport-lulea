(()=>{
const root=document.getElementById('freightTruckStock');if(!root)return;
const E=(t,v)=>{const x=document.createElement(t);if(v!==undefined)x.textContent=v;return x};
const fmt=v=>Number(v).toLocaleString('sv-SE');
fetch('data/freight-truck-stock.json').then(r=>{if(!r.ok)throw Error('Data saknas');return r.json()}).then(d=>{
 if(d.status!=='source_data'||!Array.isArray(d.rows))throw Error('Ingen verifierad fordonsstatistik');
 let year='2025';function draw(){
 root.replaceChildren();root.append(E('h2','Lätta och tunga lastbilar'));
 root.append(E('p','Antal registrerade lastbilar i trafik vid årsslut, enligt SCB. Lätta ≤3,5 ton och tunga >3,5 ton. Samtliga drivmedel och ägarkategorier ingår; detta är inte samma sak som körd lastbilstrafik i kommunen.'));
 const control=E('label','År '),sel=E('select');['2025','2024'].forEach(y=>{const o=E('option',y);o.value=y;sel.append(o)});sel.value=year;sel.addEventListener('change',()=>{year=sel.value;draw()});control.append(sel);root.append(control);
 const codes=['2580','2582','2581','2514','2560'];const values=codes.map(code=>{const data=d.rows.filter(r=>r.kommun_code===code&&r.year===year);return {name:data[0]?.kommun||code,light:data.find(r=>r.kind==='light')?.count,heavy:data.find(r=>r.kind==='heavy')?.count}}).filter(x=>Number.isFinite(x.light)&&Number.isFinite(x.heavy));
 const max=Math.max(...values.map(x=>x.light+x.heavy),1);const bars=E('div');bars.style.cssText='display:grid;gap:12px;margin:18px 0';
 for(const row of values){const outer=E('div');outer.style.cssText='display:grid;grid-template-columns:minmax(100px,150px) minmax(120px,1fr) 105px;gap:8px;align-items:center';const label=E('strong',row.name);const track=E('div');track.style.cssText='display:flex;width:100%;height:24px;background:#e5e7eb;overflow:hidden;border-radius:4px';for(const [value,color,kind] of [[row.light,'#d65a55','Lätta'],[row.heavy,'#d4a32d','Tunga']]){const seg=E('span');seg.style.cssText='height:100%;width:'+((value/max)*100)+'%;background:'+color;seg.title=kind+': '+fmt(value);track.append(seg)}outer.append(label,track,E('span',fmt(row.light+row.heavy)));bars.append(outer)}
 root.append(bars);
 const legend=E('p');legend.className='source-note';legend.textContent='Röd = lätta lastbilar · Guld = tunga lastbilar. Talet till höger är summan.';root.append(legend);
 const table=E('table');table.style.width='100%';let tr=E('tr');for(const c of ['Kommun','Lätta','Tunga','Totalt'])tr.append(E('th',c));table.append(tr);for(const x of values){tr=E('tr');for(const c of [x.name,fmt(x.light),fmt(x.heavy),fmt(x.light+x.heavy)]){const td=E('td',c);td.style.padding='6px';tr.append(td)}table.append(tr)}const scroll=E('div');scroll.style.overflowX='auto';scroll.append(table);root.append(scroll);
 const source=E('a','Källa: SCB FordonTrafik');source.href=d.url;source.target='_blank';source.rel='noopener noreferrer';root.append(source)
 }draw()
}).catch(err=>{root.append(E('p','Kunde inte visa SCB:s lastbilsstatistik: '+err.message))})
})();