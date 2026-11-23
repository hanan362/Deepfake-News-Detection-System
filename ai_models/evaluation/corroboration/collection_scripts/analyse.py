import json, itertools, collections
items=json.load(open("features.json"))
ent=json.load(open("/home/claude/proj/backend/app/ml/url_analysis/known_sources.json"))["entries"]
dom2name={e["domain"]:e["name"] for e in ent}
def supporters(x,to,te,exclude_own=False):
    own=dom2name.get(x.get("own_outlet")) if exclude_own else None
    s=set()
    for r in x["results"] or []:
        if r["rep"] and r["rep"]!=own and r["overlap_q"]>=to and r["entail"]>=te: s.add(r["rep"])
    return s
kinds=collections.defaultdict(list)
for x in items: kinds[x["kind"]].append(x)
print({k:len(v) for k,v in kinds.items()})
print("t_overlap t_entail | min_outlets | authentic(incl own) authentic(excl own) | distorted | invented")
for to in (0.5,0.6,0.7,0.8):
  for te in (0.0,0.3,0.6,0.9):
    for mn in (1,2):
        a=sum(len(supporters(x,to,te))>=mn for x in kinds["authentic"]); a2=sum(len(supporters(x,to,te,True))>=mn for x in kinds["authentic"])
        d=sum(len(supporters(x,to,te))>=mn for x in kinds["distorted"]); i=sum(len(supporters(x,to,te))>=mn for x in kinds["invented"])
        print(f"{to:.1f} {te:.1f} | {mn} | {a}/{len(kinds['authentic'])} {a2}/{len(kinds['authentic'])} | {d}/{len(kinds['distorted'])} | {i}/{len(kinds['invented'])}")
