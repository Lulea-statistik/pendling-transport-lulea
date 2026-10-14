/* SCB commuting star network: all visible flows have Luleå as endpoint. */
(() => {
"use strict";
const byId=id=>document.getElementById(id), fmt=new Intl.NumberFormat("sv-SE");
const FOCUS=["Luleå","Boden","Piteå","Älvsbyn","Kalix"];
const COLORS={"Luleå":"#ba3024","Boden":"#d79c14","Piteå":"#2863c9","Älvsbyn":"#149b8c","Kalix":"#8656d6"};
const esc=x=>String(x).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const ns="http://www.w3.org/2000/svg";
const svgEl=(tag,attrs={})=>{const el=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,String(v)));return el;};
let local=[],national=null,positions=new Map(),nodes=[],relations=[],selected="Boden",activeSvg=null,drag=null,dragged=false;
const W=1300,H=700;
function csvParse(raw){
 const lines=raw.replace(/^\uFEFF/,"").trim().split(/\r?\n/),head=lines.shift().split(",");
 return lines.map(line=>{const cells=[];let value="",quote=false;for(let i=0;i<line.length;i++){const ch=line[i];if(ch==='"'){if(quote&&line[i+1]==='"'){value+='"';i++;}else quote=!quote;}else if(ch===","&&!quote){cells.push(value);value="";}else value+=ch;}cells.push(value);return Object.fromEntries(head.map((h,i)=>[h,cells[i]||""]));});
}
const value=x=>x===null||x===undefined||x===""?null:Number.isFinite(Number(x))?Number(x):null;
const number=x=>x===null?"Saknas":fmt.format(x);
function setup(){
 const years=[...new Set(local.map(x=>x.year))].sort((a,b)=>+b-+a);
 const sexes=[...new Set(local.map(x=>x.sex))];
 years.forEach(y=>byId("networkYear").add(new Option(y,y)));
 byId("networkYear").value=years.includes("2024")?"2024":years[0];
 sexes.forEach(s=>byId("networkSex").add(new Option(s,s)));
 byId("networkSex").value=sexes.find(s=>s.toLowerCase().includes("tot"))||sexes[0];
 byId("networkScope").querySelector('option[value="national"]').disabled=!national;
 ["networkYear","networkSex","networkMinimum"].forEach(id=>byId(id).addEventListener("change",render));
 byId("networkScope").addEventListener("change",()=>{positions.clear();render();});
 byId("networkReset").addEventListener("click",()=>{positions.clear();selected="Boden";render();});
 render();
}
function calculate(yearOverride=null,sexOverride=null){
 const year=yearOverride||byId("networkYear").value,sex=sexOverride||byId("networkSex").value,scope=byId("networkScope").value;
 const minimum=Number(byId("networkMinimum").value),nation=scope==="national"&&national;
 const records=nation?national.flows.filter(r=>String(r.year)===year&&r.sex===sex).map(r=>({from:national.municipalities[r.from]||national.counties[r.from],to:national.municipalities[r.to]||national.counties[r.to],count:value(r.count)})):
 local.filter(r=>r.year===year&&r.sex===sex).map(r=>({from:r.residence,to:r.workplace,count:value(r.employed)}));
 const map=new Map(records.map(r=>[r.from+"|"+r.to,r.count]));
 const names=nation?[...Object.values(national.municipalities),...Object.values(national.counties)]:[...new Set(local.filter(r=>r.year===year&&r.sex===sex).flatMap(r=>[r.residence,r.workplace]))];
 const allowed=scope==="focus"?FOCUS:names;
 const localSelf=new Map(local.filter(r=>r.year===year&&r.sex===sex&&r.residence===r.workplace).map(r=>[r.workplace,value(r.employed)]));
 const external=new Set(nation?Object.values(national.counties):[]);
 const totalAt=new Map();
 for(const name of allowed){
   if(external.has(name)){totalAt.set(name,null);continue;}
   // The nationwide file includes Norrbotten-to-Norrbotten flows and all other counties into each municipality.
   // Add self employed from the original matrix only once.
   const incoming=records.filter(r=>r.to===name&&r.from!==name).reduce((s,r)=>s+(r.count||0),0);
   const self=localSelf.get(name);
   totalAt.set(name,self===null||self===undefined?null:self+incoming);
 }
 const partner=allowed.filter(n=>n!=="Luleå").map(name=>{
   const inward=map.has(name+"|Luleå")?map.get(name+"|Luleå"):null;
   const outward=map.has("Luleå|"+name)?map.get("Luleå|"+name):null;
   return {name,inward,outward,sum:(inward||0)+(outward||0),day:totalAt.get(name),isCounty:external.has(name)};
 }).sort((a,b)=>{
   // Stable reference ordering (2024, total) instead of reordering when year/sex changes.
   const ref=nation?national.flows.filter(x=>String(x.year)==="2024"&&x.sex==="totalt")
     .map(x=>({from:national.municipalities[x.from]||national.counties[x.from],to:national.municipalities[x.to]||national.counties[x.to],count:Number(x.count)||0})):
     local.filter(x=>x.year==="2024"&&x.sex==="totalt").map(x=>({from:x.residence,to:x.workplace,count:Number(x.employed)||0}));
   const sum=name=>ref.filter(x=>(x.from==="Luleå"&&x.to===name)||(x.from===name&&x.to==="Luleå")).reduce((total,x)=>total+x.count,0);
   return sum(b.name)-sum(a.name)||a.name.localeCompare(b.name,"sv");
 });
 return {year,sex,nation,partner,day:totalAt.get("Luleå"),minimum};
}
function labelLines(name){
 if(name.length<=12)return [name];
 if(name.endsWith(" län"))return [name.slice(0,-4),"län"];
 const mid=Math.floor(name.length/2),poss=[...name].map((c,i)=>i).filter(i=>i>3&&i<name.length-3&&/[ -]/.test(name[i]));
 if(poss.length){let i=poss.sort((a,b)=>Math.abs(a-mid)-Math.abs(b-mid))[0];return [name.slice(0,i),name.slice(i+1)];}
 return [name]; // fit long place names via responsive font size
}
function radius(n,maximum){
 const longest=Math.max(...labelLines(n.name).map(x=>x.length));
 const minimum=Math.max(24,Math.min(48,longest*2.65+9));
 const scaled=n.day===null?32:27+29*Math.pow(Math.max(0,n.day)/Math.max(1,maximum),.35);
 return Math.max(minimum,Math.min(64,scaled));
}
function resolveOverlaps(all){
 // Pairwise separation in 2D; includes centre and manually moved nodes.
 // In a dense national selection, shrink radii as required rather than allow overlaps.
 for(let pass=0;pass<90;pass++){
   let collisions=0;
   for(let i=0;i<all.length;i++)for(let j=i+1;j<all.length;j++){
     const a=all[i],b=all[j],dx=b.x-a.x,dy=b.y-a.y;
     const d=Math.hypot(dx,dy),needed=a.r+b.r+7;
     if(d>=needed)continue;
     collisions++;
     const ux=d>0.01?dx/d:Math.cos((i*13+j)*2.4),uy=d>0.01?dy/d:Math.sin((i*13+j)*2.4);
     const move=(needed-d)/2+0.2;
     const wa=a.name==="Luleå"?.15:1,wb=b.name==="Luleå"?.15:1,weight=wa+wb;
     a.x-=ux*move*2*wa/weight;a.y-=uy*move*2*wa/weight;
     b.x+=ux*move*2*wb/weight;b.y+=uy*move*2*wb/weight;
   }
   for(const n of all){n.x=Math.max(n.r+7,Math.min(W-n.r-7,n.x));n.y=Math.max(n.r+7,Math.min(H-n.r-7,n.y));}
   if(!collisions)break;
 }
}
function layout(data){
 // Reference values and geometry are independent of the active year/sex/threshold.
 const reference=calculate("2024","totalt");
 const max=Math.max(1,...[reference.day,...reference.partner.map(n=>n.day)].filter(x=>x!==null));
 const referenceDays=new Map(reference.partner.map(n=>[n.name,n.day]));
 referenceDays.set("Luleå",reference.day);
 const all=[{name:"Luleå",day:data.day,isCounty:false},...data.partner].map(n=>({...n,r:radius({...n,day:referenceDays.get(n.name)??null},max)}));
 const count=all.length-1;
 // With 34 nodes in a fixed 1300x700 SVG, smaller nodes are required for a collision-free view.
 const shrink=count>16?Math.max(.55,Math.sqrt(16/count)) :1;
 all.forEach((n,i)=>{n.r=Math.max(i===0?42:20,n.r*shrink);});
 all[0].x=W/2;all[0].y=H/2;
 const left=all.slice(1).filter((_,i)=>i%2===0),right=all.slice(1).filter((_,i)=>i%2===1);
 for(const [items,isRight] of [[left,false],[right,true]]){
   const levels=Math.ceil((items.length-1)/2),radius=Math.max(20,...items.map(n=>n.r));
   const spread=Math.min(106,(H/2-radius-22)/Math.max(1,levels));
   items.forEach((n,i)=>{
     const level=i===0?0:Math.ceil(i/2)*(i%2===1?-1:1),out=Math.abs(level);
     const x=(isRight?W-190:190)+(isRight?-1:1)*Math.min(115,out*28);
     const y=H/2+level*spread;
     const saved=positions.get(n.name);
     n.x=saved?saved.x:x;n.y=saved?saved.y:y;
   });
 }
 const centre=positions.get("Luleå");if(centre){all[0].x=centre.x;all[0].y=centre.y;}
 if(!positions.size){
   resolveOverlaps(all);
   all.forEach(n=>positions.set(n.name,{x:n.x,y:n.y,r:n.r}));
 } else {
   // Preserve exact centres when year, sex or threshold changes.
   for(const n of all){const p=positions.get(n.name);if(p){n.x=p.x;n.y=p.y;n.r=p.r??n.r;}}
 }
 return {all,H,max};
}

