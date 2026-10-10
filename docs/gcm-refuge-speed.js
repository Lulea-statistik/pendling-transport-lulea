(()=>{
 const root=document.getElementById('gcmRefugeSpeed');if(!root)return;
 const area=document.getElementById('trafficArea');
 const fmt=n=>Number(n).toLocaleString('sv-SE');
 let data,threshold=70;
 function draw(){
  root.replaceChildren();
  const title=document.createElement('h2');title.textContent='Refuger vid passager i plan';root.append(title);
  if(!data){const p=document.createElement('p');p.textContent='Laddar kvalitetssäkrad korsklassificering…';root.append(p);return}
  const row=Object.values(data.municipalities).find(x=>x.name===area?.value)||Object.values(data.municipalities)[0];
  const intro=document.createElement('p');intro.textContent='Registrerade passager i plan efter refugstatus och hastighetsgräns på närmaste väg (inte nödvändigtvis den korsade körbanan).';root.append(intro);
  const label=document.createElement('label');label.textContent='Lägsta hastighetsgräns: ';
  const select=document.createElement('select');
  [[30,'30 km/h'],[50,'50 km/h'],[70,'70 km/h'],[90,'90 km/h']].forEach(([v,text])=>{let o=document.createElement('option');o.value=v;o.textContent=text;select.append(o)});
  select.value=threshold;select.addEventListener('change',()=>{threshold=Number(select.value);draw()});label.append(select);root.append(label);
  const categories=[['ja','Med refug','#33827b'],['nej','Utan refug','#b95f53'],['okänt','Okänt','#8797a7']];
  const results=categories.map(([key,title,color])=>({title,color,count:Object.entries(row.at_grade_by_refuge_and_speed[key]||{}).reduce((sum,[speed,n])=>sum+(Number(speed)>=threshold?Number(n):0),0)}));
  const total=results.reduce((sum,x)=>sum+x.count,0);
  let totalNode=document.createElement('h3');totalNode.textContent=fmt(total)+' passager i plan nära vägar med minst '+threshold+' km/h';root.append(totalNode);
  const max=Math.max(1,...results.map(x=>x.count));const chart=document.createElement('div');chart.style.cssText='display:grid;gap:12px;margin-top:12px';
  results.forEach(x=>{const entry=document.createElement('div');const text=document.createElement('div');text.textContent=x.title+' — '+fmt(x.count);const back=document.createElement('div');back.style.cssText='height:16px;background:#e6ebf1;border-radius:8px;overflow:hidden';const bar=document.createElement('div');bar.style.cssText='height:100%;width:'+((x.count/max)*100).toFixed(1)+'%;background:'+x.color;back.append(bar);entry.append(text,back);chart.append(entry)});root.append(chart);
  const note=document.createElement('p');note.className='source-note';note.textContent='Preliminär närhetsanalys, inte säkerhetsklass eller olycksrisk. Okänt är inte samma sak som nej. GCM-passager kan även gälla cykeltrafik, och passagen behöver inte korsa den hastighetsmatchade körbanan.';root.append(note);
  const link=document.createElement('a');link.href='https://github.com/Lulea-statistik/pendling-transport-lulea/actions/runs/'+data.run_id;link.textContent='Visa beräkningskörningen';link.target='_blank';link.rel='noopener noreferrer';root.append(link);
 }
 area?.addEventListener('change',draw);
 fetch('data/gcm-refuge-speed-qa.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(x=>{data=x;draw()}).catch(()=>{root.textContent='Kunde inte läsa refuguppdelningen.'});
 draw();
})();