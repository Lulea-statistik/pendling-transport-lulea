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
const W=1300;
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
 ["networkYear","networkSex","networkScope","networkMinimum"].forEach(id=>byId(id).addEventListener("change",()=>{positions.clear();render();}));
 byId("networkReset").addEventListener("click",()=>{positions.clear();selected="Boden";render();});
 render();
}
function calculate(){
 const year=byId("networkYear").value,sex=byId("networkSex").value,scope=byId("networkScope").value;
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
 }).filter(r=>(r.inward!==null&&r.inward>=minimum)||(r.outward!==null&&r.outward>=minimum))
 .sort((a,b)=>b.sum-a.sum||a.name.localeCompare(b.name,"sv"));
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
 const label=n.isCounty?n.name:(n.name||"");
 const split=labelLines(label),longest=Math.max(...split.map(s=>s.length));
 const labelMin=Math.max(39,longest*3.7+14);
 const scaled=n.day===null?44:36+50*Math.pow(Math.max(0,n.day)/Math.max(1,maximum),.36);
 return Math.max(labelMin,Math.min(90,scaled));
}
function layout(data){
 const center={name:"Luleå",day:data.day,isCounty:false};
 const max=Math.max(1,...[data.day,...data.partner.map(n=>n.day)].filter(x=>x!==null));
 const all=[center,...data.partner].map(n=>({...n,r:radius(n,max)}));
 center.r=all[0].r;
 const gap=18,step=Math.max(124,...all.map(n=>2*n.r+gap));
 const rows=Math.ceil((all.length-1)/2),H=Math.max(620,2*(Math.ceil(rows/2)+1)*step+130);
 all[0].x=W/2;all[0].y=H/2;
 const xLeft=210,xRight=W-210;
 all.slice(1).forEach((n,i)=>{
   const row=Math.floor(i/2),side=i%2;
   const offset=row===0?0:(Math.ceil(row/2)*step*(row%2===1?1:-1));
   const y=H/2+offset;
   const override=positions.get(n.name);
   n.x=override?override.x:side?xRight:xLeft;
   n.y=override?override.y:y;
 });
 const origin=positions.get("Luleå");
 if(origin){all[0].x=origin.x;all[0].y=origin.y;}
 return {all,H,max};
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
 '<div><span>Dagbefolkning</span><strong>'+area+'</strong></div>'+
 '<div><span>Till Luleå från '+esc(title)+'</span><strong>'+number(inward)+'</strong></div>'+
 '<div><span>Från Luleå till '+esc(title)+'</span><strong>'+number(outward)+'</strong></div>'+
 '<div><span>Netto till Luleå</span><strong>'+(inward===null||outward===null?"Saknas":fmt.format(inward-outward))+'</strong></div>'+
 '</div><p class="network-detail-note">'+esc(metric)+'</p>';
 for(const g of activeSvg.querySelectorAll(".commuting-node"))g.classList.toggle("network-selected",g.dataset.name===name);
 for(const g of activeSvg.querySelectorAll(".network-link"))g.classList.toggle("network-link-selected",g.dataset.name===name);
}
function draw(data){
 const {all,H,max}=layout(data);nodes=all;relations=data.partner;
 const svg=svgEl("svg",{viewBox:"0 0 "+W+" "+H,class:"commuting-network-svg",role:"img","aria-label":"Pendlingsflöden till och från Luleå. Dra cirklar för att ändra layout."});
 svg.style.maxHeight="none";
 const defs=svgEl("defs");
 for(const [id,color] of [["in","#317db1"],["out","#e08448"]]){
   const marker=svgEl("marker",{id:"network-"+id,viewBox:"0 0 10 10",refX:9,refY:5,markerWidth:5,markerHeight:5,orient:"auto-start-reverse"});
   marker.append(svgEl("path",{d:"M0 0 L10 5 L0 10 Z",fill:color}));defs.append(marker);
 }
 svg.append(defs);
 const links=svgEl("g",{class:"network-links"});svg.append(links);
 const nodeLayer=svgEl("g");svg.append(nodeLayer);
 const center=all[0],maxFlow=Math.max(1,...data.partner.flatMap(x=>[x.inward||0,x.outward||0]));
 function path(from,to,offset){
   const dx=to.x-from.x,dy=to.y-from.y,dist=Math.max(1,Math.hypot(dx,dy)),ux=dx/dist,uy=dy/dist,px=-uy,py=ux;
   const a={x:from.x+ux*(from.r+5),y:from.y+uy*(from.r+5)};
   const b={x:to.x-ux*(to.r+11),y:to.y-uy*(to.r+11)};
   const k=offset*29;
   return "M "+a.x+" "+a.y+" Q "+((a.x+b.x)/2+px*k)+" "+((a.y+b.y)/2+py*k)+" "+b.x+" "+b.y;
 }
 for(const item of data.partner){
   const peer=all.find(x=>x.name===item.name),group=svgEl("g",{class:"network-link","data-name":item.name,tabindex:0,role:"button","aria-label":"Visa pendlingsflöden för "+item.name});
   const title=svgEl("title");title.textContent="Till Luleå från "+item.name+": "+number(item.inward)+"; från Luleå till "+item.name+": "+number(item.outward);group.append(title);
   for(const [from,to,count,offset,color,marker] of [[peer,center,item.inward,1,"#317db1","in"],[center,peer,item.outward,-1,"#e08448","out"]]){
     if(count===null||count<data.minimum||count<=0)continue;
     const d=path(from,to,offset);
     const line=svgEl("path",{d,fill:"none",stroke:color,"stroke-width":(1.7+8*Math.sqrt(count/maxFlow)).toFixed(2),"stroke-linecap":"round",opacity:".75","marker-end":"url(#network-"+marker+")",class:"network-visible-path"});
     const hit=svgEl("path",{d,fill:"none",stroke:"transparent","stroke-width":32,class:"network-hit-path"});
     group.append(line,hit);
   }
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
     drag={name:node.name,offsetX:node.x-x,offsetY:node.y-y,startX:e.clientX,startY:e.clientY,moved:false};
     group.setPointerCapture(e.pointerId);
   });
   group.addEventListener("pointermove",e=>{
     if(!drag||drag.name!==node.name)return;
     if(Math.hypot(e.clientX-drag.startX,e.clientY-drag.startY)>4)drag.moved=true;
     if(!drag.moved)return;
     const rect=svg.getBoundingClientRect(),x=(e.clientX-rect.left)*W/rect.width+drag.offsetX,y=(e.clientY-rect.top)*H/rect.height+drag.offsetY;
     positions.set(node.name,{x:Math.max(node.r+10,Math.min(W-node.r-10,x)),y:Math.max(node.r+10,Math.min(H-node.r-10,y))});
     // Re-render all geometry against the new node position, preserving pointer stream on this SVG.
     const p=positions.get(node.name);node.x=p.x;node.y=p.y;
     circle.setAttribute("cx",p.x);circle.setAttribute("cy",p.y);
     text.querySelectorAll("tspan").forEach(t=>t.setAttribute("x",p.x));
     const tspans=text.querySelectorAll("tspan");tspans.forEach((t,i)=>t.setAttribute("y",p.y+(i===tspans.length-1?(lines.length===1?15:23):-((lines.length-1)*15)/2-7+i*15)));
     links.querySelectorAll(".network-link").forEach(g=>{
       if(g.dataset.name!==node.name&&node.name!=="Luleå")return;
       const item=relations.find(r=>r.name===g.dataset.name),peer=nodes.find(n=>n.name===g.dataset.name),parts=g.querySelectorAll("path");
       let j=0;
       for(const [from,to,count,off] of [[peer,nodes[0],item.inward,1],[nodes[0],peer,item.outward,-1]]){
         if(count===null||count<data.minimum||count<=0)continue;
         const d=path(from,to,off);parts[j++].setAttribute("d",d);parts[j++].setAttribute("d",d);
       }
     });
   });
   const finish=()=>{if(!drag)return;dragged=drag.moved;drag=null;};
   group.addEventListener("pointerup",finish);group.addEventListener("pointercancel",finish);
   nodeLayer.append(group);
 }
 activeSvg=svg;
 byId("commutingNetwork").replaceChildren(svg);
 showInfo(selected==="Luleå"||relations.some(r=>r.name===selected)?selected:(relations[0]?.name||"Luleå"));
 byId("networkStatus").textContent=data.year+" · "+data.sex+" · "+relations.length+" relationer med Luleå · blått till Luleå, orange från Luleå";
}
function render(){if(!local.length)return;draw(calculate());}
Promise.all([
 fetch("data/commuting.csv",{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("SCB-matris saknas");return r.text();}),
 fetch("data/commuting-national.json",{cache:"no-store"}).then(r=>r.ok?r.json():null).catch(()=>null)
]).then(([text,n])=>{local=csvParse(text);national=n;setup();}).catch(e=>{byId("commutingNetwork").textContent="Kunde inte läsa pendlingsdata: "+e.message;});
})();