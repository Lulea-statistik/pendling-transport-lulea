import os,json,sys
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError,URLError
from datetime import datetime,timezone

BASE="https://lastkajen.trafikverket.se/api"
def get(path,token=None,form=None):
    headers={"Accept":"application/json"}
    payload=urlencode(form).encode() if form is not None else None
    if form is not None: headers["Content-Type"]="application/x-www-form-urlencoded"
    if token: headers["Authorization"]="Bearer "+token
    try:
        with urlopen(Request(BASE+path,data=payload,headers=headers),timeout=45) as resp:
            raw=resp.read(20000001)
    except HTTPError as ex: raise RuntimeError("HTTP "+str(ex.code)) from None
    except URLError: raise RuntimeError("Connection failed") from None
    if len(raw)>20000000: raise RuntimeError("Response too large")
    return json.loads(raw.decode("utf-8"))

def main():
    user=os.getenv("LASTKAJEN_USERNAME")
    password=os.getenv("LASTKAJEN_PASSWORD")
    if not user or not password: raise RuntimeError("Configure both Lastkajen secrets first")
    login=get("/Identity/Login",form={"UserName":user,"Password":password})
    if not isinstance(login,dict) or not login.get("access_token"):
        raise RuntimeError("Login response missing access_token")
    token=login["access_token"]
    packages=get("/DataPackage/GetPublishedDataPackages",token)
    if not isinstance(packages,list): raise RuntimeError("Unexpected package response")
    limit=int(os.getenv("LASTKAJEN_PACKAGE_LIMIT","0"))
    if not 0<=limit<=10000: raise RuntimeError("Invalid package limit")
    records=[]
    failures=[]
    for p in packages[:limit or None]:
        if not isinstance(p,dict) or "id" not in p: continue
        record={"id":p.get("id"),"name":p.get("name"),"description":p.get("description"),
                "published":p.get("published"),"source_folder":p.get("sourceFolder"),
                "target_folder":p.get("targetFolder"),"files":[]}
        try:
            files=get("/DataPackage/GetDataPackageFiles?"+urlencode({"id":p["id"]}),token)
            if not isinstance(files,list): raise RuntimeError("Unexpected file response")
            record["files"]=[{"name":f.get("name"),"size":f.get("size"),
                "date_time":f.get("dateTime"),"is_folder":f.get("isFolder")}
                for f in files if isinstance(f,dict)]
        except (RuntimeError,ValueError,TypeError):
            record["file_listing_failed"]=True
            failures.append(str(p["id"]))
        records.append(record)
    output={"retrieved_utc":datetime.now(timezone.utc).isoformat(),
        "source":"Trafikverket Lastkajen API","inventory_only":True,
        "total_packages":len(packages),"inspected_packages":len(records),
        "failed_file_listing_ids":failures,"packages":records}
    with open("lastkajen_inventory.json","w",encoding="utf-8") as fp:
        json.dump(output,fp,ensure_ascii=False,indent=2)
    print("Inventory complete:",len(records),"packages,",len(failures),"file-list errors.")
if __name__=="__main__":
    try: main()
    except Exception:
        # Avoid printing raw API responses/URLs/credentials in public job logs.
        print("Lastkajen inventory failed. Check credentials, API availability and 2023 guide compatibility.",file=sys.stderr)
        sys.exit(1)
