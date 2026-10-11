#!/usr/bin/env python3
"""Audit NVDB Trafik attribute definitions before cross-year freight comparisons.

Produces only schema/value diagnostics, never assumes any date field exists.
"""
import json,os,sqlite3,tempfile,zipfile
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode
from inspect_lastkajen_norrbotten import api,BASE,PACKAGE_ID,FILE_NAME

from build_nvdb_five_municipalities import quote
def main():
    bearer=api("/Identity/Login",form={"UserName":os.environ["LASTKAJEN_USERNAME"],"Password":os.environ["LASTKAJEN_PASSWORD"]}).get("access_token")
    if not bearer:raise ValueError("Authentication failed")
    ticket=api("/file/GetDataPackageDownloadToken?"+urlencode({"id":PACKAGE_ID,"fileName":FILE_NAME}),bearer=bearer)
    with tempfile.TemporaryDirectory() as td:
        zpath=Path(td)/"source.zip";size=0
        with urlopen(BASE+"/File/GetDataPackageFile?"+urlencode({"token":ticket}),timeout=180) as src,zpath.open("wb") as out:
            while block:=src.read(1048576):
                size+=len(block)
                if size>1500000000:raise ValueError("Download too large")
                out.write(block)
        with zipfile.ZipFile(zpath) as z:
            gpkg=[f for f in z.infolist() if f.filename.endswith(".gpkg") and not f.is_dir()]
            if len(gpkg)!=1 or gpkg[0].file_size>8000000000:raise ValueError("Unexpected geodata")
            path=Path(td)/"source.gpkg"
            with z.open(gpkg[0]) as ins,path.open("wb") as out:
                while block:=ins.read(1048576):out.write(block)
            con=sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True)
            try:
                layers=[t for t,g,s in con.execute("SELECT table_name,column_name,srs_id FROM gpkg_geometry_columns") if t.lower().endswith("_trafik")]
                if len(layers)!=1:raise ValueError("Trafik layer count not 1")
                table=layers[0];fields=[{"name":r[1],"type":r[2]} for r in con.execute("PRAGMA table_info("+quote(table)+")")]
                candidates=[f["name"] for f in fields if any(term in f["name"].lower() for term in ("ar","år","datum","mat","ref","period","fordon","körbana","riktning","klass","falt","tid"))]
                samples={}
                for col in candidates:
                    rows=con.execute("SELECT "+quote(col)+",count(*) n FROM "+quote(table)+" GROUP BY "+quote(col)+" ORDER BY n DESC LIMIT 12").fetchall()
                    samples[col]=[{"value":str(v)[:100] if v is not None else None,"features":count} for v,count in rows]
                record_count=con.execute("SELECT count(*) FROM "+quote(table)).fetchone()[0]
            finally:con.close()
    result={"source":"NVDB Lastkajen package 10155","table":table,"record_count":record_count,
        "fields":fields,"candidate_attribute_distributions":samples,
        "status":"schema_audit_only",
        "caution":"Variable names and values alone do not prove temporal validity or equivalence with SCB truck definition."}
    dest=Path("nvdb_output/heavy_traffic_schema_audit.json");dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Audited",table,record_count,"records",len(fields),"fields")
if __name__=="__main__":main()
