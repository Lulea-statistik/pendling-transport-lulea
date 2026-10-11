(()=>{
const root=document.getElementById('roadStandardByClass');if(!root)return;
const E=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e};
let data,area='2580',measure='width';
const fmt=v=>Number(v).toLocaleString('sv-SE',{maximumFractionDigits:1,minimumFractionDigits:1});
function draw(){
root.replaceChildren();root.append(E('h2','Datatäckning efter funktionell vägklass'));
if(!data){root.append(E('p','Väntar på sammanställning av NVDB:s klassvisa kvalitetstal.'));return;}
const controls=E('div');controls.className='controls';const geo=E('select');
[['FA','Luleå FA-region'],...Object.entries(data.municipalities).map(([key,m])=>[key,m.name])].forEach(([v,n])=>{let o=E('option',n);o.value=v;geo.append(o)});geo.value=area;geo.onchange=()=>{area=geo.value;draw()};let l=E('label','Kommun ');l.append(geo);controls.append(l);
const sel=E('select');[['width','Vägbredd'],['lanes','Antal körfält']].forEach(([v,n])=>{let o=E('option',n);o.value=v;sel.append(o)});sel.value=measure;sel.onchange=()=>{measure=sel.value;draw()};l=E('label','Attribut ');l.append(sel);controls.append(l);root.append(controls);
const members=area==='FA'?Object.values(data.municipalities):[data.municipalities[area]];
const classes={};
for(const m of members){for(const [k,v] of Object.entries(m.variables[measure])){let b=classes[k]||(classes[k]={total:0,known:0,absent:0});b.total+=v.class_km;b.known+=v.known_km;b.absent+=v.no_attribute_km}}
const wrapper=E('div');wrapper.style.cssText='display:grid;gap:12px;margin-top:14px';
for(let i=0;i<=9;i++){const v=classes[i];if(!v||v.total<=0)continue;const part=E('div');const share=100*v.known/v.total;
part.append(E('div','Vägklass '+i+' — '+fmt(share)+' % med dokumenterat attribut ('+fmt(v.known)+' av '+fmt(v.total)+' km)'));
const bar=E('div');bar.style.cssText='display:flex;height:16px;background:#dbe2ea;border-radius:6px;overflow:hidden';
const fill=E('div');fill.style.cssText='width:'+share.toFixed(2)+'%;height:100%;background:#517f9e';bar.append(fill);part.append(bar);wrapper.append(part)}
root.append(wrapper);const p=E('p','Beräkningen avser registrerat, giltigt attribut på exakt sammanfallande geometri. Omatchat betyder inte säkert att uppgiften saknas i NVDB på en närliggande väglinje. Andelarna är längdvägda och ska inte förväxlas med antal vägar.');p.className='source-note';root.append(p)
}
fetch('data/nvdb-road-standard-by-class.json').then(r=>{if(!r.ok)throw Error('not found');return r.json()}).then(v=>{data=v;draw()}).catch(()=>{root.append(E('p','Klassvis datafil kunde inte laddas.'))});draw()
})();