const FOCUS=new Set(["Luleå","Boden","Piteå","Älvsbyn","Kalix"]);

let rows=[];

const $=id=>document.getElementById(id);
const fmt=new Intl.NumberFormat("sv-SE",{maximumFractionDigits:0});

function parseCsv(text){
  const lines=text.trim().split(/\r?\n/);
  const header=lines.shift().replace(/^\uFEFF/,"").split(",");
  return lines.map(line=>{
    const parts=[];let cur="",q=false;
    for(let i=0;i<line.length;i++){
      const ch=line[i];
      if(ch==='"'){
        if(q&&line[i+1]==='"'){cur+='"';i++}else q=!q;
      }else if(ch===","&&!q){parts.push(cur);cur="";}else cur+=ch;
    }
    parts.push(cur);
    return Object.fromEntries(header.map((h,i)=>[h,parts[i]??""]));
  });
}

function fillSelect(id,values,preferred){
  const s=$(id);s.innerHTML="";
  values.forEach(v=>{const o=document.createElement("option");o.value=v;o.textContent=v;s.appendChild(o)});
  if(preferred&&values.includes(preferred))s.value=preferred;
}

function cellColor(value,max){
  if(!Number.isFinite(value)||value<=0)return "#f8fafc";
  const t=Math.sqrt(value/Math.max(1,max));
  const a=[238,245,255],b=[29,78,216];
  const c=a.map((x,i)=>Math.round(x+(b[i]-x)*t));
  return "rgb("+c.join(",")+")";
}
function textColor(value,max){
  if(!Number.isFinite(value)||value<=0)return "#94a3b8";
  return Math.sqrt(value/Math.max(1,max))>.58?"#fff":"#172033";
}

function render(){
  const year=Number($("year").value);
  const sex=$("sex").value;
  const scope=$("scope").value;
  const data=rows.filter(r=>Number(r.year)===year&&r.sex===sex);
  const names=[...new Set(data.flatMap(r=>[r.residence,r.workplace]))].sort((a,b)=>a.localeCompare(b,"sv"));
  const shown=scope==="focus"?names.filter(n=>FOCUS.has(n)):names;
  const map=new Map(data.map(r=>[r.residence+"|"+r.workplace,Number(r.employed)]));
  const values=[];
  for(const a of shown)for(const b of shown){
    if(a===b)continue;
    const v=map.get(a+"|"+b);
    if(Number.isFinite(v))values.push(v);
  }
  const max=Math.max(1,...values);

  const table=document.createElement("table");table.className="matrix";
  const thead=document.createElement("thead"),tr=document.createElement("tr");
  const corner=document.createElement("th");corner.textContent="Bostad ↓ / Arbete →";corner.className="row";tr.appendChild(corner);
  shown.forEach((name,colIndex)=>{
    const th=document.createElement("th");th.className="col"+(FOCUS.has(name)?" focus-label":"");
    th.dataset.colIndex=String(colIndex);
    const span=document.createElement("span");span.textContent=name;th.appendChild(span);tr.appendChild(th);
  });
  thead.appendChild(tr);table.appendChild(thead);
  const tbody=document.createElement("tbody");
  shown.forEach((res,rowIndex)=>{
    const rr=document.createElement("tr");
    const th=document.createElement("th");th.className="row"+(FOCUS.has(res)?" focus-label":"");
    th.dataset.rowIndex=String(rowIndex);
    th.textContent=res;rr.appendChild(th);
    shown.forEach((work,colIndex)=>{
      const td=document.createElement("td");
      const v=map.get(res+"|"+work);
      td.textContent=Number.isFinite(v)?fmt.format(v):"–";
      td.dataset.rowIndex=String(rowIndex);
      td.dataset.colIndex=String(colIndex);
      if(res===work){
        td.classList.add("diagonal");
        td.style.background="#e5e7eb";
        td.style.color="#475569";
      }else{
        td.style.background=cellColor(v,max);
        td.style.color=textColor(v,max);
        if(FOCUS.has(res)||FOCUS.has(work))td.classList.add("focus-edge");
      }
      td.dataset.tip=res+" → "+work+": "+(Number.isFinite(v)?fmt.format(v):"saknas");
      rr.appendChild(td);
    });
    tbody.appendChild(rr);
  });
  table.appendChild(tbody);

  const clearMatrixGuide=()=>{
    table.querySelectorAll(".matrix-hover-guide,.matrix-hover-header").forEach(el=>{
      el.classList.remove("matrix-hover-guide","matrix-hover-header");
    });
  };

  table.addEventListener("mouseover",event=>{
    const cell=event.target.closest("td");
    if(!cell||!table.contains(cell))return;
    clearMatrixGuide();
    const rowIndex=Number(cell.dataset.rowIndex);
    const colIndex=Number(cell.dataset.colIndex);

    table.querySelectorAll("tbody td").forEach(td=>{
      const r=Number(td.dataset.rowIndex);
      const c=Number(td.dataset.colIndex);
      if((r===rowIndex&&c<colIndex)||(c===colIndex&&r<rowIndex)){
        td.classList.add("matrix-hover-guide");
      }
    });

    const rowHeader=table.querySelector('tbody th.row[data-row-index="'+rowIndex+'"]');
    const colHeader=table.querySelector('thead th.col[data-col-index="'+colIndex+'"]');
    if(rowHeader)rowHeader.classList.add("matrix-hover-header");
    if(colHeader)colHeader.classList.add("matrix-hover-header");
  });

  table.addEventListener("mouseleave",clearMatrixGuide);

  $("matrix").replaceChildren(table);

  const cross=data.filter(r=>r.residence!==r.workplace&&Number(r.employed)>0).sort((a,b)=>Number(b.employed)-Number(a.employed));
  const largest=cross[0];
  $("largest").textContent=largest?fmt.format(Number(largest.employed)):"–";
  $("largestSub").textContent=largest?largest.residence+" → "+largest.workplace:"–";
  const into=data.filter(r=>r.workplace==="Luleå"&&r.residence!=="Luleå").reduce((s,r)=>s+(Number(r.employed)||0),0);
  const out=data.filter(r=>r.residence==="Luleå"&&r.workplace!=="Luleå").reduce((s,r)=>s+(Number(r.employed)||0),0);
  $("intoLulea").textContent=fmt.format(into);$("outLulea").textContent=fmt.format(out);
}

