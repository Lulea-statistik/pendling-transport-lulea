from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

URL="https://lanstrafikennorrbotten.se/trafikinformation"
JSON_PATH=Path("data/traffic_disruptions.json")
CSV_PATH=Path("data/traffic_disruptions.csv")
WEB_PATH=Path("docs/data/traffic_disruptions.json")

def fetch_html():
    req=Request(URL,headers={"User-Agent":"pendling-transport-lulea/1.0"})
    with urlopen(req,timeout=120) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8",errors="replace")

def clean(text):
    return re.sub(r"\s+"," ",text or "").strip()

def extract_section(soup, heading_text):
    heading=None
    for h in soup.find_all(["h2","h3"]):
        if clean(h.get_text(" ",strip=True)).casefold()==heading_text.casefold():
            heading=h
            break
    if not heading:
        return []

    nodes=[]
    for el in heading.find_all_next():
        if el is heading:
            continue
        if el.name in {"h2","h3"} and el is not heading:
            txt=clean(el.get_text(" ",strip=True))
            if txt.casefold() in {"aktuella","planerade","prenumerera på trafikinformation"}:
                break
        nodes.append(el)

    # Titles on the live page are short text blocks followed by a "Visa" button.
    candidates=[]
    for el in nodes:
        txt=clean(el.get_text(" ",strip=True))
        if not txt or txt=="Visa":
            continue
        if el.name in {"h3","h4","strong"}:
            candidates.append((el,txt))
        elif el.name in {"p","div"} and len(txt)<180:
            nxt=el.find_next()
            if nxt and clean(nxt.get_text(" ",strip=True))=="Visa":
                candidates.append((el,txt))

    # Fallback: inspect buttons named Visa and use nearest previous compact text.
    if not candidates:
        for btn in nodes:
            if clean(btn.get_text(" ",strip=True))!="Visa":
                continue
            prev=btn.find_previous()
            seen=0
            while prev and seen<8:
                txt=clean(prev.get_text(" ",strip=True))
                if txt and txt!="Visa" and len(txt)<180:
                    candidates.append((prev,txt))
                    break
                prev=prev.find_previous()
                seen+=1

    out=[]
    used=set()
    for el,title in candidates:
        if title in used:
            continue
        used.add(title)
        pieces=[]
        cur=el.find_next()
        while cur:
            txt=clean(cur.get_text(" ",strip=True))
            if cur.name in {"h2","h3","h4"} and txt and txt!=title:
                break
            if txt=="Visa":
                cur=cur.find_next()
                continue
            if txt and txt not in pieces and len(txt)<1200:
                pieces.append(txt)
            if len(" ".join(pieces))>2500:
                break
            cur=cur.find_next()
        body=clean(" ".join(pieces))
        if body.startswith(title):
            body=clean(body[len(title):])
        key=hashlib.sha1((heading_text+"|"+title+"|"+body[:300]).encode("utf-8")).hexdigest()[:16]
        line_nums=sorted(set(re.findall(r"(?i)linje\s+(\d+)",title+" "+body)))
        out.append({
            "id":key,
            "status":heading_text,
            "title":title,
            "body":body,
            "lines":line_nums,
        })
    return out

def load_existing():
    if JSON_PATH.exists():
        try:
            return json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"source":URL,"updated":None,"items":[]}

def main():
    now=datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    soup=BeautifulSoup(fetch_html(),"html.parser")
    current=extract_section(soup,"Aktuella")
    planned=extract_section(soup,"Planerade")
    live=current+planned

    existing=load_existing()
    by_id={x["id"]:x for x in existing.get("items",[])}
    live_ids={x["id"] for x in live}

    for item in live:
        old=by_id.get(item["id"])
        if old:
            old.update(item)
            old["last_seen"]=now
            old["active"]=True
        else:
            item["first_seen"]=now
            item["last_seen"]=now
            item["active"]=True
            by_id[item["id"]]=item

    for item in by_id.values():
        if item["id"] not in live_ids:
            item["active"]=False

    items=sorted(by_id.values(),key=lambda x:(not x.get("active",False),x.get("first_seen","")),reverse=False)
    out={
        "source":URL,
        "updated":now,
        "active_count":sum(1 for x in items if x.get("active")),
        "history_count":len(items),
        "items":items,
    }

    JSON_PATH.parent.mkdir(parents=True,exist_ok=True)
    WEB_PATH.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(out,ensure_ascii=False,indent=2)
    JSON_PATH.write_text(text,encoding="utf-8")
    WEB_PATH.write_text(text,encoding="utf-8")

    with CSV_PATH.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["id","status","title","body","lines","first_seen","last_seen","active"])
        w.writeheader()
        for x in items:
            row=x.copy()
            row["lines"]=";".join(row.get("lines",[]))
            w.writerow({k:row.get(k,"") for k in w.fieldnames})

    print("active",out["active_count"],"history",out["history_count"])
    for x in live[:10]:
        print(x["status"],x["title"])

if __name__=="__main__":
    main()
