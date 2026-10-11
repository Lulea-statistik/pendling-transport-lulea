(()=>{
 const root=document.getElementById('roadWidthByClass');if(!root)return;
 const el=(tag,value)=>{const x=document.createElement(tag);if(value!==undefined)x.textContent=value;return x};
 const fmt=(v,n=1)=>Number(v).toLocaleString('sv-SE',{minimumFractionDigits:n,maximumFractionDigits:n});
 const bands=[['<4 m','#587ea3'],['4–<6 m','#789eae'],['6–<8 m','#9fb596'],['8–<10 m','#d9ac65'],['≥10 m','#bc8058']];
 let data,area='2580',mode='share';
 function render(){
  root.replaceChildren();root.append(el('h2','Vägbredd inom funktionell vägklass'));
  if(!data){root.append(el('p','Väntar på ny analyskörning och kvalitetskontrollerad datafil.'));return}
  const controls=el('div');controls.className='controls';
  const m=el('select');[['FA','Luleå FA-region'],...Object.entries(data.municipalities).map(([k,v])=>[k,v.name])].forEach(([k,v])=>{const option=el('option',v);option.value=k;m.append(option)});m.value=area;m.addEventListener('change',()=>{area=m.value;render()});let l=el('label','Geografi ');l.append(m);controls.append(l);
  const select=el('select');[['share','Andel av dokumenterad väglängd (%)'],['km','Dokumenterad längd (km)']].forEach(([k,v])=>{const option=el('option',v);option.value=k;select.append(option)});select.value=mode;select.addEventListener('change',()=>{mode=select.value;render()});l=el('label','Mått ');l.append(select);controls.append(l);root.append(controls);
  const chosen=area==='FA'?Object.values(data.municipalities):[data.municipalities[area]].filter(Boolean);
  const classes={};
  for(const town of chosen)for(const [k,item] of Object.entries(town.classes)){
   const v=classes[k]||(classes[k]={road_km:0,known_km:0,bands_km:{}});
   v.road_km+=item.road_km;v.known_km+=item.known_km;
   for(const [b,num] of Object.entries(item.bands_km))v.bands_km[b]=(v.bands_km[b]||0)+num;
  }
  const totalKnown=Object.values(classes).reduce((s,x)=>s+x.known_km,0);
  const totalRoad=Object.values(classes).reduce((s,x)=>s+x.road_km,0);
  root.append(el('p','Dokumenterad vägbredd: '+fmt(totalKnown,0)+' av '+fmt(totalRoad,0)+' km bilvägnät ('+fmt(totalKnown/totalRoad*100)+' %).'));
  const list=el('div');list.style.cssText='display:grid;gap:16px;margin:15px 0';
  for(let i=0;i<=9;i++){
   const v=classes[String(i)];if(!v||v.road_km===0)continue;
   const item=el('div');const coverage=v.known_km/v.road_km*100;
   item.append(el('div','Vägklass '+i+' · '+fmt(v.known_km)+' km dokumenterade · täckning '+fmt(coverage)+' %'));
   if(v.known_km>0){
    const track=el('div');track.style.cssText='display:flex;overflow:hidden;border-radius:6px;height:20px;background:#e5e7eb;margin:6px 0';
    for(const [band,color] of bands){
     const n=v.bands_km[band]||0;if(!n)continue;
     const segment=el('div');segment.style.cssText='height:100%;width:'+(100*n/v.known_km).toFixed(3)+'%;background:'+color;
     segment.title=band+': '+fmt(n)+' km; '+fmt(100*n/v.known_km)+' % av dokumenterade km';track.append(segment);
    }item.append(track);
    const detail=el('p',bands.map(([b])=>b+': '+fmt(mode==='km'?(v.bands_km[b]||0):100*(v.bands_km[b]||0)/v.known_km)+(mode==='km'?' km':' %')).join(' · '));detail.className='source-note';item.append(detail);
   }else item.append(el('p','Ingen dokumenterad bredd.'));
   list.append(item)
  }root.append(list);
  const note=el('p','Staplarna summerar till 100 % av den DOKUMENTERADE bredden inom respektive vägklass, inte 100 % av hela klassens vägnät. Jämför alltid med täckningsgraden. Värden från NVDB med exakt geometriöverlapp; ingen imputering. '+data.limitations);
  note.className='source-note';root.append(note);
 }
 fetch('data/nvdb-road-width-by-class.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(v=>{if(v.status!=='validated_preliminary')throw Error('Not validated');data=v;render()}).catch(()=>{root.append(el('p','Den verifierade datafilen är ännu inte publicerad.'))});render()
})();