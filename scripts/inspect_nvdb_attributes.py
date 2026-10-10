#!/usr/bin/env python3
"""Inspect NVDB field definitions and small value samples. Never publish raw geometries."""
import json, os, sqlite3, sys, tempfile, zipfile
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from inspect_lastkajen_norrbotten import api, BASE, PACKAGE_ID, FILE_NAME

KEYWORDS = ("Trafik", "Hastighetsgrans", "ForbjudenFardriktning", "GCM_passage",
            "CykelVgsKat", "GCM_vagtyp", "Farthinder", "FunkVagklass", "Vagbredd", "Vagtrafiknat")
MAX_ZIP = 1_500_000_000
def quote(name): return '"' + name.replace('"','""') + '"'
def inspect(path):
    con=sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True)
    try:
        all_tables={r[0]:r[1] for r in con.execute("SELECT table_name,srs_id FROM gpkg_contents")}
        selected={name:epsg for name,epsg in all_tables.items() if any(k.lower() in name.lower() for k in KEYWORDS)}
        result=[]
        for name,srs in selected.items():
            colinfo=con.execute("PRAGMA table_info("+quote(name)+")").fetchall()
            geom=[x[0] for x in con.execute("SELECT column_name FROM gpkg_geometry_columns WHERE table_name=?",(name,))]
            names=[c[1] for c in colinfo]
            cols=[{"name":c[1],"type":c[2],"primary_key":bool(c[5])} for c in colinfo]
            # No geometry values are retrieved, even in the sample.
            sample_cols=[x for x in names if x not in geom][:15]
            samples=[]
            if sample_cols:
                q="SELECT "+",".join(quote(c) for c in sample_cols)+" FROM "+quote(name)+" LIMIT 3"
                for row in con.execute(q):
                    samples.append({col: (str(v)[:120] if v is not None else None) for col,v in zip(sample_cols,row)})
            result.append({"table":name,"srs_id":srs,"fields":cols,"geometry_fields":geom,
                           "row_count":con.execute("SELECT COUNT(*) FROM "+quote(name)).fetchone()[0],
                           "sample_attributes":samples})
        if not result: raise RuntimeError("No expected NVDB tables found")
        return result
    finally:con.close()
def main():
    user=os.environ.get("LASTKAJEN_USERNAME");password=os.environ.get("LASTKAJEN_PASSWORD")
    if not user or not password:raise RuntimeError("Missing credentials")
    login=api("/Identity/Login",form={"UserName":user,"Password":password})
    bearer=login.get("access_token")
    if not bearer:raise RuntimeError("Missing access token")
    ticket=api("/file/GetDataPackageDownloadToken?"+urlencode({"id":PACKAGE_ID,"fileName":FILE_NAME}),bearer=bearer)
    if not isinstance(ticket,str):raise RuntimeError("Unexpected token response")
    with tempfile.TemporaryDirectory() as tmp:
        archive=Path(tmp)/"source.zip"
        url=BASE+"/File/GetDataPackageFile?"+urlencode({"token":ticket})
        size=0
        with urlopen(url,timeout=180) as response,archive.open("wb") as output:
            while chunk:=response.read(1024*1024):
                size+=len(chunk)
                if size>MAX_ZIP:raise RuntimeError("Source ZIP exceeds 1.5 GB")
                output.write(chunk)
        report={"source":"Trafikverket Lastkajen, Norrbottens lan","package_id":PACKAGE_ID,
                "zip_bytes":size,"tables":[]}
        with zipfile.ZipFile(archive) as z:
            gpkg_files=[f for f in z.infolist() if f.filename.lower().endswith(".gpkg") and not f.is_dir()]
            if len(gpkg_files)!=1:raise RuntimeError("Expected exactly one GeoPackage")
            f=gpkg_files[0]
            if f.file_size>8_000_000_000:raise RuntimeError("GPKG too large")
            db=Path(tmp)/"data.gpkg"
            with z.open(f) as src,db.open("wb") as dest:
                while chunk:=src.read(1024*1024):dest.write(chunk)
            report["tables"]=inspect(db)
        Path("nvdb_field_inventory.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Inspected",len(report["tables"]),"NVDB layers (attributes only)")
if __name__=="__main__":
    try:main()
    except Exception as ex:
        print("NVDB attribute inspection failed:",str(ex),file=sys.stderr)
        sys.exit(1)
