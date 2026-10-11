(()=>{
const root=document.getElementById('freightDieselDeliveries');if(!root)return;
const E=(tag,text)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;return el};
const fmt=v=>Number(v).toLocaleString('sv-SE',{maximumFractionDigits:0});
let data,year='2025';
function render(){
 root.replaceChildren();root.append(E('h2','Dieselleveranser till återförsäljare'));
 root.append(E('p','Diesel levererad till återförsäljare i kommunen är en möjlig indikator på drivmedelsmarknadens geografiska omfattning, men visar inte var lastbilar har tankat.'));
 if(!data){root.append(E('p','Inväntar första verifierade uttaget från SCB. Inga värden visas innan publicering.'));return}
 const select=E('select'),years=[...new Set(data.rows.map(x=>x.year))].sort().reverse();
 years.forEach(y=>{let o=E('option',y);o.value=y;select.append(o)});
 if(!years.includes(year))year=years[0];
 select.value=year;select.onchange=()=>{year=select.value;render()};const label=E('label','År ');label.append(select);root.append(label);
 const rows=data.rows.filter(x=>x.year===year),max=Math.max(1,...rows.map(x=>x.diesel_m3||0)),chart=E('div');chart.style.cssText='display:grid;gap:12px;margin:14px 0';
 for(const item of rows){const line=E('div'),value=item.diesel_m3;line.append(E('div',item.kommun+' — '+(value===null?'uppgift saknas':fmt(value)+' m³')));const track=E('div');track.style.cssText='height:16px;background:#e5e9ee;border-radius:6px;overflow:hidden';if(value!==null){const fill=E('div');fill.style.cssText='width:'+((value/max)*100).toFixed(2)+'%;height:100%;background:#537d9d';track.append(fill)}line.append(track);chart.append(line)}
 root.append(chart);const note=E('p','Avser leveranser till återförsäljare, inte leveranser till alla slutkunder, faktiskt såld volym eller enbart lastbilarnas diesel. Äldre oljeleveranser 2018–2023 redovisas inte i samma tidsserie på grund av skillnader i definition. Källa: SCB, '+data.source+'.');note.className='source-note';root.append(note);
 const link=E('a','Öppna ursprungstabellen hos SCB');link.href=data.source_url;link.target='_blank';link.rel='noopener noreferrer';root.append(link)
}
fetch('data/freight-diesel-reseller-deliveries.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(x=>{if(x.status!=='source_data')throw Error('unexpected data');data=x;render()}).catch(()=>{});render()
})();