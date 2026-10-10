(()=>{
 const root=document.getElementById('roadStructureAnalysis');if(!root)return;
 let data=null,metric='road_class',area='FA';
 const fmt=(v,d=0)=>Number(v).toLocaleString('sv-SE',{minimumFractionDigits:d,maximumFractionDigits:d});
 const node=(tag,txt)=>{const e=document.createElement(tag);if(txt!==undefined)e.textContent=txt;return e};
 const allCodes=['2580','2582','2581','2560','2514'];
 function render(){
  root.replaceChildren();root.append(node('h2','Vägnätets struktur och funktion'));
  if(!data){root.append(node('p','Laddar NVDB:s vägstruktur…'));return}
  const controls=node('div');controls.className='controls';
  const muni=node('label','Geografi '),geo=node('select');
  [['FA','Luleå FA-region (summa kommuner)'],...data.municipalities.map(m=>[m.code,m.name])].forEach(([v,t])=>{const o=node('option',t);o.value=v;geo.append(o)});geo.value=area;geo.addEventListener('change',()=>{area=geo.value;render()});muni.append(geo);controls.append(muni);
  const lab=node('label','Indelning '),select=node('select');
  [['road_class','Funktionell vägklass (bilnät)'],['maintainer','Väghållare (alla nät)']].forEach(([v,t])=>{const o=node('option',t);o.value=v;select.append(o)});select.value=metric;select.addEventListener('change',()=>{metric=select.value;render()});lab.append(select);controls.append(lab);root.append(controls);
  const selected=area==='FA'?data.municipalities:[data.municipalities.find(x=>x.code===area)].filter(Boolean);
  const vals={};
  for(const m of selected){for(const [k,v] of Object.entries(m[metric])) vals[k]=(vals[k]||0)+v}
  const keys=metric==='road_class'?Array.from({length:10},(_,i)=>String(i)):['statlig','kommunal','enskild'];
  const total=selected.reduce((s,m)=>s+(metric==='road_class'?m.car_km:m.all_network_km),0);
  root.append(node('h3',fmt(total,0)+' km '+(metric==='road_class'?'bilvägnät':'registrerat väg-, gång- och cykelnät')));
  const max=Math.max(1,...keys.map(k=>vals[k]||0));
  const chart=node('div');chart.style.cssText='display:grid;gap:10px;margin:16px 0';
  keys.forEach(k=>{
   const val=vals[k]||0,entry=node('div');
   const label=metric==='road_class'?'Klass '+k:k.charAt(0).toUpperCase()+k.slice(1);
   entry.append(node('div',label+' — '+fmt(val,1)+' km ('+fmt(total?val/total*100:0,1)+' %)'));
   const track=node('div');track.style.cssText='height:16px;border-radius:8px;background:#e6ecf2;overflow:hidden';
   const fill=node('div');fill.style.cssText='height:100%;width:'+(val/max*100).toFixed(2)+'%;border-radius:8px;background:'+(metric==='maintainer'?{statlig:'#4d79a5',kommunal:'#d4a245',enskild:'#8c9cab'}[k]:'#4d79a5');track.append(fill);entry.append(track);chart.append(entry)
  });root.append(chart);
  const warning=node('p',metric==='road_class'?'Funktionell vägklass är NVDB:s numeriska klass 0–9, inte en egen indelning i huvudväg/lokalgata. Måttet gäller bilnätet.':'Väghållaruppgifter gäller samtliga registrerade nät (bil, gång, cykel), inte enbart bilvägar. Därför kan dessa värden inte användas för att uppskatta bilvägarnas fördelning efter väghållare.');warning.className='source-note';root.append(warning);
  const note=node('p','Preliminära GIS-längder: sammanfallande linjegeometrier är sammanslagna inom klass, men kvarvarande skillnader i nätdefinition och körbanor behöver granskas. FA-totalen är summan av de fem kommunernas längder. Källa: NVDB Lastkajen, körning '+data.run_id+'.');note.className='source-note';root.append(note);
 }
 fetch('data/nvdb-road-structure.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(j=>{data=j;render()}).catch(()=>{root.textContent='Vägstrukturdata kunde inte hämtas.'});
 render();
})();