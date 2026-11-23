import json, re
real=json.load(open("real_headlines.json"))
SUBS=[("Karachi","Lahore"),("Lahore","Karachi"),("Pakistan","India"),("India","Pakistan"),("Iran","Iraq"),("Russia","China"),("Indonesian","Malaysian"),
("South Africa","Nigeria"),("Gaza","Beirut"),("Israel","Egypt"),("US firms","UK firms"),("UK","France"),("France","Spain"),("Germany","Italy"),
("killed","rescued"),("passes away","is released from hospital"),("sentenced","acquitted"),("threatens","welcomes"),("rises","falls"),("falls","rises"),
("wins","loses"),("loses","wins"),("approves","rejects"),("rejects","approves"),("bans","allows"),("arrested","released"),("resigns","is re-elected")]
def perturb(h):
    m=re.search(r"\b(\d[\d,\.]*)\b",h)
    if m and not re.match(r"^(19|20)\d\d$",m.group(1)):
        try:
            n=float(m.group(1).replace(",","")); new=str(int(n*3+7)) if n==int(n) else str(round(n*3+7,1))
            return h.replace(m.group(1),new,1),"number"
        except: pass
    for a,b in SUBS:
        if re.search(r"\b"+re.escape(a)+r"\b",h): return re.sub(r"\b"+re.escape(a)+r"\b",b,h,count=1),"swap:"+a
    return None,None
items=[]
for i,r in enumerate(real): items.append({"id":f"R{i:02d}","kind":"authentic","headline":r["headline"],"own_outlet":r["outlet"]})
k=0
for i,r in enumerate(real):
    p,how=perturb(r["headline"])
    if p and p!=r["headline"]:
        items.append({"id":f"D{k:02d}","kind":"distorted","headline":p,"own_outlet":None,"derived_from":r["headline"],"how":how}); k+=1
INV=["Government announces free electricity for all households from next month",
"NASA confirms signal from an alien civilisation detected near a neighbouring star",
"State Bank cuts its policy rate to 2 percent in surprise emergency meeting",
"WHO declares a new pandemic after a mystery virus spreads across five Asian cities",
"Cricket board bans all franchise leagues for national team players with immediate effect",
"Scientists confirm that drinking hot lemon water every morning cures cancer in three days",
"Parliament passes law making all university degrees free for every citizen",
"Airline announces free lifetime tickets for anyone who shares its post on social media",
"Major bank to close all branches nationwide by the end of the month, officials confirm",
"Heavy snowfall expected in Karachi this week as temperatures drop to minus ten",
"Mobile networks to be shut down for ten days across the country, ministry says",
"Local factory owner discovers gold worth millions buried under his workshop floor",
"Court orders every school in the country to close permanently from January",
"New study proves that mobile phones switched off overnight cause serious illness",
"Prime minister to step down tomorrow after secret meeting with army chief, sources claim",
"Vaccine found to contain microchips that track citizens, whistleblower doctor reveals",
"Petrol price to fall to fifty rupees per litre from Friday, finance ministry insiders say",
"Giant asteroid will hit the earth next Tuesday, space agency scientists quietly admit",
"Country to introduce a new national currency next week, replacing all existing banknotes",
"Famous cricketer announces he will join the army after retiring from all cricket"]
for j,h in enumerate(INV): items.append({"id":f"I{j:02d}","kind":"invented","headline":h,"own_outlet":None})
json.dump(items,open("sets.json","w"),indent=1,ensure_ascii=False)
import collections; print(collections.Counter(x["kind"] for x in items))
for x in items:
    if x["kind"]=="distorted": print(x["how"],"|",x["derived_from"],"=>",x["headline"])
