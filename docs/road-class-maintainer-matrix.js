(()=>{
 const root=document.getElementById('roadClassMaintainerMatrix');
 if(!root)return;
 let data=null,area='2580',mode='km';
 const fmt=(x,n=1)=>Number(x).toLocaleString('sv-SE',{minimumFractionDigits:n,maximumFractionDigits:n});
 const categories=[['statlig','Statlig','#4476ab'],['kommunal','Kommunal','#d3a347'],['enskild','Enskild','#7b9a8f'],['okand','Okänd','#9ca3af']];
 const el=(name,text)=>{let x=document.createElement(name);if(text!==undefined)x.textContent=text;return x};
 function render(){
  root.replaceChildren();root.append(el('h2','Funktionell vägklass × väghållare – samma bilvägnät'));
  if(!data){root.append(el('p','Väntar på kvalitetssäkrad klassificering från nästa GitHub-körning.'));return}
  const controls=el('div');controls.className='controls';
  const geo=el('select');
  [['FA','Luleå FA-region'],...Object.entries(data.municipalities).map(([code,m])=>[code,m.name])].forEach(([id,label])=>{const o=el('option',label);o.value=id;geo.append(o)});
  geo.value=area;geo.addEventListener('change',()=>{area=geo.value;render()});
  let label=el('label','Geografi ');label.append(geo);controls.append(label);
  const opt=el('select');
  [['km','Kilometer'],['percent','Andel inom vägklass (%)']].forEach(([v,label])=>{const o=el('option',label);o.value=v;opt.append(o)});
  opt.value=mode;opt.addEventListener('change',()=>{mode=opt.value;render()});
  label=el('label','Visa ');label.append(opt);controls.append(label);root.append(controls);
  const selected=area==='FA'?Object.values(data.municipalities):[data.municipalities[area]].filter(Boolean);
  const sums={};
  let total=0,unmatched=0;
  for(const m of selected){
   total+=m.car_network_km;unmatched+=m.unmatched_km;
   for(const [cls,r] of Object.entries(m.classes)){
    if(!sums[cls])sums[cls]={total_km:0,km:{}};
    sums[cls].total_km+=r.total_km;
    for(const [cat,value] of Object.entries(r.km))sums[cls].km[cat]=(sums[cls].km[cat]||0)+value;
   }
  }
  root.append(el('h3',fmt(total,0)+' km bilvägnät · '+fmt((1-unmatched/total)*100,2)+' % med entydig väghållare'));
  const legend=el('p',categories.map(x=>x[1]).join(' · '));legend.className='source-note';root.append(legend);
  const entries=el('div');entries.style.cssText='display:grid;gap:15px;margin-top:14px';
  for(let cls=0;cls<=9;cls++){
   const value=sums[String(cls)];if(!value||value.total_km===0)continue;
   const cell=el('div');cell.append(el('div','Klass '+cls+' — '+fmt(value.total_km,1)+' km'));
   const bar=el('div');bar.style.cssText='display:flex;height:20px;border-radius:5px;overflow:hidden;background:#e5e7eb';
   for(const [key,title,color] of categories){
    const km=value.km[key]||0;if(km<=0)continue;
    const piece=el('div');piece.style.cssText='width:'+(100*km/value.total_km).toFixed(3)+'%;background:'+color;piece.title=title+': '+fmt(km,1)+' km ('+fmt(100*km/value.total_km,1)+' %)';
    bar.append(piece);
   }
   cell.append(bar);
   const detail=el('p',categories.map(([key,title])=>title+': '+fmt(mode==='km'?(value.km[key]||0):100*(value.km[key]||0)/value.total_km,1)+(mode==='km'?' km':' %')).join(' · '));
   detail.className='source-note';cell.append(detail);entries.append(cell);
  }root.append(entries);
  const caveat=el('p',data.method+' '+data.caveat);caveat.className='source-note';root.append(caveat);
 }
 fetch('data/nvdb-road-class-maintainer.json').then(r=>{if(!r.ok)throw Error(String(r.status));return r.json()}).then(d=>{if(d.status!=='preliminary_validated')throw Error('Unvalidated');data=d;render()}).catch(()=>render());
 render();
})();