(async()=>{
  const [csv,meta]=await Promise.all([
    fetch("data/commuting.csv",{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error("Data saknas – kör GitHub Action Update commuting data först.");return r.text()}),
    fetch("data/meta.json",{cache:"no-store"}).then(r=>r.ok?r.json():null)
  ]);
  rows=parseCsv(csv);
  const years=[...new Set(rows.map(r=>r.year))].sort((a,b)=>Number(b)-Number(a));
  const sexes=[...new Set(rows.map(r=>r.sex))].sort((a,b)=>a.localeCompare(b,"sv"));
  fillSelect("year",years,years[0]);
  fillSelect("sex",sexes,sexes.find(x=>x.toLocaleLowerCase("sv").includes("tot"))||sexes[0]);
  ["year","sex","scope"].forEach(id=>$(id).addEventListener("change",render));
  render();
})().catch(err=>{
  $("matrix").innerHTML='<div style="padding:20px;color:#b42318"><strong>Kunde inte ladda data.</strong><br>'+String(err.message||err)+'</div>';
});


const NORRBOTTEN_MUNICIPALITIES=[
  "Arjeplog","Arvidsjaur","Boden","Gällivare","Haparanda","Jokkmokk","Kalix",
  "Kiruna","Luleå","Pajala","Piteå","Älvsbyn","Överkalix","Övertorneå"
];

function setupPageNavigation(){
  const tabs=[...document.querySelectorAll(".tab[data-page]")];
  const pages=[...document.querySelectorAll(".page")];

  function openPage(name){
    tabs.forEach(t=>t.classList.toggle("active",t.dataset.page===name));
    pages.forEach(p=>p.classList.toggle("active",p.id==="page-"+name));
    window.scrollTo({top:0,behavior:"smooth"});
  }

  tabs.forEach(tab=>tab.addEventListener("click",()=>openPage(tab.dataset.page)));
  document.querySelectorAll("[data-open-page]").forEach(btn=>{
    btn.addEventListener("click",()=>openPage(btn.dataset.openPage));
  });
}

