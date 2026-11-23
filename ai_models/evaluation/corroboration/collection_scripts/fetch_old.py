import urllib.request, urllib.parse, urllib.error, xml.etree.ElementTree as ET, json, time, re
items=json.load(open("sets_old.json"))
def strip_outlet(title,outlet):
    if outlet and title.endswith(" - "+outlet): return title[:-len(outlet)-3]
    return re.sub(r"\s+-\s+[^-]{2,40}$","",title)
def search(q,n=12):
    url="https://news.google.com/rss/search?"+urllib.parse.urlencode({"q":q,"hl":"en-US","gl":"US","ceid":"US:en"})
    for attempt in range(4):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
            root=ET.fromstring(urllib.request.urlopen(req,timeout=25).read()); break
        except urllib.error.HTTPError as e:
            if e.code in (429,503): time.sleep(8*(attempt+1)); continue
            raise
    out=[]
    for it in root.iter("item"):
        s=it.find("source"); t=it.findtext("title") or ""
        name=s.text if s is not None else None
        out.append({"title":strip_outlet(t,name),"domain":(s.get("url") if s is not None else None),"outlet":name,"pubDate":it.findtext("pubDate")})
        if len(out)>=n: break
    return out
prev={}
res={}
for i,x in enumerate(items):
    if x["id"] in prev and prev[x["id"]].get("results"):
        res[x["id"]]=prev[x["id"]]; continue
    try: x["results"]=search(x["headline"])
    except Exception as e: x["results"]=None; x["error"]=str(e)[:100]
    res[x["id"]]=x; print(i,x["id"],len(x["results"] or []),flush=True)
    json.dump(list(res.values()),open("results_old.json","w"),indent=1,ensure_ascii=False); time.sleep(2.0)
print("DONE")
