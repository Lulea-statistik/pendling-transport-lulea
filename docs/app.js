const FOCUS=new Set(["Luleå","Boden","Piteå","Älvsbyn","Kalix"]);
const NEUTRAL_MATRIX=new Set(["Arjeplog"]);
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
    if(NEUTRAL_MATRIX.has(a)||NEUTRAL_MATRIX.has(b))continue;
    const v=map.get(a+"|"+b);
    if(Number.isFinite(v))values.push(v);
  }
  const max=Math.max(1,...values);

  const table=document.createElement("table");table.className="matrix";
  const thead=document.createElement("thead"),tr=document.createElement("tr");
  const corner=document.createElement("th");corner.textContent="Bostad ↓ / Arbete →";corner.className="row";tr.appendChild(corner);
  shown.forEach(name=>{
    const th=document.createElement("th");th.className="col"+(FOCUS.has(name)?" focus-label":"");
    const span=document.createElement("span");span.textContent=name;th.appendChild(span);tr.appendChild(th);
  });
  thead.appendChild(tr);table.appendChild(thead);
  const tbody=document.createElement("tbody");
  shown.forEach(res=>{
    const rr=document.createElement("tr");
    const th=document.createElement("th");th.className="row"+(FOCUS.has(res)?" focus-label":"");th.textContent=res;rr.appendChild(th);
    shown.forEach(work=>{
      const td=document.createElement("td");
      const v=map.get(res+"|"+work);
      td.textContent=Number.isFinite(v)?fmt.format(v):"–";
      const neutral=NEUTRAL_MATRIX.has(res)||NEUTRAL_MATRIX.has(work);
      td.style.background=neutral?"#e5e7eb":cellColor(v,max);
      td.style.color=neutral?"#475569":textColor(v,max);
      if(neutral)td.classList.add("neutral-cell");
      if(res===work)td.classList.add("diagonal");
      if(!neutral&&(FOCUS.has(res)||FOCUS.has(work)))td.classList.add("focus-edge");
      td.dataset.tip=res+" → "+work+": "+(Number.isFinite(v)?fmt.format(v):"saknas");
      rr.appendChild(td);
    });
    tbody.appendChild(rr);
  });
  table.appendChild(tbody);
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
