// Jämförelse baserad på redan publicerad årsstatistik från NVDB, inte segmentgeometrier.
(async function(){
 const root=document.getElementById("nvdbCompare");if(!root)return;
 const select=document.getElementById("nvdbCompareYear");
 const type=document.getElementById("nvdbCompareType");
 const status=document.getElementById("nvdbCompareStatus");
 try{
  const response=await fetch("data/nvdb.json",{cache:"no-store"});
  if(!response.ok)throw new Error("HTTP "+response.status);
  const data=await response.json();
  const years=[...new Set(Object.values(data).flatMap(d=>d.years||[]))].sort((a,b)=>b-a);
  years.forEach(y=>{const o=document.createElement("option");o.value=y;o.textContent=y;select.appendChild(o)});
  const fmt=new Intl.NumberFormat("sv-SE",{maximumFractionDigits:1});
  function render(){
   root.replaceChildren();
   const dataset=type.value, year=Number(select.value);
   const section=data[dataset];if(!section)return;
   const factor=section.unit==="m"?1/1000:1;
   const rows=section.rows.filter(r=>Number(r.year)===year).map(r=>({
    name:r.municipality,
    value:Number(r.total)*factor,
    state:Number(r.state)*factor,
    municipal:Number(r.municipal)*factor,
    private:Number(r.private)*factor
   })).filter(r=>Number.isFinite(r.value)).sort((a,b)=>b.value-a.value);
   status.textContent=rows.length+" kommuner · "+year+" · kilometer vägnät. Jämförelse av total längd, inte nätets täthet.";
   if(!rows.length){root.textContent="Ingen statistik för detta år.";return;}
   const max=Math.max(...rows.map(r=>r.value),1);
   rows.forEach(r=>{
    const item=document.createElement("div");
    item.className="bar-row";
    const label=document.createElement("span");label.className="bar-name";label.textContent=r.name;
    const track=document.createElement("div");track.className="bar-track";
    const bar=document.createElement("i");bar.style.width=(100*r.value/max)+"%";track.appendChild(bar);
    const amount=document.createElement("strong");amount.textContent=fmt.format(r.value)+" km";
    item.title=r.name+" ("+year+"): enskild "+fmt.format(r.private)+", kommunal "+fmt.format(r.municipal)+", statlig "+fmt.format(r.state)+" km";
    item.append(label,track,amount);root.appendChild(item);
   });
  }
  select.addEventListener("change",render);type.addEventListener("change",render);render();
 }catch(err){status.textContent="Kunde inte läsa jämförelsedata: "+err.message;}
})();
