(()=>{
 const root=document.getElementById('gcmPassageAnalysis');if(!root)return;
 const area=document.getElementById('trafficArea');let data,dimension='types';
 const sv=n=>Number(n).toLocaleString('sv-SE');
 const make=(t,s)=>{const e=document.createElement(t);if(s!=null)e.textContent=s;return e};
 function render(){
  root.replaceChildren();root.append(make('h2','Gångpassager och överfarter över bilväg'));
  if(!data){root.append(make('p','Laddar passageklassificering…'));return}
  const m=data.municipalities.find(x=>x.name===area?.value)||data.municipalities[0];
  const lead=make('p','Registrerade GCM-passager i '+m.name+'. Välj passagetyp eller vilka trafikanter passagerna är avsedda för.');root.append(lead);
  const sel=make('select');
  [['types','Passagetyp'],['travelers','Trafikanttyp']].forEach(([val,label])=>{const opt=make('option',label);opt.value=val;sel.append(opt)});
  sel.value=dimension;sel.addEventListener('change',()=>{dimension=sel.value;render()});root.append(sel);
  const names=dimension==='types'?data.types:data.traveler_types;
  const values=m[dimension];const maximum=Math.max(1,...values);
  const group=make('div');group.style.cssText='display:grid;gap:12px;margin:20px 0';
  names.forEach((name,i)=>{const item=make('div');const title=make('div',name+' — '+sv(values[i]));const track=make('div');track.style.cssText='height:15px;background:#e6ecf2;border-radius:7px;overflow:hidden';const bar=make('div');bar.style.cssText='height:100%;width:'+((values[i]/maximum)*100).toFixed(1)+'%;background:#337e94;border-radius:7px';track.append(bar);item.append(title,track);group.append(item)});
  root.append(group);
  root.append(make('h3','Refuger vid GCM-passager'));
  root.append(make('p','Ja: '+sv(m.refuge.yes)+' · Nej: '+sv(m.refuge.no)+' · Okänt: '+sv(m.refuge.unknown)));
  const notes=make('p','Observera: Övergångsställe och cykelpassage är sammanslagna i vissa NVDB-kategorier. Filtervalen visar separata marginalfördelningar och är inte en korsklassificering. Antalen avser registrerade NVDB-objekt och inte faktiskt antal gående eller en komplett förteckning över spontana korsningsplatser.');notes.className='source-note';root.append(notes);
 }
 area?.addEventListener('change',render);
 fetch('data/nvdb-gcm-passages.json').then(x=>{if(!x.ok)throw Error('missing');return x.json()}).then(x=>{data=x;render()}).catch(()=>{root.textContent='GCM-passageuppgifterna kunde inte hämtas.'});
})();