function setupMunicipalityExplorer(selectId,headingIds){
  const select=$(selectId);
  if(!select)return;
  select.innerHTML="";
  NORRBOTTEN_MUNICIPALITIES.forEach(name=>{
    const opt=document.createElement("option");
    opt.value=name;opt.textContent=name;select.appendChild(opt);
  });
  select.value="Luleå";

  const update=()=>{
    headingIds.forEach(id=>{
      const node=$(id);
      if(node)node.textContent=select.value;
    });
  };
  select.addEventListener("change",update);
  update();
}

setupPageNavigation();
setupMunicipalityExplorer("vehicleMunicipality",["vehicleMunicipalityTitle","vehicleMunicipalityHeading"]);
setupMunicipalityExplorer("injuryMunicipality",["injuryMunicipalityHeading"]);
setupMunicipalityExplorer("serviceMunicipality",["serviceMunicipalityHeading"]);
setupMunicipalityExplorer("nvdbMunicipality",["nvdbMunicipalityTitle","nvdbMunicipalityHeading"]);


let TRAFA=null;
const trafaFmt0=new Intl.NumberFormat("sv-SE",{maximumFractionDigits:0});
const trafaFmt2=new Intl.NumberFormat("sv-SE",{maximumFractionDigits:2});

function formatTrafaValue(value,suffix=""){
  if(value==null||value==="")return "–";
  const n=Number(value);
  if(Number.isFinite(n)){
    const text=Math.abs(n-Math.round(n))<1e-9?trafaFmt0.format(n):trafaFmt2.format(n);
    return text+(suffix||"");
  }
  return String(value);
}

const VEHICLE_DATASETS=[
  {sheet:"Tabell 3 Personbil",label:"Personbilar och ägande",metrics:[
    ["Kolumn 3","Personbilar i trafik",""],
    ["Kolumn 5","Ägda av kvinnor",""],
    ["Kolumn 6","Ägda av män",""],
    ["Kolumn 7","Ägda av juridiska personer",""],
    ["Kolumn 13","Personbilar per 1 000 invånare",""],
    ["Kolumn 14","Privatägda personbilar per 1 000 invånare",""]
  ]},
  {sheet:"Tabell 6 Lätt lastbil",label:"Lätta lastbilar",metrics:[["Kolumn 11","Lätta lastbilar i trafik",""]]},
  {sheet:"Tabell 7 Tung lastbil",label:"Tunga lastbilar",metrics:[["Kolumn 11","Tunga lastbilar i trafik",""]]},
  {sheet:"Tabell 8 Buss",label:"Bussar",metrics:[["Kolumn 10","Bussar i trafik",""]]}
];

