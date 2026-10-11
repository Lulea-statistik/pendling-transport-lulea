(()=>{
const root=document.getElementById('freightHeavyTrafficQA');if(!root)return;
const el=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e};
const fmt=(x,d=1)=>Number(x).toLocaleString('sv-SE',{minimumFractionDigits:d,maximumFractionDigits:d});
fetch('data/nvdb-heavy-traffic-coverage.json').then(r=>{if(!r.ok)throw Error('Unavailable');return r.json()}).then(data=>{
root.replaceChildren();root.append(el('h2','Tung trafik – verifierad geografisk täckning'));
root.append(el('p','ÅDT tunga fordon och beräknade fordonskilometer på de väglänkar där Trafikverkets NVDB har uppgifter. Kommunernas övriga vägar ingår inte i dessa trafikvärden.'));
const table=el('table'),thead=el('thead'),tr=el('tr');['Kommun','ÅDT-täckning, km','Ungefärlig täckning av bilvägnätet','Tung trafik, % av ÅDT','Miljoner tunga fordonskm/år'].forEach(t=>tr.append(el('th',t)));thead.append(tr);table.append(thead);const body=el('tbody');
for(const row of data.municipalities){const t=el('tr');[row.name,fmt(row.covered_km),fmt(row.coverage_pct)+' %',fmt(row.heavy_share_pct)+' %',fmt(row.heavy_vehicle_km_year/1e6,2)].forEach(v=>{const td=el('td',v);td.style.padding='7px 6px';t.append(td)});body.append(t)}table.append(body);const wrapper=el('div');wrapper.style.overflowX='auto';wrapper.append(table);root.append(wrapper);
const p=el('p','Kvalitetsstatus: inga överlappande vägsträckor med motstridiga ÅDT-värden hittades. Täckningsandelen bygger på jämförelse med ett separat klassificerat vägnät och är därför ungefärlig. Uppgifter om mätår, dubbla körbanor och fordonsslag behöver fortfarande granskas. Resultaten får inte extrapoleras till hela kommunen och kan inte direkt användas som bevis för tankning inom kommunen.');p.className='source-note';root.append(p);
const a=el('a','Källa och körning: NVDB kvalitetskontroll');a.href=data.run_url;a.target='_blank';a.rel='noopener noreferrer';root.append(a);
}).catch(()=>{root.append(el('p','Kvalitetskontrollerad tungtrafikdata är ännu inte tillgänglig.'))});
})();