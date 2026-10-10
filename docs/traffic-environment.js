
(()=>{
 const groups={
 walk:{name:"Fotgängare",description:"Passager över bilvägar, farthinder, skyltad hastighet och sammanhängande gångstråk påverkar om en sträcka är framkomlig och attraktiv. Trafiksäkerhetsklass mäter inte antalet gående.",factors:[
 ["GCM-passager","Platser där gång-, cykel- och mopedtrafik korsar bilväg; klassificera säkerhet och barriärer."],
 ["Hastighetsgräns","Lägre tillåten hastighet kan påverka korsningsmiljö och trygghet, men visar inte faktisk hastighet."],
 ["Farthinder","Identifiera fysiska hastighetsdämpande åtgärder."],
 ["Gångnät och korsningspunkter","Förbindelser och omvägar kräver ett gångbart nätverk; GCM-punkter ensamma räcker inte."]
 ]},
 cycle:{name:"Cyklister",description:"Sammanhängande cykelstråk, korsningars utformning, barriärer och färdriktningar är viktiga. Ruttanalys kräver en riktad cykelgraf och validerade kopplingar.",factors:[
 ["Cykelnät","Undersök var cykelbara sträckor finns och om länkarna hänger samman."],
 ["GCM-passager","Identifiera korsningar där säkerhetsklass och barriärer påverkar cyklisternas vägval."],
 ["Hastighetsgräns och farthinder","Undersök miljön där cykeltrafik möter motorfordon."],
 ["Färdriktning","Biltrafikens enkelriktning gäller inte nödvändigtvis cyklister; lokala regler måste verifieras."]
 ]},
 motor:{name:"Bilar och andra motorfordon",description:"ÅDT kan visa fordonsvolym där mätning eller skattning finns. Hastighet, enkelriktning, vägklass och farthinder används som nätverksattribut, inte som direkta mått på flödet.",factors:[
 ["Årsmedeldygnstrafik (ÅDT)","Identifiera belastade vägavsnitt; skilj personbilar, tunga fordon och andra slag endast där data medger det."],
 ["Hastighetsgräns","Använd som regelattribut för restid och vägval, inte som faktiskt uppmätt färdhastighet."],
 ["Enkelriktning / förbjuden färdriktning","Riktade vägkanter behövs för korrekt körbarhets- och ruttanalys."],
 ["Funktionell vägklass och farthinder","Undersök hur vägnätets hierarki och lokala begränsningar styr alternativa rutter."]
 ]}
 };
 function render(){
 const mode=document.getElementById("trafficMode")?.value||"walk",g=groups[mode],root=document.getElementById("trafficFactors");
 if(!root)return;
 document.getElementById("trafficModeHeading").textContent=g.name;
 document.getElementById("trafficModeDescription").textContent=g.description;
 root.replaceChildren();
 g.factors.forEach(([title,description])=>{
 const article=document.createElement("article"),h=document.createElement("h3"),p=document.createElement("p");
 h.textContent=title;p.textContent=description;article.append(h,p);root.append(article);
 });
 }
 document.getElementById("trafficMode")?.addEventListener("change",render);render();
})();
