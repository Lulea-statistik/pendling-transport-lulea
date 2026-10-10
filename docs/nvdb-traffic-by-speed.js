(()=>{
 const el=document.getElementById('nvdbTrafficSpeed');
 if(!el)return;
 const area=document.getElementById('trafficArea');
 const fmt=(v,d=0)=>Number(v).toLocaleString('sv-SE',{maximumFractionDigits:d,minimumFractionDigits:d});
 let data=null;
 let measure='traffic_exposure_vehicle_km_per_day';
 let maintainer='all';
 function render(){
  el.replaceChildren();
  const h=document.createElement('h2');h.textContent='Trafikflöden efter hastighetsgräns';el.append(h);
  if(!data){const p=document.createElement('p');p.textContent='Analysen av trafiksträckornas hastighetsgränser väntar på kvalitetskontroll. Inga värden visas innan GIS-samkörningen har verifierats.';el.append(p);return}
  const row=data.municipalities?.[Object.keys(data.municipalities).find(k=>data.municipalities[k].name===area?.value)];
  if(!row){el.append(document.createTextNode('Inga data för vald kommun.'));return}
  const control=document.createElement('select');
  [['traffic_exposure_vehicle_km_per_day','Trafikexponering (fordonskm/dygn)'],['length_weighted_adt','Genomsnittligt ÅDT (fordon/dygn)']].forEach(([val,label])=>{const o=document.createElement('option');o.value=val;o.textContent=label;control.append(o)});
  control.value=measure;control.addEventListener('change',()=>{measure=control.value;render()});el.append(control);
  const managerSelect=document.createElement('select');
  [['all','Alla väghållare'],['statlig','Statlig väg'],['kommunal','Kommunal väg'],['enskild','Enskild väg']].forEach(([val,label])=>{const o=document.createElement('option');o.value=val;o.textContent=label;managerSelect.append(o)});
  managerSelect.value=maintainer;
  managerSelect.disabled=!row.manager_by_speed;
  managerSelect.title=managerSelect.disabled?'Väntar på verifierad samkörning med NVDB Väghållare':'Filtrera efter väghållarkategori';
  managerSelect.addEventListener('change',()=>{maintainer=managerSelect.value;render()});
  el.append(managerSelect);
  if(managerSelect.disabled){const wait=document.createElement('p');wait.className='source-note';wait.textContent='Väghållaruppdelningen beräknas i nästa GIS-körning. Tills dess visas samtliga väghållare tillsammans.';el.append(wait)}
  const info=document.createElement('p');info.textContent='Preliminär GIS-samkörning mellan NVDB:s trafikmängder och ordinarie hastighetsgräns. Inte särskilt personbilar: ÅDT avser samtliga fordon. Trafikdata i detta uttag omfattar endast statliga vägar; kommunala och enskilda vägar saknar ÅDT-underlag.';el.append(info);
  const unavailable=(maintainer==='kommunal'||maintainer==='enskild') && !Object.values(row.manager_by_speed||{}).some(categories=>categories[maintainer]);
  if(unavailable){const msg=document.createElement('p');msg.className='source-note';msg.textContent='ÅDT-uppgifter saknas för '+(maintainer==='kommunal'?'kommunala':'enskilda')+' vägar i detta NVDB-uttag. Detta betyder inte att trafikflödet är noll. Välj Statlig väg eller Alla väghållare för att se de registrerade värdena.';el.append(msg);return;}
  const values=(row.speed_classes||[]).map(x=>{
    if(maintainer==='all'||!row.manager_by_speed)return x;
    const match=row.manager_by_speed[String(x.speed_kmh)]?.[maintainer];
    return {...x,[measure]:match?.[measure]||0,covered_length_km:match?.covered_length_km||0};
  });
  const max=Math.max(1,...values.map(x=>Number(x[measure])||0));
  const bars=document.createElement('div');bars.style.cssText='display:grid;gap:12px;margin-top:16px';
  values.forEach(x=>{
   const entry=document.createElement('div');
   const txt=document.createElement('div');txt.textContent=x.speed_kmh+' km/h — '+fmt(x[measure]||0,measure==='length_weighted_adt'?0:0)+' ('+fmt(x.covered_length_km,1)+' km med giltig matchning)';
   const bar=document.createElement('div');bar.style.cssText='height:16px;border-radius:8px;background:#e5ebf1;overflow:hidden';
   const fill=document.createElement('div');fill.style.cssText='height:100%;width:'+((Number(x[measure])||0)/max*100).toFixed(1)+'%;background:#4372a8;border-radius:8px';
   bar.append(fill);entry.append(txt,bar);bars.append(entry);
  });el.append(bars);
  if(row.manager_by_speed){
    const cover=document.createElement('p');cover.className='source-note';
    cover.textContent='Väghållarkoppling: '+fmt(row.manager_unmatched_km||0,1)+' km utan match, '+fmt(row.manager_ambiguous_km||0,1)+' km med motstridiga väghållaruppgifter.';
    el.append(cover);
  }
  const note=document.createElement('p');note.className='source-note';note.textContent='Kvalitet: '+fmt(row.matched_length_km,1)+' km matchad trafiksträcka, '+fmt(row.without_speed_match_km,1)+' km utan match och '+fmt(row.ambiguous_speed_length_km,1)+' km med motstridiga hastighetsgränser. Överlappande trafikobjekt är ännu inte avdubbelräknade.';el.append(note);
 }
 area?.addEventListener('change',render);
 fetch('data/nvdb-traffic-by-speed.json').then(r=>{if(!r.ok)throw Error('not published');return r.json()}).then(j=>{if(j.status!=='preliminary'||!j.municipalities)throw Error('invalid');data=j;render()}).catch(()=>render());
 render();
})();