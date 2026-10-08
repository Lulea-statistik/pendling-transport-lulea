from urllib.request import Request,urlopen
from urllib.parse import quote

queries=[
 "t1004|antolyckdsl|antpersd|antperss|antpersl|antdslper100000|ar:2020,2021,2022,2023,2024,2025|kommun:2580",
 "t1004|antolyckdsl|antpersd|antperss|antpersl|antdslper100000|ar|kommun:2580",
 "t1004|antolyckdsl|ar:2025|kommun:2580",
]
for q in queries:
    url="https://api.trafa.se/api/data?query="+quote(q,safe="|:,")+"&lang=sv"
    print("QUERY",q)
    try:
        req=Request(url,headers={"User-Agent":"pendling-transport-lulea/1.0","Accept":"application/json"})
        with urlopen(req,timeout=120) as r:
            data=r.read()
            print("STATUS",r.status,"TYPE",r.headers.get("content-type"),"LEN",len(data))
            print(data[:5000].decode(r.headers.get_content_charset() or "utf-8",errors="replace"))
    except Exception as e:
        print("ERROR",repr(e))