const SERVICE_DATASETS=[
  {sheet:"Tabell 2b",label:"Färdtjänsttillstånd",metrics:[
    ["Kolumn 3","Män under 65 år",""],
    ["Kolumn 4","Kvinnor under 65 år",""],
    ["Kolumn 5","Män 65 år eller äldre",""],
    ["Kolumn 6","Kvinnor 65 år eller äldre",""],
    ["Kolumn 7","Män totalt",""],
    ["Kolumn 8","Kvinnor totalt",""],
    ["Kolumn 9","Tillstånd totalt",""]
  ]},
  {sheet:"Tabell 3b",label:"Tillstånd per 1 000 invånare",metrics:[
    ["Kolumn 3","Tillstånd totalt",""],
    ["6.98 · 3.11 · 7.53","Män under 65 år per 1 000",""],
    ["10.13 · 5.84 · 8.67","Kvinnor under 65 år per 1 000",""],
    ["68.97 · 67.42 · 88.22","Män 65+ per 1 000",""],
    ["113.95 · 71.09 · 128.84","Kvinnor 65+ per 1 000",""],
    ["19.64 · 23.43 · 24.07","Män totalt per 1 000",""],
    ["34.06 · 27.39 · 36.62","Kvinnor totalt per 1 000",""],
    ["26.7 · 25.31 · 30.24","Totalt per 1 000",""]
  ]},
  {sheet:"Tabell 4",label:"Färdtjänstresor och nyttjande",metrics:[
    ["Kolumn 3","Enkelresor, män",""],
    ["Kolumn 4","Enkelresor, kvinnor",""],
    ["Kolumn 5","Enkelresor totalt",""],
    ["35.98 · 14.97 · 50.34","Resor per tillstånd, män",""],
    ["17.44 · 27.66 · 39.49","Resor per tillstånd, kvinnor",""],
    ["24.4 · 21.5 · 43.88","Resor per tillstånd, totalt",""],
    ["65.22 · 63.64 · 65.65","Andel nyttjare, män"," %"],
    ["56.86 · 85.71 · 68.37","Andel nyttjare, kvinnor"," %"],
    ["87.74 · 80.27 · 67.27","Andel nyttjare, totalt"," %"]
  ]},
  {sheet:"Tabell 7b",label:"Riksfärdtjänst – nyttjare",metrics:[
    ["Kolumn 3","Män",""],["Kolumn 4","Kvinnor",""],["Kolumn 5","Totalt",""]
  ]},
  {sheet:"Tabell 8b",label:"Riksfärdtjänst – nyttjare per 1 000",metrics:[
    ["3.2 · 0.71 · 1.18","Män per 1 000",""],["6.23 · 6.26 · 1.7","Kvinnor per 1 000",""],["4.69 · 3.35 · 1.44","Totalt per 1 000",""]
  ]},
  {sheet:"Tabell 9",label:"Riksfärdtjänst – resor",metrics:[
    ["Kolumn 3","Enkelresor, män",""],["Kolumn 4","Enkelresor, kvinnor",""],["Kolumn 5","Enkelresor totalt",""],
    ["6.45 · 16.87 · 6.3","Resor per nyttjare, män",""],["10.89 · 4.75 · 5.52","Resor per nyttjare, kvinnor",""],["12.98 · 4.44 · 5.85","Resor per nyttjare, totalt",""]
  ]}
];

function fillDatasetSelect(id,defs){
  const s=$(id);if(!s)return;
  s.innerHTML="";
  defs.forEach(d=>{
    const o=document.createElement("option");
    o.value=d.sheet;o.textContent=d.label;s.appendChild(o);
  });
}

function renderMetricGrid(gridId,metrics,values){
  const grid=$(gridId);if(!grid)return;
  grid.innerHTML="";
  metrics.forEach(([key,label,suffix])=>{
    if(!(key in values))return;
    const article=document.createElement("article");
    article.className="metric-card";
    const span=document.createElement("span");span.textContent=label;
    const strong=document.createElement("strong");strong.textContent=formatTrafaValue(values[key],suffix);
    article.append(span,strong);
    grid.appendChild(article);
  });
}

function findTrafaRow(section,sheetName,municipality){
  const sheet=TRAFA?.[section]?.sheets?.find(s=>s.title===sheetName);
  return sheet?.rows?.find(r=>r.municipality===municipality)||null;
}

function renderVehicleData(){
  if(!TRAFA)return;
  const municipality=$("vehicleMunicipality").value;
  const sheetName=$("vehicleDataset").value;
  const def=VEHICLE_DATASETS.find(d=>d.sheet===sheetName)||VEHICLE_DATASETS[0];
  const row=findTrafaRow("vehicles",def.sheet,municipality);
  $("vehicleDataStatus").textContent=row
    ? "Trafikanalys 2025 · "+def.label
    : "Ingen kommunrad hittades i valt tabellblad.";
  renderMetricGrid("vehicleDataGrid",def.metrics,row?.values||{});
}

function renderServiceData(){
  if(!TRAFA)return;
  const municipality=$("serviceMunicipality").value;
  const sheetName=$("serviceDataset").value;
  const def=SERVICE_DATASETS.find(d=>d.sheet===sheetName)||SERVICE_DATASETS[0];
  const row=findTrafaRow("service",def.sheet,municipality);
  $("serviceDataStatus").textContent=row
    ? "Trafikanalys 2025 · "+def.label
    : "Ingen kommunrad hittades i valt tabellblad.";
  renderMetricGrid("serviceDataGrid",def.metrics,row?.values||{});
}

