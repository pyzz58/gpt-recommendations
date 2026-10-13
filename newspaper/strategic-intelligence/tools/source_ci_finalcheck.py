#!/usr/bin/env python3
import json,urllib.request,xml.etree.ElementTree as E
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
jobs=[
("SRC-088","yicai-json","https://www.yicai.com/api/ajax/getlatest?page=1&pagesize=10"),
("SRC-116","medrxiv-epi","https://connect.medrxiv.org/medrxiv_xml.php?subject=Epidemiology"),
("SRC-116","medrxiv-nursing","https://connect.medrxiv.org/medrxiv_xml.php?subject=nursing+nutrition"),
("SRC-106","europarl-rss","https://www.europarl.europa.eu/rss/doc/press-releases/en.xml"),
("SRC-053","arxiv-fresh","https://export.arxiv.org/api/query?search_query=cat%3Acs.AI&sortBy=submittedDate&sortOrder=descending&max_results=1"),
]
def f(a):
 id,label,url=a
 r={"id":id,"label":label,"url":url,"http_status":None,"content_type":None,"kind":None,"records":0,"sample":None,"error":None}
 try:
  req=urllib.request.Request(url,headers={"User-Agent":"NeicanPublicSourceAudit/1.0 (low volume; no auth or paywall)","Accept":"application/json,application/atom+xml,application/rss+xml,application/xml,text/html,*/*"})
  with urllib.request.urlopen(req,timeout=12) as o:
   r["http_status"]=o.status;r["content_type"]=o.headers.get("content-type","");b=o.read(300000)
  text=b.decode("utf-8","replace")
  if text.strip().startswith(("[","{")) or "json" in r["content_type"]:
   v=json.loads(text);r["kind"]="json";r["records"]=len(v) if isinstance(v,list) else len(v.get("data",[])) if isinstance(v.get("data"),list) else 0
   r["sample"]=str(v[0] if isinstance(v,list) and v else list(v.keys())[:5])[:180]
  else:
   try:
    root=E.fromstring(b);r["kind"]="xml:"+root.tag;r["records"]=len(root.findall(".//item"))+len(root.findall(".//{http://www.w3.org/2005/Atom}entry"));r["sample"]=(root.findtext(".//{http://www.w3.org/2005/Atom}entry/{http://www.w3.org/2005/Atom}title") or root.findtext(".//item/title") or text[:150])[:180]
   except E.ParseError as e:r["kind"]="xml_parse_failed";r["sample"]=text[:150];r["error"]=str(e)
 except Exception as e:r["kind"]="request_failed";r["error"]=str(e)[:200];r["http_status"]=getattr(e,"code",None)
 return r
with ThreadPoolExecutor(max_workers=4) as p:res=list(p.map(f,jobs))
path=Path(__file__).resolve().parents[1]/"audits"/"source-smoke-round3-20261013.json"
path.parent.mkdir(exist_ok=True);path.write_text(json.dumps({"generated_at":datetime.now(timezone.utc).isoformat(),"results":res},ensure_ascii=False,indent=2),encoding="utf-8")
for x in res:print(x["id"],x["label"],x["http_status"],x["kind"],x["records"],x["error"])
