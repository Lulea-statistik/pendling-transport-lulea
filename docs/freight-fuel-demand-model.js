(()=>{
const root=document.getElementById('freightFuelModel');if(!root)return;
const E=(t,txt)=>{const x=document.createElement(t);if(txt!==undefined)x.textContent=txt;return x};
const fmt=(x,n=0)=>Number(x).toLocaleString('sv-SE',{maximumFractionDigits:n,minimumFractionDigits:n});
const km={"2024":{light:13030,heavy:40060},"2025":{light:14320,heavy:40790}};
let year="2025",lightL=9,heavyL=30,lightDiesel=80,heavyDiesel=95,stock=null,delivery=null;
function draw(){
root.replaceChildren();root.append(E('h2','Teoretiskt dieselbehov hos registrerade lastbilar'));
root.append(E('p','Modell för lastbilars årliga körsträcka och tänkt dieselförbrukning med rikets genomsnittliga körsträcka. Alla lastbilar antas inte gå på diesel: justera dieselandelarna. Leveranser till återförsäljare innefattar även andra dieselförbrukare.'));
if(!stock||!delivery){root.append(E('p','Inväntar verifierade data från SCB om både registrerade lastbilar och dieselleveranser. Ingen jämförelsekvot visas ännu.'));return}
const yearLabel=E('label','År '),sel=E('select');["2025","2024"].forEach(y=>{const o=E('option',y);o.value=y;sel.append(o)});sel.value=year;sel.addEventListener('change',()=>{year=sel.value;draw()});yearLabel.append(sel);root.append(yearLabel);
const description=E('p','Antaganden: rikssnitt körsträcka '+fmt(km[year].light/10)+' mil/år för lätt lastbil och '+fmt(km[year].heavy/10)+' mil/år för tung lastbil. Liter/100 km och dieselandelar nedan är scenarioantaganden, inte uppmätta kommunvärden.');description.className='source-note';root.append(description);
const controls=E('div');controls.style.cssText='display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:12px 0';
for(const [caption,min,max,step,val,update,suffix] of [
 ['Lätta lastbilar – liter/100 km',5,18,0.5,lightL,v=>lightL=v,' l/100 km'],
 ['Tunga lastbilar – liter/100 km',15,50,0.5,heavyL,v=>heavyL=v,' l/100 km'],
 ['Dieselandel lätta lastbilar',0,100,5,lightDiesel,v=>lightDiesel=v,' %'],
 ['Dieselandel tunga lastbilar',0,100,5,heavyDiesel,v=>heavyDiesel=v,' %']]){
 const group=E('label');group.append(E('div',caption));const number=E('input');number.type='number';number.min=min;number.max=max;number.step=step;number.value=val;number.style.width='100%';
 number.addEventListener('change',()=>{const n=Number(number.value);if(Number.isFinite(n)&&n>=min&&n<=max){update(n);draw()}else number.value=val});group.append(number,E('small',fmt(val,1)+suffix));controls.append(group)
}root.append(controls);
const rows=[];
for(const code of ["2580","2581","2514","2582","2560"]){
 const l=stock.rows.find(r=>r.kommun_code===code&&r.year===year&&r.kind==='light');
 const h=stock.rows.find(r=>r.kommun_code===code&&r.year===year&&r.kind==='heavy');
 const d=delivery.rows.find(r=>r.kommun_code===code&&r.year===year);
 if(!l||!h||!d||l.count===null||h.count===null||d.diesel_m3===null)continue;
 const vl=l.count*km[year].light*lightL/100*lightDiesel/100/1000;
 const vh=h.count*km[year].heavy*heavyL/100*heavyDiesel/100/1000;
 rows.push({name:l.kommun,light:l.count,heavy:h.count,model:vl+vh,del:d.diesel_m3});
}
if(!rows.length){root.append(E('p','Det finns ännu inga komplett matchade kommunvärden.'));return}
const table=E('table');table.style.cssText='width:100%;margin:16px 0;border-collapse:collapse';const head=E('thead'),hr=E('tr');['Kommun','Lätta','Tunga','Modell: lastbilsdiesel, m³','Leveranser till återförsäljare, m³','Leveranser / modell'].forEach(t=>hr.append(E('th',t)));head.append(hr);table.append(head);const body=E('tbody');
for(const r of rows){const tr=E('tr');[r.name,fmt(r.light),fmt(r.heavy),fmt(r.model),fmt(r.del),r.model?fmt(r.del/r.model,2):'–'].forEach(v=>{const cell=E('td',v);cell.style.padding='7px 5px';tr.append(cell)});body.append(tr)}table.append(body);const holder=E('div');holder.style.overflowX='auto';holder.append(table);root.append(holder);
const note=E('p','OBS: Kvoten jämför ALL återförsäljardiesel med bara SCENARIOBERÄKNAD lastbilsdiesel. Den är inte ett mått på nettotankning av besökande lastbilar eller transittrafik. Personbilar, bussar, entreprenadmaskiner och leveranser direkt till förbrukare saknas i nämnaren/jämförelsens täckning. Fordonen kan vara aktiva och tanka i andra kommuner eller utomlands. Riksgenomsnittliga körsträckor är inte kommunernas verkliga körning.');note.className='source-note';root.append(note);
const links=E('p');const a=E('a','Trafikanalys – körsträckor');a.href='https://www.trafa.se/vagtrafik/korstrackor/';a.target='_blank';a.rel='noopener noreferrer';const b=E('a','SCB – fordon i trafik');b.href=stock.url;b.target='_blank';b.rel='noopener noreferrer';links.append(a,E('span',' · '),b);root.append(links)
}
Promise.all([fetch('data/freight-truck-stock.json').then(r=>{if(!r.ok)throw Error('stock unavailable');return r.json()}),fetch('data/freight-diesel-reseller-deliveries.json').then(r=>{if(!r.ok)throw Error('diesel unavailable');return r.json()})]).then(([s,d])=>{if(s.status!=='source_data'||d.status!=='source_data')throw Error('not validated');stock=s;delivery=d;draw()}).catch(()=>{});draw()
})();