function flashDetailPanel(){
 const panel=byId("networkPair");
 if(!panel)return;
 panel.classList.remove("network-detail-flash");
 void panel.offsetWidth;
 panel.classList.add("network-detail-flash");
}

function showInfo(name){
 const item=relations.find(r=>r.name===name),node=nodes.find(n=>n.name===name);
 if(!node)return;
 selected=name;
 const inward=item?.inward??null,outward=item?.outward??null;
 const title=node.name;
 const metric=node.isCounty?"Dagbefolkning i hela länet är inte tillgänglig i denna fil.":"Sysselsatta med arbetsställe i kommunen (inklusive personer som bor och arbetar där).";
 const area=node.isCounty?"Ej tillgänglig":number(node.day);
 byId("networkPair").innerHTML='<div class="network-detail-title">'+esc(title)+'</div><div class="network-detail-grid">'+
 '<div><span>Summerat flöde</span><strong>'+number(inward===null&&outward===null?null:(inward||0)+(outward||0))+'</strong></div>'+
 '<div><span>Till Luleå från '+esc(title)+'</span><strong>'+number(inward)+'</strong></div>'+
 '<div><span>Från Luleå till '+esc(title)+'</span><strong>'+number(outward)+'</strong></div>'+
 '<div><span>Netto till Luleå</span><strong>'+(inward===null||outward===null?"Saknas":fmt.format(inward-outward))+'</strong></div>'+
 '</div><p class="network-detail-note">'+esc(metric)+'</p>';
 for(const g of activeSvg.querySelectorAll(".commuting-node"))g.classList.toggle("network-selected",g.dataset.name===name);
 for(const g of activeSvg.querySelectorAll(".network-link"))g.classList.toggle("network-link-selected",g.dataset.name===name);
 flashDetailPanel();
}
function draw(data){
 const {all,H,max}=layout(data);nodes=all;relations=data.partner;
 const svg=svgEl("svg",{viewBox:"0 0 "+W+" "+H,class:"commuting-network-svg",role:"img","aria-label":"Pendlingsflöden till och från Luleå. Dra cirklar för att ändra layout."});
 svg.style.maxHeight="none";
 const links=svgEl("g",{class:"network-links"});svg.append(links);
 const nodeLayer=svgEl("g");svg.append(nodeLayer);
 const center=all[0],maxFlow=Math.max(1,...data.partner.flatMap(x=>[x.inward||0,x.outward||0]));
 function segment(from,to){
   const dx=to.x-from.x,dy=to.y-from.y,d=Math.max(.01,Math.hypot(dx,dy));
   const ux=dx/d,uy=dy/d;
   return {x1:from.x+ux*(from.r+5),y1:from.y+uy*(from.r+5),x2:to.x-ux*(to.r+5),y2:to.y-uy*(to.r+5)};
 }
 function diamond(p,size){
   const mx=(p.x1+p.x2)/2,my=(p.y1+p.y2)/2,angle=Math.atan2(p.y2-p.y1,p.x2-p.x1);
   const ux=Math.cos(angle),uy=Math.sin(angle),px=-uy,py=ux;
   return [[mx+ux*size,my+uy*size],[mx+px*size*.72,my+py*size*.72],
           [mx-ux*size,my-uy*size],[mx-px*size*.72,my-py*size*.72]].map(a=>a.join(",")).join(" ");
 }
 function updateLink(group,peer){
   const p=segment(nodes[0],peer);
   for(const el of group.querySelectorAll("line")){
     for(const k of ["x1","y1","x2","y2"])el.setAttribute(k,p[k]);
   }
   const poly=group.querySelector("polygon");
   if(poly)poly.setAttribute("points",diamond(p,Number(poly.dataset.size)));
 }
 for(const item of data.partner){
   const peer=all.find(x=>x.name===item.name),group=svgEl("g",{class:"network-link","data-name":item.name,tabindex:0,role:"button","aria-label":"Visa båda pendlingsriktningarna för "+item.name});
   const title=svgEl("title");title.textContent="Till Luleå från "+item.name+": "+number(item.inward)+"; från Luleå till "+item.name+": "+number(item.outward);group.append(title);
   if(item.inward<data.minimum && item.outward<data.minimum)continue;
   const p=segment(center,peer),both=(item.inward||0)+(item.outward||0);
   const width=(2+9*Math.sqrt(both/(maxFlow*2))).toFixed(2);
   const line=svgEl("line",{...p,stroke:"#587baf","stroke-width":width,"stroke-linecap":"round",opacity:".8",class:"network-visible-path"});
   const size=Math.max(8,Number(width)*1.35);
   const rhombus=svgEl("polygon",{points:diamond(p,size),fill:"#587baf",opacity:".92",class:"network-mid-diamond","data-size":size});
   const hit=svgEl("line",{...p,stroke:"transparent","stroke-width":34,class:"network-hit-path"});
   group.append(line,rhombus,hit);
   group.addEventListener("click",()=>showInfo(item.name));
   group.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();showInfo(item.name);}});
   links.append(group);
 }
 for(const node of all){
   const group=svgEl("g",{class:"commuting-node","data-name":node.name,tabindex:0,role:"button","aria-label":"Visa dagbefolkning och pendling för "+node.name});
   const circle=svgEl("circle",{cx:node.x,cy:node.y,r:node.r,fill:COLORS[node.name]||(node.isCounty?"#7b8798":"#617086"),stroke:"#fff","stroke-width":3});
   group.append(circle);
   const text=svgEl("text",{"text-anchor":"middle",fill:"#fff","font-weight":700,"pointer-events":"none"});
   const lines=labelLines(node.name);
   const font=Math.max(10,Math.min(16,(node.r*1.65)/Math.max(...lines.map(l=>l.length)) * 1.6));
   lines.forEach((line,i)=>{const t=svgEl("tspan",{x:node.x,y:node.y-((lines.length-1)*15)/2-7+i*15,"font-size":font});t.textContent=line;text.append(t);});
   const amount=svgEl("tspan",{x:node.x,y:node.y+((lines.length===1)?15:23),"font-size":12,"font-weight":500});
   amount.textContent=node.isCounty?"Län":number(node.day);
   text.append(amount);group.append(text);
   const tooltip=svgEl("title");tooltip.textContent=node.name+" – "+(node.isCounty?"regional pendlingsgrupp":"dagbefolkning: "+number(node.day))+". Klicka för detaljer; dra för att flytta.";group.append(tooltip);
   group.addEventListener("click",()=>{if(!dragged)showInfo(node.name);dragged=false;});
   group.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();showInfo(node.name);}});
   group.addEventListener("pointerdown",e=>{
     if(e.button!==0)return;e.preventDefault();
     const rect=svg.getBoundingClientRect(),x=(e.clientX-rect.left)*W/rect.width,y=(e.clientY-rect.top)*H/rect.height;
     drag={name:node.name,offsetX:node.x-x,offsetY:node.y-y,startX:e.clientX,startY:e.clientY,moved:false,lastX:e.clientX,lastY:e.clientY,lastTime:e.timeStamp};
     group.classList.add("network-dragging");
     group.setPointerCapture(e.pointerId);
   });
   group.addEventListener("pointermove",e=>{
     if(!drag||drag.name!==node.name)return;
     if(Math.hypot(e.clientX-drag.startX,e.clientY-drag.startY)>4)drag.moved=true;
     if(!drag.moved)return;
     const dt=Math.max(8,e.timeStamp-drag.lastTime),speed=Math.hypot(e.clientX-drag.lastX,e.clientY-drag.lastY)/dt;
     drag.lastX=e.clientX;drag.lastY=e.clientY;drag.lastTime=e.timeStamp;
     const intensity=Math.min(1,speed/2);
     group.style.setProperty("--drag-blur",(9+23*intensity).toFixed(1)+"px");
     group.style.setProperty("--drag-glow",(0.18+0.62*intensity).toFixed(2));
     group.style.setProperty("--drag-scale",(1.03+0.09*intensity).toFixed(3));
     const rect=svg.getBoundingClientRect(),x=(e.clientX-rect.left)*W/rect.width+drag.offsetX,y=(e.clientY-rect.top)*H/rect.height+drag.offsetY;
     positions.set(node.name,{x:Math.max(node.r+10,Math.min(W-node.r-10,x)),y:Math.max(node.r+10,Math.min(H-node.r-10,y)),r:node.r});
     // Re-render all geometry against the new node position, preserving pointer stream on this SVG.
     const p=positions.get(node.name);node.x=p.x;node.y=p.y;
     circle.setAttribute("cx",p.x);circle.setAttribute("cy",p.y);
     text.querySelectorAll("tspan").forEach(t=>t.setAttribute("x",p.x));
     const tspans=text.querySelectorAll("tspan");tspans.forEach((t,i)=>t.setAttribute("y",p.y+(i===tspans.length-1?(lines.length===1?15:23):-((lines.length-1)*15)/2-7+i*15)));
     links.querySelectorAll(".network-link").forEach(g=>{
       if(g.dataset.name!==node.name&&node.name!=="Luleå")return;
       const peer=nodes.find(n=>n.name===g.dataset.name);
       updateLink(g,peer);
     });
   });
   const finish=()=>{if(!drag)return;dragged=drag.moved;drag=null;group.classList.remove("network-dragging");group.style.removeProperty("--drag-blur");group.style.removeProperty("--drag-glow");group.style.removeProperty("--drag-scale");};
   group.addEventListener("pointerup",finish);group.addEventListener("pointercancel",finish);
   nodeLayer.append(group);
 }
 activeSvg=svg;
 byId("commutingNetwork").replaceChildren(svg);
 showInfo(selected==="Luleå"||relations.some(r=>r.name===selected)?selected:(relations[0]?.name||"Luleå"));
 byId("networkStatus").textContent=data.year+" · "+data.sex+" · "+relations.length+" relationer med Luleå · dubbelriktade pilar; klicka för båda flödena";
}
function render(){if(!local.length)return;draw(calculate());}
Promise.all([
 fetch("data/commuting.csv",{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("SCB-matris saknas");return r.text();}),
 fetch("data/commuting-national.json",{cache:"no-store"}).then(r=>r.ok?r.json():null).catch(()=>null)
]).then(([text,n])=>{local=csvParse(text);national=n;setup();}).catch(e=>{byId("commutingNetwork").textContent="Kunde inte läsa pendlingsdata: "+e.message;});
})();