"""SCB ArRegPend2: 14 Norrbotten municipalities versus all 290 Swedish municipalities.
Writes a separate aggregated OD file. Original Norrbotten matrix is untouched.
"""
from __future__ import annotations
import csv
import io
import json
import re
from collections import defaultdict
from pathlib import Path
from fetch_commuting import API_URL, NBR, get_json, post_json, find_var, norm, code_from_label

COUNTIES = {
 "01":"Stockholms län","03":"Uppsala län","04":"Södermanlands län",
 "05":"Östergötlands län","06":"Jönköpings län","07":"Kronobergs län",
 "08":"Kalmar län","09":"Gotlands län","10":"Blekinge län",
 "12":"Skåne län","13":"Hallands län","14":"Västra Götalands län",
 "17":"Värmlands län","18":"Örebro län","19":"Västmanlands län",
 "20":"Dalarnas län","21":"Gävleborgs län","22":"Västernorrlands län",
 "23":"Jämtlands län","24":"Västerbottens län","25":"Norrbottens län",
}
def municipal_codes(variable):
    out = []
    for v, label in zip(variable.get("values", []), variable.get("valueTexts", [])):
        raw = str(v).strip()
        code = raw if re.fullmatch(r"\d{4}", raw) else code_from_label(label)
        if code and code[:2] in COUNTIES:
            out.append((raw, code))
    return out

def query(metadata,sex,res,work,year,res_codes,work_codes):
    payload={"query":[
      {"code":sex["code"],"selection":{"filter":"item","values":sex["values"]}},
      {"code":res["code"],"selection":{"filter":"item","values":res_codes}},
      {"code":work["code"],"selection":{"filter":"item","values":work_codes}},
      {"code":year["code"],"selection":{"filter":"item","values":year["values"]}},
    ],"response":{"format":"csv"}}
    raw=post_json(API_URL,payload)
    try: dialect=csv.Sniffer().sniff(raw[:5000],delimiters=";,\t")
    except csv.Error:
      dialect=csv.excel; dialect.delimiter=";"
    reader=csv.DictReader(io.StringIO(raw),dialect=dialect)
    headers=reader.fieldnames or []
    def col(*parts):
      return next(h for h in headers if all(norm(p) in norm(h) for p in parts))
    c_sex=col("kon");c_res=col("bostad","kommun");c_work=col("arbets","kommun")
    years=[(h,int(m.group(1))) for h in headers if h not in (c_sex,c_res,c_work)
       if (m:=re.search(r"((?:19|20)\d{2})",h))]
    if not years: raise ValueError("No year columns: "+repr(headers))
    for row in reader:
      rc=code_from_label(row[c_res]);wc=code_from_label(row[c_work])
      if not (re.fullmatch(r"\d{4}",rc or "") and re.fullmatch(r"\d{4}",wc or "")): continue
      for h,y in years:
        v=str(row.get(h,"")).strip().replace(" ","").replace(",",".")
        if v in ("","..",".","-"):continue
        try: count=int(float(v))
        except ValueError:continue
        yield (y,row[c_sex],rc,wc,count)

def main():
    metadata=get_json(API_URL)
    sex=find_var(metadata,"kon")
    residence=find_var(metadata,"bostad","kommun")
    workplace=find_var(metadata,"arbets","kommun")
    year=next(v for v in metadata["variables"] if str(v.get("code","")).lower() in ("tid","time","ar","år"))
    rm=municipal_codes(residence);wm=municipal_codes(workplace)
    rr={actual:value for value,actual in rm};ww={actual:value for value,actual in wm}
    nbr_res=[rr[c] for c in NBR if c in rr];nbr_work=[ww[c] for c in NBR if c in ww]
    if len(nbr_res)!=14 or len(nbr_work)!=14 or len(rm)<290 or len(wm)<290:
      raise RuntimeError(f"Unexpected SCB geographic coverage: {len(rm)}, {len(wm)}, {len(nbr_res)}, {len(nbr_work)}")
    data=defaultdict(int)
    for direction,rv,wv in [
      ("in",[v for v,_ in rm],nbr_work),
      ("out",nbr_res,[v for v,_ in wm])
    ]:
      count=0
      for y,s,rc,wc,value in query(metadata,sex,residence,workplace,year,rv,wv):
        # Norrbotten-to-Norrbotten appears in BOTH queries; count once.
        if direction=="out" and rc in NBR and wc in NBR: continue
        if rc not in NBR and wc not in NBR: continue
        a=rc if rc in NBR else rc[:2]
        b=wc if wc in NBR else wc[:2]
        if a==b:continue
        data[(y,s,a,b)]+=value;count+=1
      print(f"{direction}: accepted {count} rows")
    result={
      "source":"SCB ArRegPend2, employed 15-74 years; housing municipality to workplace municipality",
      "scope":"All Sweden origin/destination, Norrbotten municipalities individually, other municipalities aggregated by county",
      "years":sorted({k[0] for k in data}),
      "municipalities":NBR,
      "counties":{k:v for k,v in COUNTIES.items() if k!="25"},
      "flows":[{"year":y,"sex":s,"from":a,"to":b,"count":v}
                for (y,s,a,b),v in sorted(data.items())],
    }
    output=Path("docs/data/commuting-national.json")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print(f"Wrote {len(result['flows'])} aggregated flow rows, {result['years']}")
if __name__=="__main__":main()