async function loadTrafaData(){
  try{
    const r=await fetch("data/trafa.json",{cache:"no-store"});
    if(!r.ok)throw new Error("HTTP "+r.status);
    TRAFA=await r.json();
    fillDatasetSelect("vehicleDataset",VEHICLE_DATASETS);
    fillDatasetSelect("serviceDataset",SERVICE_DATASETS);
    $("vehicleMunicipality").addEventListener("change",renderVehicleData);
    $("vehicleDataset").addEventListener("change",renderVehicleData);
    $("serviceMunicipality").addEventListener("change",renderServiceData);
    $("serviceDataset").addEventListener("change",renderServiceData);
    renderVehicleData();
    renderServiceData();
  }catch(err){
    if($("vehicleDataStatus"))$("vehicleDataStatus").textContent="Kunde inte läsa Trafikanalys-data: "+err.message;
    if($("serviceDataStatus"))$("serviceDataStatus").textContent="Kunde inte läsa Trafikanalys-data: "+err.message;
  }
}
loadTrafaData();


let NVDB_DATA=null;
const nvdbFmt=new Intl.NumberFormat("sv-SE",{minimumFractionDigits:0,maximumFractionDigits:1});

function nvdbKm(section,value){
  if(value==null||!Number.isFinite(Number(value)))return null;
  return section==="cycle"?Number(value)/1000:Number(value);
}

function nvdbValueText(value){
  if(value==null||!Number.isFinite(Number(value)))return "–";
  return nvdbFmt.format(Number(value))+" km";
}

function nvdbLineSvg(series){
  const width=900,height=330,p={l:62,r:22,t:26,b:48};
  const all=series.flatMap(s=>s.values.map(v=>v.value).filter(Number.isFinite));
  const max=Math.max(1,...all);
  const years=[...new Set(series.flatMap(s=>s.values.map(v=>v.year)))].sort((a,b)=>a-b);
  const x=year=>p.l+(years.indexOf(year)/(Math.max(1,years.length-1)))*(width-p.l-p.r);
  const y=value=>height-p.b-(value/max)*(height-p.t-p.b);
  const colors=["#2563eb","#dc2626","#16a34a"];
  const labels=series.map((s,i)=>'<span class="nvdb-legend-item"><i style="background:'+colors[i]+'"></i>'+s.label+'</span>').join("");
  const grid=[0,.25,.5,.75,1].map(fr=>{
    const yy=height-p.b-fr*(height-p.t-p.b);
    return '<line x1="'+p.l+'" x2="'+(width-p.r)+'" y1="'+yy+'" y2="'+yy+'" class="nvdb-gridline"/>'+
      '<text x="'+(p.l-10)+'" y="'+(yy+4)+'" text-anchor="end" class="nvdb-axis">'+nvdbFmt.format(max*fr)+'</text>';
  }).join("");
  const yearTicks=years.map(year=>'<text x="'+x(year)+'" y="'+(height-18)+'" text-anchor="middle" class="nvdb-axis">'+year+'</text>').join("");
  const lines=series.map((s,i)=>{
    const pts=s.values.filter(v=>Number.isFinite(v.value)).map(v=>x(v.year)+','+y(v.value)).join(' ');
    const circles=s.values.filter(v=>Number.isFinite(v.value)).map(v=>
      '<circle cx="'+x(v.year)+'" cy="'+y(v.value)+'" r="4" fill="'+colors[i]+'"><title>'+s.label+' '+v.year+': '+nvdbFmt.format(v.value)+' km</title></circle>'
    ).join("");
    return '<polyline points="'+pts+'" fill="none" stroke="'+colors[i]+'" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>'+circles;
  }).join("");
  return '<div class="nvdb-legend">'+labels+'</div><svg class="nvdb-svg" viewBox="0 0 '+width+' '+height+'" role="img" aria-label="Utveckling av vägnät">'+grid+yearTicks+lines+'</svg>';
}

