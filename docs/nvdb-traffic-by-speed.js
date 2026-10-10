(()=>{
 const el=document.getElementById('nvdbTrafficSpeed');
 if(!el)return;
 const area=document.getElementById('trafficArea');
 const fmt=(v,d=0)=>Number(v).toLocaleString('sv-SE',{maximumFractionDigits:d,minimumFractionDigits:d});
 let data=null;
 let measure='traffic_exposure_vehicle_km_per_day';
 function render(){
  el.replaceChildren();
  const h=document.createElement('h2');h.textContent='Trafikflöden efter hastighetsgräns';el.append(h);
  if(!data){const p=document.createElement('p');p.textContent='Analysen av trafiksträckornas hastighetsgränser väntar på kvalitetskontroll. Inga värden visas innan GIS-samkörningen har verifierats.';el.append(p);return}
  const row=data.municipalities?.[Object.keys(data.municipalities).find(k=>data.municipalities[k].name===area?.value)];
  if(!row){el.append(document.createTextNode('Inga data för vald kommun.'));return}
  const control=document.createElement('select');
  [['traffic_exposure_vehicle_km_per_day','Trafikexponering (fordonskm/dygn)'],['length_weighted_adt','Genomsnittligt ÅDT (fordon/dygn)']].forEach(([val,label])=>{const o=document.createElement('option');o.value=val;o.textContent=label;control.append(o)});
  control.value=measure;control.addEventListener('change',()=>{measure=control.value;render()});el.append(control);
  const info=document.createElement('p');info.textContent='Preliminär GIS-samkörning mellan NVDB:s trafikmängder och ordinarie hastighetsgräns. Inte särskilt personbilar: ÅDT avser samtliga fordon.';el.append(info);
  const values=row.speed_classes||[],max=Math.max(1,...values.map(x=>Number(x[measure])||0));
  const bars=document.createElement('div');bars.style.cssText='display:grid;gap:12px;margin-top:16px';
  values.forEach(x=>{
   const entry=document.createElement('div');
   const txt=document.createElement('div');txt.textContent=x.speed_kmh+' km/h — '+fmt(x[measure]||0,measure==='length_weighted_adt'?0:0)+' ('+fmt(x.covered_length_km,1)+' km med giltig matchning)';
   const bar=document.createElement('div');bar.style.cssText='height:16px;border-radius:8px;background:#e5ebf1;overflow:hidden';
   const fill=document.createElement('div');fill.style.cssText='height:100%;width:'+((Number(x[measure])||0)/max*100).toFixed(1)+'%;background:#4372a8;border-radius:8px';
   bar.append(fill);entry.append(txt,bar);bars.append(entry);
  });el.append(bars);
  const note=document.createElement('p');note.className='source-note';note.textContent='Kvalitet: '+fmt(row.matched_length_km,1)+' km matchad trafiksträcka, '+fmt(row.without_speed_match_km,1)+' km utan match och '+fmt(row.ambiguous_speed_length_km,1)+' km med motstridiga hastighetsgränser. Överlappande trafikobjekt är ännu inte avdubbelräknade.';el.append(note);
 }
 area?.addEventListener('change',render);
 fetch('data/nvdb-traffic-by-speed.json').then(r=>{if(!r.ok)throw Error('not published');return r.json()}).then(j=>{if(j.status!=='preliminary'||!j.municipalities)throw Error('invalid');data=j;render()}).catch(()=>render());
 render();
})();