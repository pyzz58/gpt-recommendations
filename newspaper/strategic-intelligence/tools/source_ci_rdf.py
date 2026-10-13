#!/usr/bin/env python3
import json,urllib.request,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
TESTS=[
("SRC-116","medrxiv epidemiology RDF","https://connect.medrxiv.org/medrxiv_xml.php?subject=Epidemiology"),
("SRC-116","medrxiv nursing RDF","https://connect.medrxiv.org/medrxiv_xml.php?subject=nursing+nutrition"),
("SRC-053","arxiv latest by date","https://export.arxiv.org/api/query?search_query=cat%3Acs.AI&sortBy=submittedDate&sortOrder=descending&max_results=1"),
]
out=[]
for id,name,url in TESTS:
 r={"id":id,"name":name,"url":url,"http":None,"root":None,"items":0,"headline":None,"published":None,"error":None}
 try:
  req=urllib.request.Request(url,headers={"User-Agent":"NeicanGSI/1.0 public low-frequency endpoint verification"})
  with urllib.request.urlopen(req,timeout=10) as s:
   r["http"]=s.status;b=s.read(400000)
  x=ET.fromstring(b);r["root"]=x.tag
  items=x.findall(".//item")+x.findall(".//{http://purl.org/rss/1.0/}item")+x.findall(".//{http://www.w3.org/2005/Atom}entry")
  r["items"]=len(items)
  if items:
   item=items[0];r["headline"]=(item.findtext("title") or item.findtext("{http://purl.org/rss/1.0/}title") or item.findtext("{http://www.w3.org/2005/Atom}title") or "")[:190]
   r["published"]=(item.findtext("pubDate") or item.findtext("{http://purl.org/dc/elements/1.1/}date") or item.findtext("{http://www.w3.org/2005/Atom}published") or "")[:80]
 except Exception as ex:r["error"]=str(ex)[:190];r["http"]=getattr(ex,"code",r["http"])
 out.append(r)
p=Path(__file__).resolve().parents[1]/"audits"/"source-smoke-round4-20261013.json";p.parent.mkdir(exist_ok=True)
p.write_text(json.dumps({"generated_at":datetime.now(timezone.utc).isoformat(),"results":out},ensure_ascii=False,indent=2),encoding="utf8")
for v in out:print(v["id"],v["http"],v["root"],v["items"],v["headline"],v["published"],v["error"])
