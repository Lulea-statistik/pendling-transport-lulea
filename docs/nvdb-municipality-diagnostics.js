(()=>{
 const fmt=(n,d=0)=>Number(n).toLocaleString('sv-SE',{minimumFractionDigits:d,maximumFractionDigits:d});
 const root=document.getElementById('nvdbMunicipalityDiagnostics');
 if(!root)return;
 let data;
 const select=document.getElementById('trafficArea');
 const create=(tag,txt,cls)=>{const el=document.createElement(tag);if(txt!==undefined)el.textContent=txt;if(cls)el.className=cls;return el};
 const metric=(name,val,desc)=>{const a=create('article',undefined,'analysis-card');a.append(create('h3',name),create('strong',val),create('p',desc));return a};
 const render=()=>{
  if(!data)return;
  const current=data.municipalities.find(x=>x.name===select.value)||data.municipalities[0];
  root.replaceChildren();
  const head=create('div');head.append(create('h3','Preliminär NVDB-statistik – '+current.name),create('p','Källa: Lastkajen paket 10155 · GIS-urval med SCB RegSO 2025 · diagnostiska resultat från GitHub Actions.'));
  root.append(head);
  const cards=create('div',undefined,'analysis-grid');
  cards.append(
    metric('Hastighetsgräns 70 km/h',fmt(100*current.speed70_km/current.speed_km,1)+' %','Andel av summerad klippt längd i hastighetslagret ('+fmt(current.speed_km,0)+' km).'),
    metric('Längdvägt ÅDT',fmt(current.adt,0),'Fordon/dygn på registrerade trafiksträckor ('+fmt(current.adt_km,0)+' km).'),
    metric('Tung trafik, längdvägt ÅDT',fmt(current.adt_heavy,0),'Tunga fordon/dygn på samma registrerade sträckor.'),
    metric('GCM-passager',fmt(current.gcm_passages),'Registrerade objekt som geografiskt berör kommunen.'),
    metric('Cykelvägskategorier',fmt(current.cycle_km,1)+' km','Summerade klippta NVDB-linjeobjekt; ej avdubbelräknad unik längd.'),
    metric('Primär funktion: pendling',fmt(current.cycle_commute_km,1)+' km','Registrerad cykelvägskategori med pendling som primär funktion.')
  );root.append(cards);
  const title=create('h3','Jämförelse: längdvägt ÅDT, registrerade sträckor');
  const bars=create('div');bars.style.display='grid';bars.style.gap='10px';
  const max=Math.max(...data.municipalities.map(x=>x.adt));
  for(const m of data.municipalities){
   const line=create('div');
   const label=create('div',m.name+' – '+fmt(m.adt,0)+' fordon/dygn');
   const track=create('div');track.style.cssText='height:14px;background:var(--border,#e0e7ef);border-radius:7px;overflow:hidden';
   const fill=create('div');fill.style.cssText='height:100%;border-radius:7px;background:#4476aa;width:'+ (m.adt/max*100).toFixed(1)+'%';
   track.append(fill);line.append(label,track);bars.append(line);
  }
  root.append(title,bars);
  root.append(create('p','Metodbegränsning: ÅDT och väglängderna avser tillgängliga NVDB-objekt. Överlappande och riktningsuppdelade vägobjekt är ännu inte avdubbelräknade. Skillnader mellan kommunerna kan påverkas av mättäckning. Detta är inte ett mått på faktisk gång- eller cykeltrafik.','source-note'));
  const link=create('a','Visa källkörningen');link.href=data.run_url;link.target='_blank';link.rel='noopener noreferrer';root.append(link);
 };
 select?.addEventListener('change',render);
 fetch('data/nvdb-municipality-diagnostics.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(d=>{data=d;render()}).catch(()=>{root.textContent='NVDB-statistiken kunde inte läsas in.'});
})();