#!/usr/bin/env python3
"""Quality-controlled heavy traffic AADT on NVDB Trafik linework, for five municipalities."""
import json,os,sys,sqlite3,tempfile,zipfile
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from shapely.ops import unary_union
from inspect_lastkajen_norrbotten import api,BASE,PACKAGE_ID,FILE_NAME
from analyze_nvdb_attribute_diagnostics import region_geometries
from build_nvdb_five_municipalities import gpkg_geom,quote

def analyze(con,regions):
    tables=[t for t,g,s in con.execute("SELECT table_name,column_name,srs_id FROM gpkg_geometry_columns") if t.lower().endswith("_trafik")]
    if len(tables)!=1:raise ValueError("One Trafik layer required: "+str(tables))
    table=tables[0]
    cols=[r[1] for r in con.execute("PRAGMA table_info("+quote(table)+")")]
    heavy="Adt_tunga_fordon";total="Adt_samtliga_fordon"
    for field in (heavy,total):
        if field not in cols:raise ValueError("Missing field "+field)
    geocol=con.execute("SELECT column_name FROM gpkg_geometry_columns WHERE table_name=?",(table,)).fetchone()[0]
    sql="SELECT "+",".join(quote(x) for x in (geocol,heavy,total))+" FROM "+quote(table)
    sets={code:{"name":name,"records":{},"invalid":0,"unavailable":0,"conflicting":0} for code,name,*_ in regions}
    for blob,h,t in con.execute(sql):
        g=gpkg_geom(blob)
        if g is None or g.is_empty or not g.is_valid or g.geom_type not in ("LineString","MultiLineString"):continue
        try:
            hv=float(h);tv=float(t)
            valid=0<=hv<=tv and tv>0 and tv<=1000000
        except (ValueError,TypeError):valid=False
        for code,name,poly,prepared in regions:
            if not prepared.intersects(g):continue
            clipped=g.intersection(poly)
            if clipped.is_empty or clipped.length<=0:continue
            b=sets[code]
            if not valid:b["unavailable"]+=1;continue
            # Same classification and exact geometry get unioned to avoid duplicated record lengths.
            key=(hv,tv);b["records"].setdefault(key,[]).append(clipped)
    output={}
    for code,b in sets.items():
        groups={key:unary_union(lines) for key,lines in b["records"].items()}
        allroad=unary_union(list(groups.values())) if groups else None
        unique=allroad.length/1000 if allroad else 0
        summed=sum(geo.length for geo in groups.values())/1000
        overlap=max(0,summed-unique)
        # In conflicting segments different ADT reports exist; exclude these from firm vehicle-km estimates.
        conflicts=[]
        geoms=list(groups.values())
        for i in range(len(geoms)):
            for j in range(i+1,len(geoms)):
                if geoms[i].intersects(geoms[j]):
                    common=geoms[i].intersection(geoms[j])
                    if common.length>0:conflicts.append(common)
        conflicted=unary_union(conflicts) if conflicts else None
        conflict_km=(conflicted.length/1000) if conflicted else 0
        heavy_km=total_km=vehicle_km=0
        for (h,t),geo in groups.items():
            effective=geo.difference(conflicted) if conflicted else geo
            length=effective.length/1000
            heavy_km+=h*length
            total_km+=t*length
            vehicle_km+=length
        if overlap+0.01<conflict_km:raise ValueError("Overlap accounting inconsistency")
        output[code]={"name":b["name"],"traffic_mapped_unique_km":round(unique,3),
            "validated_unique_km":round(vehicle_km,3),"overlapping_conflicting_km":round(conflict_km,3),
            "unavailable_records":b["unavailable"],
            "adt_heavy_length_weighted":round(heavy_km/vehicle_km,1) if vehicle_km else None,
            "adt_all_length_weighted":round(total_km/vehicle_km,1) if vehicle_km else None,
            "heavy_share_percent":round(100*heavy_km/total_km,1) if total_km else None,
            "heavy_vehicle_km_per_day_on_covered_lines":round(heavy_km,1),
            "heavy_vehicle_km_per_year_on_covered_lines":round(heavy_km*365)}
    return output

def main():
    regions=region_geometries()
    token=api("/Identity/Login",form={"UserName":os.environ["LASTKAJEN_USERNAME"],"Password":os.environ["LASTKAJEN_PASSWORD"]}).get("access_token")
    if not token:raise RuntimeError("NVDB authentication failed")
    ticket=api("/file/GetDataPackageDownloadToken?"+urlencode({"id":PACKAGE_ID,"fileName":FILE_NAME}),bearer=token)
    if not isinstance(ticket,str):raise ValueError("No download ticket")
    with tempfile.TemporaryDirectory() as td:
        archive=Path(td)/"source.zip";size=0
        with urlopen(BASE+"/File/GetDataPackageFile?"+urlencode({"token":ticket}),timeout=180) as src,archive.open("wb") as dest:
            while chunk:=src.read(1024*1024):
                size+=len(chunk)
                if size>1500000000:raise ValueError("Archive oversized")
                dest.write(chunk)
        with zipfile.ZipFile(archive) as z:
            gpkg=[x for x in z.infolist() if not x.is_dir() and x.filename.lower().endswith(".gpkg")]
            if len(gpkg)!=1 or gpkg[0].file_size>8000000000:raise ValueError("Unexpected GPKG")
            path=Path(td)/"roads.gpkg"
            with z.open(gpkg[0]) as source,path.open("wb") as dest:
                while chunk:=source.read(1024*1024):dest.write(chunk)
            con=sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True)
            try:result=analyze(con,regions)
            finally:con.close()
    dest=Path("nvdb_output/heavy_traffic_qa.json");dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps({"status":"qa_only","source":"NVDB Lastkajen 10155, Trafik, Adt_tunga_fordon",
       "limits":"Coverage limited to roads with both heavy and total AADT; no extrapolation to municipal/private roads. Exact duplicated lines unioned, conflicting overlaps removed. Parallel carriageways are counted individually. The vehicle-km measure refers only to documented lines.",
       "municipalities":result},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Heavy traffic audit finished",list(result))
if __name__=="__main__":
    try:main()
    except Exception as ex:print("Heavy traffic QA failed:",ex,file=sys.stderr);sys.exit(1)
