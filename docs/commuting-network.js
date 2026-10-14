/* Directed intermunicipal commuting network, using the same SCB CSV as the matrix. */
(() => {
"use strict";
const $ = id => document.getElementById(id);
const format = new Intl.NumberFormat("sv-SE");
const focus = ["Luleå","Boden","Piteå","Älvsbyn","Kalix"];
const palette = {"Luleå":"#b42318","Boden":"#d99d13","Piteå":"#2563eb","Älvsbyn":"#0d9488","Kalix":"#8b5cf6"};
const escapeHtml = s => String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let data = [];
let selected = ["Boden","Luleå"];
function csvParse(raw) {
 const lines = raw.replace(/^\uFEFF/,"").trim().split(/\r?\n/);
 const headers = lines.shift().split(",");
 return lines.map(line => {
  const cells=[];let field="",quoted=false;
  for(let i=0;i<line.length;i++){let c=line[i];if(c==='"'){if(quoted&&line[i+1]==='"'){field+='"';i++;}else quoted=!quoted;}else if(c===","&&!quoted){cells.push(field);field="";}else field+=c;}
  cells.push(field);
  return Object.fromEntries(headers.map((h,i)=>[h,cells[i]||""]));
 });
}
const nodeColors = name => palette[name] || "#64748b";
function setup() {
 const ys=[...new Set(data.map(x=>x.year))].sort((a,b)=>+b-+a);
 const sexes=[...new Set(data.map(x=>x.sex))];
 const year=$("networkYear"),sex=$("networkSex");
 ys.forEach(v=>year.add(new Option(v,v)));
 year.value=ys.includes("2024")?"2024":ys[0];
 sexes.forEach(v=>sex.add(new Option(v,v)));
 sex.value=sexes.find(x=>x.toLowerCase().includes("tot"))||sexes[0];
 ["networkYear","networkSex","networkScope","networkMinimum"].forEach(id=>$(id).addEventListener("change",render));
 $("networkReset").addEventListener("click",()=>{selected=["Boden","Luleå"];render();});
 render();
}
function render(){
 const year=$("networkYear").value,sex=$("networkSex").value,scope=$("networkScope").value;
 const minimum=Number($("networkMinimum").value);
 const records=data.filter(x=>x.year===year&&x.sex===sex);
 const names=[...new Set(records.flatMap(x=>[x.residence,x.workplace]))].filter(Boolean).sort((a,b)=>a.localeCompare(b,"sv"));
 const shown=scope==="focus"?focus.filter(n=>names.includes(n)):names;
 const map=new Map(records.map(x=>[x.residence+"|"+x.workplace,Number(x.employed)]));
 const workplaceTotals=new Map(shown.map(n=>[n,records.filter(x=>x.workplace===n).reduce((a,x)=>a+(Number(x.employed)||0),0)]));
 const maxDay=Math.max(1,...workplaceTotals.values());
 const W=1080,H=710,cx=540,cy=347,rx=425,ry=250;
 const nodes=shown.map((name,i)=>{
  const angle=-Math.PI/2+2*Math.PI*i/shown.length;
  const day=workplaceTotals.get(name)||0;
  return {name,day,x:cx+rx*Math.cos(angle),y:cy+ry*Math.sin(angle),r:Math.max(18,Math.sqrt(day/maxDay)*60)};
 });
 const nodeMap=new Map(nodes.map(n=>[n.name,n]));
 const pairs=[];
 for(let i=0;i<shown.length;i++)for(let j=i+1;j<shown.length;j++){
  const a=shown[i],b=shown[j],ab=map.get(a+"|"+b),ba=map.get(b+"|"+a);
  if((Number.isFinite(ab)&&ab>=minimum)||(Number.isFinite(ba)&&ba>=minimum))pairs.push({a,b,ab,ba});
 }
 const maxFlow=Math.max(1,...pairs.flatMap(p=>[p.ab||0,p.ba||0]));
 const svg=[];
 svg.push('<svg viewBox="0 0 '+W+' '+H+'" class="commuting-network-svg" role="img" aria-label="Riktat nätverk med kommuner och arbetspendling"><defs><marker id="commuteArrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0 0 L6 3 L0 6 Z" fill="context-stroke"/></marker></defs>');
 // Curves are offset on opposite sides of each municipality pair.
 const draw=(from,to,count,side)=>{
  if(!Number.isFinite(count)||count<minimum||count<=0)return;
  const a=nodeMap.get(from),b=nodeMap.get(to);if(!a||!b)return;
  const dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy);if(!d)return;
  const ux=dx/d,uy=dy/d,nx=-uy,ny=ux;
  const offset=side*23;
  const sx=a.x+ux*(a.r+3)+nx*offset*.3,sy=a.y+uy*(a.r+3)+ny*offset*.3;
  const tx=b.x-ux*(b.r+10)+nx*offset*.3,ty=b.y-uy*(b.r+10)+ny*offset*.3;
  const mx=(sx+tx)/2+nx*offset,my=(sy+ty)/2+ny*offset;
  const thickness=(1.2+10*Math.sqrt(count/maxFlow)).toFixed(2);
  const highlighted=selected.includes(from)&&selected.includes(to);
  const opacity=selected.length===2&&!highlighted?".18":".79";
  svg.push('<path d="M '+sx.toFixed(1)+' '+sy.toFixed(1)+' Q '+mx.toFixed(1)+' '+my.toFixed(1)+' '+tx.toFixed(1)+' '+ty.toFixed(1)+'" fill="none" stroke="'+nodeColors(from)+'" stroke-width="'+thickness+'" opacity="'+opacity+'" stroke-linecap="round" marker-end="url(#commuteArrow)"><title>'+escapeHtml(from)+' → '+escapeHtml(to)+': '+format.format(count)+' personer ('+year+')</title></path>');
 };
 pairs.forEach(p=>{draw(p.a,p.b,p.ab,1);draw(p.b,p.a,p.ba,1);});
 nodes.forEach(n=>{
  const active=selected.includes(n.name);
  svg.push('<g class="commuting-node" tabindex="0" role="button" data-name="'+escapeHtml(n.name)+'" aria-label="'+escapeHtml(n.name)+', '+format.format(n.day)+' sysselsatta arbetsplatser"><circle cx="'+n.x+'" cy="'+n.y+'" r="'+n.r+'" fill="'+nodeColors(n.name)+'" stroke="'+(active?"#172033":"#fff")+'" stroke-width="'+(active?5:3)+'"/><text x="'+n.x+'" y="'+(n.y+4)+'" text-anchor="middle" fill="#fff" font-size="'+(n.r>35?14:11)+'" font-weight="700">'+escapeHtml(n.name)+'</text><text x="'+n.x+'" y="'+(n.y+20)+'" text-anchor="middle" fill="#fff" font-size="11">'+format.format(n.day)+'</text><title>'+escapeHtml(n.name)+': '+format.format(n.day)+' sysselsatta med arbetsställe i kommunen, från bostadskommuner i datamaterialet</title></g>');
 });
 svg.push('</svg>');
 const root=$("commutingNetwork");root.innerHTML=svg.join("");
 root.querySelectorAll(".commuting-node").forEach(el=>{
  const activate=()=>{const name=el.dataset.name;selected=selected[1]===name?[selected[0],name]:[selected[1],name];render();};
  el.addEventListener("click",activate);
  el.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();activate();}});
 });
 const [a,b]=selected;
 const ab=map.get(a+"|"+b),ba=map.get(b+"|"+a);
 $("networkPair").innerHTML='<strong>'+escapeHtml(a)+' → '+escapeHtml(b)+': '+(Number.isFinite(ab)?format.format(ab):"saknas")+'</strong><strong>'+escapeHtml(b)+' → '+escapeHtml(a)+': '+(Number.isFinite(ba)?format.format(ba):"saknas")+'</strong><span>Netto till '+escapeHtml(b)+': '+(Number.isFinite(ab)&&Number.isFinite(ba)?format.format(ab-ba):"saknas")+'</span>';
 $("networkStatus").textContent=year+' · '+sex+' · '+shown.length+' kommuner · '+pairs.length+' kommunpar med minst ett synligt flöde';
}
fetch("data/commuting.csv",{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("HTTP "+r.status);return r.text();}).then(t=>{data=csvParse(t);setup();}).catch(e=>{$("commutingNetwork").textContent="Kunde inte läsa pendlingsdata: "+e.message;});
})();