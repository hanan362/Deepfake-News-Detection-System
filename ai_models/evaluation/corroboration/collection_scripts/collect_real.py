import urllib.request, xml.etree.ElementTree as ET, json, random, re
FEEDS={"dawn.com":"https://www.dawn.com/feeds/home","bbc.com":"https://feeds.bbci.co.uk/news/world/rss.xml","aljazeera.com":"https://www.aljazeera.com/xml/rss/all.xml",
"nytimes.com":"https://rss.nytimes.com/services/xml/rss/nyt/World.xml","theguardian.com":"https://www.theguardian.com/world/rss","npr.org":"https://feeds.npr.org/1001/rss.xml",
"tribune.com.pk":"https://tribune.com.pk/feed/home","thehindu.com":"https://www.thehindu.com/news/international/feeder/default.rss"}
random.seed(7)
out=[]
for dom,url in FEEDS.items():
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
        root=ET.fromstring(urllib.request.urlopen(req,timeout=25).read())
        titles=[(i.findtext("title") or "").strip() for i in root.iter("item")]
        titles=[t for t in titles if 35<=len(t)<=140 and not t.lower().startswith(("live","watch","podcast","quiz"))]
        print(dom,len(titles))
        for t in random.sample(titles,min(6,len(titles))): out.append({"outlet":dom,"headline":t})
    except Exception as e: print(dom,"ERR",str(e)[:80])
json.dump(out,open("real_headlines.json","w"),indent=1,ensure_ascii=False)
print(len(out))
