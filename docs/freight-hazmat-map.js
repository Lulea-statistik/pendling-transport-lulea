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
const categories=[['Primär rekommenderad väg','#b91c1c'],['Sekundär rekommenderad väg','#eab308'],['Förbudsobjekt – ej juridiskt verifierade','#475569']];
for(const [label,color] of categories){const item=document.createElement('label');item.style.cssText='display:inline-flex;align-items:center;gap:8px;cursor:pointer;font-size:14px;min-height:30px;flex-wrap:nowrap';const check=document.createElement('input');check.type='checkbox';check.checked=true;check.dataset.category=label;check.style.cssText='width:16px;height:16px;accent-color:'+color+';margin:0;flex:none';const swatch=document.createElement('span');swatch.style.cssText='display:inline-block;width:22px;border-top:4px solid '+color;item.append(check,swatch,document.createTextNode(label));legend.append(item)}
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
legend.querySelectorAll('input').forEach(c=>c.addEventListener('change',()=>{const layer=layers[c.dataset.category];if(c.checked)map.addLayer(layer);else map.removeLayer(layer)}));
const note=document.createElement('p');note.className='source-note';note.textContent='Datakälla: Luleå kommun, ArcGIS REST (lager 38–39), geometrier verifierade 12 oktober 2026. Det här är en datakarta, inte en ruttplanerare eller juridiskt bindande redovisning av trafikföreskrifter. Kontrollera aktuella regler före körning med farligt gods. Storhedens lokala trafikmätningar används inte.';root.append(note);
if(page&&page.classList.contains('active'))setTimeout(repairMapView,250);
}).catch(err=>{message.textContent='Kartan kunde inte läsas in: '+String(err.message||err)});
})();