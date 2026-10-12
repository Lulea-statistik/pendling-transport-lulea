(()=>{
const root=document.getElementById('freightHazmatMap');if(!root)return;
const message=document.createElement('p');message.textContent='Laddar kontrollerade väggeometrier från kommunens öppna karttjänst…';root.append(message);
if(typeof L==='undefined'){message.textContent='Kartbiblioteket kunde inte laddas.';return}
fetch('data/lulea-hazardous-goods-roads.geojson',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('GeoJSON unavailable');return r.json()}).then(data=>{
if(data.type!=='FeatureCollection'||!Array.isArray(data.features)||data.features.length!==510)throw Error('Unexpected feature count');
root.replaceChildren();
const heading=document.createElement('h2');heading.textContent='Transportleder för farligt gods';root.append(heading);
const intro=document.createElement('p');intro.textContent='Kommunens rekommenderade vägar för farligt gods. Lager med förbudsobjekt visas separat med särskild reservation eftersom föreskrifterna inte har granskats juridiskt.';root.append(intro);
const legend=document.createElement('div');legend.style.cssText='display:flex;flex-wrap:wrap;gap:16px;margin:10px 0 14px';
const categories=[['Primär rekommenderad väg','#b91c1c'],['Sekundär rekommenderad väg','#eab308'],['Förbudsobjekt – ej juridiskt verifierade','#475569'],['Väghållare – kommunal','#2563eb'],['Väghållare – statlig','#15803d'],['Väghållare – enskild','#6b7280'],['Allmänna parkeringsytor','#7c3aed'],['Laddplatser','#0891b2']];
for(const [label,color] of categories){const item=document.createElement('label');item.style.cssText='display:inline-flex;align-items:center;gap:8px;cursor:pointer;font-size:14px;min-height:30px;flex-wrap:nowrap';const check=document.createElement('input');check.type='checkbox';check.checked=categories.indexOf(categories.find(x=>x[0]===label))<3;check.dataset.category=label;check.style.cssText='width:16px;height:16px;accent-color:'+color+';margin:0;flex:none';const swatch=document.createElement('span');swatch.style.cssText='display:inline-block;width:22px;border-top:4px solid '+color;item.append(check,swatch,document.createTextNode(label));legend.append(item)}
root.append(legend);
const status=document.createElement('p');status.className='source-note';status.textContent='Kartdata: 429 primära, 73 sekundära rekommenderade vägobjekt och 8 preliminära förbudsobjekt. Klicka på linjerna för detaljer. Du kan zooma med musens rullhjul.';root.append(status);
const mapDiv=document.createElement('div');mapDiv.style.cssText='height:480px;min-height:310px;width:100%;border-radius:10px;overflow:hidden';root.append(mapDiv);
const map=L.map(mapDiv,{scrollWheelZoom:true,zoomControl:true}).setView([65.58,22.15],10);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'© OpenStreetMap-bidragsgivare'}).addTo(map);
const types={
'Primär rekommenderad väg':{color:'#b91c1c',weight:4},
'Sekundär rekommenderad väg':{color:'#eab308',weight:4},
'Förbudsobjekt – ej juridiskt verifierade':{color:'#475569',weight:4,dashArray:'6,5'}};
function cat(f){const p=f.properties||{};if(p.layer==='restricted')return 'Förbudsobjekt – ej juridiskt verifierade';return p.classification==='rekommenderad sekundär väg'?'Sekundär rekommenderad väg':'Primär rekommenderad väg'}
const layers={};for(const [name,style] of Object.entries(types)){layers[name]=L.geoJSON(data,{filter:cat2=>cat(cat2)===name,style:()=>style,onEachFeature:(f,layer)=>{const p=f.properties||{};const content=document.createElement('div');for(const [k,v] of [['Kategori',name],['Objekt-ID',p.objectid],['Giltig från',p.valid_from||'Uppgift saknas'],['Giltig till',p.valid_to||'Uppgift saknas']]){const line=document.createElement('div');line.textContent=k+': '+v;content.append(line)}layer.bindPopup(content)}}).addTo(map)}
const bounds=L.geoJSON(data).getBounds();
const page=root.closest('.page');
function repairMapView(){
 if(page && !page.classList.contains('active'))return;
 if(!mapDiv.isConnected||mapDiv.clientWidth<200)return;
 requestAnimationFrame(()=>requestAnimationFrame(()=>{
   map.invalidateSize({pan:false,animate:false});
   if(bounds.isValid())map.fitBounds(bounds.pad(0.04),{maxZoom:12,animate:false});
 }));
}
if(page){
 const visibilityObserver=new MutationObserver(()=>{if(page.classList.contains('active'))repairMapView()});
 visibilityObserver.observe(page,{attributes:true,attributeFilter:['class']});
}
const resizeObserver=typeof ResizeObserver==='undefined'?null:new ResizeObserver(()=>repairMapView());
if(resizeObserver)resizeObserver.observe(mapDiv);
if(!page||page.classList.contains('active'))repairMapView();
const extra={
'Väghållare – kommunal':{id:35,group:'VAGHALLARE',value:'kommunal',color:'#2563eb'},
'Väghållare – statlig':{id:35,group:'VAGHALLARE',value:'statlig',color:'#15803d'},
'Väghållare – enskild':{id:35,group:'VAGHALLARE',value:'enskild',color:'#6b7280'},
'Allmänna parkeringsytor':{id:5,color:'#7c3aed'},
'Laddplatser':{id:2,color:'#0891b2'}};
const extraLayers={};let pending=0;let extraLoadSerial=0;
const service='https://kartportal.lulea.se/server/rest/services/samhalle_och_gator/MapServer/';
function setExtraStatus(text){status.textContent='Kartdata: 429 primära, 73 sekundära rekommenderade vägobjekt och 8 preliminära förbudsobjekt. '+text}
async function queryArc(layerId,parameters){
 const params=new URLSearchParams({f:'json',where:'1=1',outFields:'*',returnGeometry:'true',outSR:'4326',...parameters});
 const response=await fetch(service+layerId+'/query?'+params.toString());
 if(!response.ok)throw Error('HTTP '+response.status);
 const data=await response.json();if(data.error)throw Error(data.error.message||'ArcGIS-fråga misslyckades');
 return data;
}
function esriGeometry(g){
 if(!g)return null;
 if(g.x!==undefined&&g.y!==undefined)return {type:'Point',coordinates:[g.x,g.y]};
 if(g.paths)return {type:'MultiLineString',coordinates:g.paths};
 if(g.rings)return {type:'MultiPolygon',coordinates:g.rings.map(r=>[r])};
 return null;
}
async function refreshExtras(){
 const selected=Object.keys(extra).filter(n=>legend.querySelector('input[data-category="'+n+'"]').checked);
 for(const name of Object.keys(extraLayers)){map.removeLayer(extraLayers[name]);delete extraLayers[name]}
 if(!selected.length){setExtraStatus('Övriga lager är avstängda.');return}
 if(map.getZoom()<11){setExtraStatus('Zooma in till nivå 11 eller mer för kommunala detaljlager.');return}
 const serial=++extraLoadSerial,b=map.getBounds();
 const envelope=JSON.stringify({xmin:b.getWest(),ymin:b.getSouth(),xmax:b.getEast(),ymax:b.getNorth(),spatialReference:{wkid:4326}});
 const groups=new Map();
 for(const name of selected){const obj=extra[name];const key=obj.id+'|'+(obj.value||'');if(!groups.has(key))groups.set(key,[]);groups.get(key).push(name)}
 setExtraStatus('Hämtar kommunala lager för synligt kartutsnitt…');
 let shown=0;let truncated=false;
 for(const names of groups.values()){
   if(serial!==extraLoadSerial)return;
   const cfg=extra[names[0]];
   try{
     const data=await queryArc(cfg.id,{where:cfg.value?"VAGHALLARE='"+cfg.value+"'":'1=1',
       geometry:envelope,geometryType:'esriGeometryEnvelope',inSR:'4326',
       spatialRel:'esriSpatialRelIntersects',resultRecordCount:'1000'});
     if(serial!==extraLoadSerial)return;
     if(data.exceededTransferLimit||data.features?.length>=1000)truncated=true;
     const features=(data.features||[]).map(f=>({type:'Feature',properties:f.attributes||{},geometry:esriGeometry(f.geometry)})).filter(f=>f.geometry);
     for(const name of names){
       const layer=L.geoJSON({type:'FeatureCollection',features},{
         style:()=>({color:extra[name].color,weight:3,fillOpacity:.22}),
         pointToLayer:(feature,latlng)=>L.circleMarker(latlng,{radius:6,color:extra[name].color,fillOpacity:.75}),
         onEachFeature:(feature,part)=>{
           const props=feature.properties;
           const panel=document.createElement('div');
           const title=document.createElement('strong');title.textContent=name;panel.append(title);
           for(const field of ['VAGHALLARE','NAMN','ADRESS','TYP','ANTALPL','GILTIG_FROM','GILTIG_TOM','OBJECTID']){
             if(props[field]===undefined||props[field]===null)continue;
             const row=document.createElement('div');row.textContent=field+': '+props[field];panel.append(row)}
           part.bindPopup(panel)
         }});
       extraLayers[name]=layer;layer.addTo(map)
     }
     shown+=features.length
   }catch(err){setExtraStatus('Kunde inte läsa lager '+names.join(', ')+': '+err.message);return}
 }
 setExtraStatus('Visar '+shown.toLocaleString('sv-SE')+' kommunala objekt i kartutsnittet.'+(truncated?' Sökningen kan vara ofullständig (över 1 000 objekt). Zooma in för bättre täckning.':'')+' Parkering och laddplats innebär inte att tunga lastbilar får använda platsen.');
}
let refreshTimeout;
function queueExtraRefresh(){clearTimeout(refreshTimeout);refreshTimeout=setTimeout(refreshExtras,300)}
map.on('moveend zoomend',queueExtraRefresh);
legend.querySelectorAll('input').forEach(c=>c.addEventListener('change',()=>{
 const name=c.dataset.category;
 if(extra[name]){++extraLoadSerial;queueExtraRefresh()}
 else{const layer=layers[name];if(c.checked)map.addLayer(layer);else map.removeLayer(layer)}
}));
const note=document.createElement('p');note.className='source-note';note.textContent='Datakälla: Luleå kommun, ArcGIS REST (lager 2, 5, 35, 38–39). Rekommenderade leder är verifierat statiskt uttag; andra lager hämtas för synligt kartutsnitt. Det här är en datakarta, inte en ruttplanerare eller juridiskt bindande redovisning av trafikföreskrifter. Kontrollera aktuella regler före körning med farligt gods. Storhedens lokala trafikmätningar används inte.';root.append(note);
if(page&&page.classList.contains('active'))setTimeout(repairMapView,250);
}).catch(err=>{message.textContent='Kartan kunde inte läsas in: '+String(err.message||err)});
})();