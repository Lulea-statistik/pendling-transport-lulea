(()=>{
 const root=document.getElementById('gcmSpeedProximity');if(!root)return;
 const municipal=document.getElementById('trafficArea');
 let data, group='plan',threshold=70;
 const groups={plan:['Annan ordnad passage i plan','Övergångsställe/cykelpassage i plan','Signalreglerad passage i plan'],grade:['Underfart','Överfart (bro)'],all:[]};
 const fmt=n=>Number(n).toLocaleString('sv-SE');
 const node=(tag,text)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=text;return x};
 function render(){
  root.replaceChildren();root.append(node('h2','GCM-passager och närliggande hastighetsgränser'));
  if(!data){root.append(node('p','Laddar GIS-analys…'));return}
  const row=Object.values(data.municipalities).find(x=>x.name===municipal?.value)||Object.values(data.municipalities)[0];
  const description=node('p','En geografisk närhetsanalys, inte uppmätt trafiksäkerhetsklass. Vägens hastighet kan inte alltid fastställas säkert enbart utifrån närhet.');
  root.append(description);
  const controls=node('div');controls.className='controls';
  const typ=node('select');[['plan','Passager i plan'],['grade','Broar och tunnlar'],['all','Alla passager']].forEach(([v,l])=>{const o=node('option',l);o.value=v;typ.append(o)});typ.value=group;typ.addEventListener('change',()=>{group=typ.value;render()});controls.append(typ);
  const speed=node('select');[[30,'30 km/h eller högre'],[50,'50 km/h eller högre'],[70,'70 km/h eller högre'],[90,'90 km/h eller högre']].forEach(([v,l])=>{const o=node('option',l);o.value=v;speed.append(o)});speed.value=String(threshold);speed.addEventListener('change',()=>{threshold=Number(speed.value);render()});controls.append(speed);
  root.append(controls);
  const selected=group==='all'?data.types:groups[group];
  const totals=selected.map(type=>({type,count:Object.entries(row.speed_by_type[type]||{}).reduce((s,[k,v])=>s+(Number(k)>=threshold?Number(v):0),0)}));
  const sum=totals.reduce((s,x)=>s+x.count,0);
  const title=node('h3',fmt(sum)+' registrerade passager nära vägar med minst '+threshold+' km/h');root.append(title);
  const chart=node('div');chart.style.cssText='display:grid;gap:12px;margin:14px 0';
  const max=Math.max(1,...totals.map(x=>x.count));
  totals.forEach(({type,count})=>{const item=node('div');item.append(node('div',type+' — '+fmt(count)));const track=node('div');track.style.cssText='height:16px;background:#e5ebf1;border-radius:8px;overflow:hidden';const bar=node('div');bar.style.cssText='height:100%;background:#467aab;width:'+(count/max*100).toFixed(1)+'%;border-radius:8px';track.append(bar);item.append(track);chart.append(item)});
  root.append(chart);
  const coverage=node('p','Matchning: '+fmt(row.matches)+' av '+fmt(row.passages)+' passager. '+fmt(row.unmatched)+' utan hastighetsmatch och '+fmt(row.ambiguous)+' med motstridiga hastighetsklasser.');coverage.className='source-note';root.append(coverage);
  const warning=node('p','Viktigt: Passager i plan kan ligga nära en väg med hög hastighetsgräns utan att faktiskt korsa just den vägen. Underfarter och broar är planskilda. Ingen olycksrisk eller uppmätt säkerhetsklass kan utläsas ur detta diagram.');warning.className='source-note';root.append(warning);
  const link=node('a','Visa GIS-körningen');link.href='https://github.com/Lulea-statistik/pendling-transport-lulea/actions/runs/'+data.run_id;link.target='_blank';link.rel='noopener noreferrer';root.append(link);
 }
 municipal?.addEventListener('change',render);
 fetch('data/gcm-crossing-speed-qa.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(x=>{data=x;render()}).catch(()=>{root.textContent='Kunde inte ladda analysen av passager och hastigheter.'});
 render();
})();