function renderNvdb(){
  if(!NVDB_DATA)return;
  const section=$("nvdbDataset").value;
  const municipality=$("nvdbMunicipality").value;
  const data=NVDB_DATA[section];
  if(!data)return;
  const years=data.years.slice().sort((a,b)=>a-b);
  if(!$("nvdbYear").options.length){
    years.slice().sort((a,b)=>b-a).forEach(year=>{
      const o=document.createElement("option");o.value=year;o.textContent=year;$("nvdbYear").appendChild(o);
    });
  }
  let year=Number($("nvdbYear").value||years[years.length-1]);
  if(!years.includes(year)){
    year=years[years.length-1];
    $("nvdbYear").value=year;
  }
  const row=data.rows.find(r=>r.year===year&&r.municipality===municipality);
  $("nvdbDatasetTitle").textContent=data.label;
  $("nvdbStatus").textContent=row
    ? "NVDB "+year+" · värden efter väghållare"
    : "Ingen kommunrad hittades för valt år.";
  $("nvdbPeriod").textContent=years[0]+"–"+years[years.length-1];
  $("nvdbChartUnit").textContent="kilometer";

  const metrics=[
    ["private","Enskild väghållare"],
    ["municipal","Kommunal väghållare"],
    ["state","Statlig väghållare"],
    ["total","Totalt vägnät"]
  ];
  const grid=$("nvdbMetricGrid");grid.innerHTML="";
  metrics.forEach(([key,label])=>{
    const article=document.createElement("article");article.className="metric-card";
    const span=document.createElement("span");span.textContent=label;
    const strong=document.createElement("strong");strong.textContent=nvdbValueText(row?nvdbKm(section,row[key]):null);
    article.append(span,strong);grid.appendChild(article);
  });

  renderNvdbHolderShares(row,section);

  const municipalRows=data.rows.filter(r=>r.municipality===municipality).sort((a,b)=>a.year-b.year);
  const series=[
    {label:"Enskild",values:municipalRows.map(r=>({year:r.year,value:nvdbKm(section,r.private)}))},
    {label:"Kommunal",values:municipalRows.map(r=>({year:r.year,value:nvdbKm(section,r.municipal)}))},
    {label:"Statlig",values:municipalRows.map(r=>({year:r.year,value:nvdbKm(section,r.state)}))}
  ];
  $("nvdbTrend").innerHTML=nvdbLineSvg(series);

  const table=document.createElement("table");table.className="simple-data-table";
  table.innerHTML="<thead><tr><th>År</th><th>Enskild</th><th>Kommunal</th><th>Statlig</th><th>Totalt</th></tr></thead>";
  const tbody=document.createElement("tbody");
  municipalRows.slice().sort((a,b)=>b.year-a.year).forEach(r=>{
    const tr=document.createElement("tr");
    [r.year,nvdbValueText(nvdbKm(section,r.private)),nvdbValueText(nvdbKm(section,r.municipal)),nvdbValueText(nvdbKm(section,r.state)),nvdbValueText(nvdbKm(section,r.total))].forEach(v=>{
      const td=document.createElement("td");td.textContent=v;tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  $("nvdbTable").replaceChildren(table);
}

async function loadNvdbData(){
  try{
    const r=await fetch("data/nvdb.json",{cache:"no-store"});
    if(!r.ok)throw new Error("HTTP "+r.status);
    NVDB_DATA=await r.json();
    const years=[...new Set(Object.values(NVDB_DATA).flatMap(x=>x.years||[]))].sort((a,b)=>b-a);
    $("nvdbYear").innerHTML="";
    years.forEach(year=>{const o=document.createElement("option");o.value=year;o.textContent=year;$("nvdbYear").appendChild(o)});
    ["nvdbMunicipality","nvdbDataset","nvdbYear"].forEach(id=>$(id).addEventListener("change",renderNvdb));
    renderNvdb();
  }catch(err){
    $("nvdbStatus").textContent="Kunde inte läsa NVDB-data: "+err.message;
  }
}
loadNvdbData();


function renderNvdbHolderShares(row,section){
  const root=$("nvdbHolderShares");
  if(!root)return;
  root.innerHTML="";
  const vals=[
    ["Enskild",row?nvdbKm(section,row.private):null],
    ["Kommunal",row?nvdbKm(section,row.municipal):null],
    ["Statlig",row?nvdbKm(section,row.state):null]
  ];
  const total=vals.reduce((s,[,v])=>s+(Number.isFinite(v)?v:0),0);
  vals.forEach(([label,value])=>{
    const pct=total>0&&Number.isFinite(value)?value/total*100:0;
    const item=document.createElement("div");item.className="share-row";
    item.innerHTML='<div class="share-label"><span>'+label+'</span><strong>'+nvdbFmt.format(pct)+' %</strong></div>'+
      '<div class="share-track"><i style="width:'+Math.max(0,Math.min(100,pct))+'%"></i></div>'+
      '<small>'+nvdbValueText(value)+'</small>';
    root.appendChild(item);
  });
}

const MUNICIPALITY_CODES={
  "Arvidsjaur":"2505","Arjeplog":"2506","Jokkmokk":"2510","Överkalix":"2513",
  "Kalix":"2514","Övertorneå":"2518","Pajala":"2521","Gällivare":"2523",
  "Älvsbyn":"2560","Luleå":"2580","Piteå":"2581","Boden":"2582",
  "Haparanda":"2583","Kiruna":"2584"
};

let INJURY_DATA=null;
const injuryFmt0=new Intl.NumberFormat("sv-SE",{maximumFractionDigits:0});
const injuryFmt2=new Intl.NumberFormat("sv-SE",{maximumFractionDigits:2});

function injuryValue(v,digits=0){
  if(v==null||!Number.isFinite(Number(v)))return "–";
  return (digits===2?injuryFmt2:injuryFmt0).format(Number(v));
}

function injuryLineSvg(rows){
  const width=900,height=320,p={l:58,r:22,t:24,b:46};
  const values=rows.map(r=>Number(r.antolyckdsl)).filter(Number.isFinite);
  const max=Math.max(1,...values);
  const years=rows.map(r=>Number(r.ar));
  const minYear=Math.min(...years),maxYear=Math.max(...years);
  const x=year=>p.l+((year-minYear)/Math.max(1,maxYear-minYear))*(width-p.l-p.r);
  const y=value=>height-p.b-(value/max)*(height-p.t-p.b);
  const grid=[0,.25,.5,.75,1].map(fr=>{
    const yy=height-p.b-fr*(height-p.t-p.b);
    return '<line x1="'+p.l+'" x2="'+(width-p.r)+'" y1="'+yy+'" y2="'+yy+'" class="nvdb-gridline"/>'+
      '<text x="'+(p.l-10)+'" y="'+(yy+4)+'" text-anchor="end" class="nvdb-axis">'+injuryFmt0.format(max*fr)+'</text>';
  }).join("");
  const tickYears=years.filter((y,i)=>i===0||i===years.length-1||y%2===0);
  const ticks=tickYears.map(year=>'<text x="'+x(year)+'" y="'+(height-17)+'" text-anchor="middle" class="nvdb-axis">'+year+'</text>').join("");
  const pts=rows.filter(r=>Number.isFinite(Number(r.antolyckdsl))).map(r=>x(Number(r.ar))+','+y(Number(r.antolyckdsl))).join(" ");
  const circles=rows.filter(r=>Number.isFinite(Number(r.antolyckdsl))).map(r=>{
    const year=Number(r.ar),v=Number(r.antolyckdsl);
    return '<circle cx="'+x(year)+'" cy="'+y(v)+'" r="4" fill="#2563eb"><title>'+year+': '+injuryFmt0.format(v)+' olyckor</title></circle>';
  }).join("");
  return '<svg class="nvdb-svg" viewBox="0 0 '+width+' '+height+'" role="img" aria-label="Olyckor med personskada över tid">'+grid+ticks+
    '<polyline points="'+pts+'" fill="none" stroke="#2563eb" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>'+circles+'</svg>';
}

function renderBarList(rootId,rows,labelField){
  const root=$(rootId);if(!root)return;
  root.innerHTML="";
  const usable=rows
    .map(r=>({label:r._labels?.[labelField]||r[labelField]||"Okänt",value:Number(r.antolyckdsl)}))
    .filter(x=>Number.isFinite(x.value)&&x.value>=0)
    .sort((a,b)=>b.value-a.value);
  const max=Math.max(1,...usable.map(x=>x.value));
  usable.forEach(x=>{
    const item=document.createElement("div");item.className="bar-row";
    const pct=x.value/max*100;
    item.innerHTML='<span class="bar-name">'+x.label+'</span>'+
      '<div class="bar-track"><i style="width:'+pct+'%"></i></div>'+
      '<strong>'+injuryFmt0.format(x.value)+'</strong>';
    root.appendChild(item);
  });
  if(!usable.length)root.textContent="Ingen data för valt urval.";
}

function renderInjury(){
  if(!INJURY_DATA)return;
  const municipality=$("injuryMunicipality").value;
  const code=MUNICIPALITY_CODES[municipality];
  const year=Number($("injuryYear").value||INJURY_DATA.latest_year);
  const rows=INJURY_DATA.total.filter(r=>String(r.kommun)===String(code)).sort((a,b)=>Number(a.ar)-Number(b.ar));
  const row=rows.find(r=>Number(r.ar)===year);

  $("injuryDataStatus").textContent=row
    ? "Trafikanalys "+year+" · polisrapporterade vägtrafikolyckor"
    : "Ingen data hittades för valt år.";

  const metrics=[
    ["antolyckdsl","Olyckor med personskada",0,""],
    ["antpersd","Dödade personer",0,""],
    ["antperss","Svårt skadade",0,""],
    ["antpersl","Lindrigt skadade",0,""],
    ["antdslper100000","Dödade + skadade per 100 000 inv.",2,""]
  ];
  const grid=$("injuryMetricGrid");grid.innerHTML="";
  metrics.forEach(([key,label,digits,suffix])=>{
    const article=document.createElement("article");article.className="metric-card";
    const span=document.createElement("span");span.textContent=label;
    const strong=document.createElement("strong");strong.textContent=injuryValue(row?.[key],digits)+suffix;
    article.append(span,strong);grid.appendChild(article);
  });

  $("injuryTrend").innerHTML=rows.length?injuryLineSvg(rows):"Ingen tidsserie tillgänglig.";

  const table=document.createElement("table");table.className="simple-data-table";
  table.innerHTML="<thead><tr><th>År</th><th>Olyckor</th><th>Dödade</th><th>Svårt skadade</th><th>Lindrigt skadade</th><th>Per 100 000</th></tr></thead>";
  const tbody=document.createElement("tbody");
  rows.slice().sort((a,b)=>Number(b.ar)-Number(a.ar)).forEach(r=>{
    const tr=document.createElement("tr");
    const vals=[r.ar,injuryValue(r.antolyckdsl),injuryValue(r.antpersd),injuryValue(r.antperss),injuryValue(r.antpersl),injuryValue(r.antdslper100000,2)];
    vals.forEach(v=>{const td=document.createElement("td");td.textContent=v;tr.appendChild(td)});
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  $("injuryTable").replaceChildren(table);

  const latest=Number(INJURY_DATA.latest_year);
  renderBarList("injurySpeedBars",INJURY_DATA.by_speed_limit.filter(r=>String(r.kommun)===String(code)&&Number(r.ar)===latest),"hastighet");
  renderBarList("injuryRoadBars",INJURY_DATA.by_road_type.filter(r=>String(r.kommun)===String(code)&&Number(r.ar)===latest),"vagtyp");
}

async function loadInjuryData(){
  try{
    const r=await fetch("data/injuries.json",{cache:"no-store"});
    if(!r.ok)throw new Error("HTTP "+r.status);
    INJURY_DATA=await r.json();
    const years=INJURY_DATA.years.slice().sort((a,b)=>b-a);
    $("injuryYear").innerHTML="";
    years.forEach(year=>{
      const o=document.createElement("option");o.value=year;o.textContent=year;$("injuryYear").appendChild(o);
    });
    $("injuryYear").value=String(INJURY_DATA.latest_year);
    $("injuryMunicipality").addEventListener("change",renderInjury);
    $("injuryYear").addEventListener("change",renderInjury);
    renderInjury();
  }catch(err){
    if($("injuryDataStatus"))$("injuryDataStatus").textContent="Kunde inte läsa vägtrafikskador: "+err.message;
  }
}
loadInjuryData();
