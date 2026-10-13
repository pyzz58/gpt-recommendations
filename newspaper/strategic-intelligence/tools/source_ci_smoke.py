#!/usr/bin/env python3
"""One-time public endpoint validation. No paid access, account logins, or source scraping bypass."""
import json,ssl,time,urllib.request,urllib.error,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
BASE=Path(__file__).resolve().parents[1]
DATA=json.loads((BASE/"SOURCE_REGISTRY.json").read_text(encoding="utf8"))
PROBLEM=[e for e in DATA["entries"] if e.get("recovery_20261013")]
EXCEPTIONS={
"SRC-005":"https://feeds.bbci.co.uk/news/world/rss.xml",
"SRC-034":"https://api.congress.gov/v3/bill?limit=1",
"SRC-038":"https://www.ungeneva.org/en/news-media/rss",
"SRC-039":"https://commission.europa.eu/about/contact/press-services/press-releases-and-notifications_en",
"SRC-053":"https://export.arxiv.org/api/query?search_query=all%3Acat&max_results=1",
"SRC-060":"https://clinicaltrials.gov/api/v2/studies?pageSize=1",
"SRC-061":"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=malaria&format=json&pageSize=1",
"SRC-062":"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=cancer&retmax=1",
"SRC-064":"https://ourworldindata.org/",
"SRC-087":"https://cache.thepaper.cn/contentapi/wwwIndex/rightSidebar",
"SRC-088":"https://www.yicai.com/",
"SRC-099":"https://www.gao.gov/topics/government-operations?page=1",
"SRC-132":"https://population.un.org/wpp/Download/Standard/MostUsed/"
}
# RSSHub routes are not endpoints themselves. Probe public source endpoints only.
def inspect(entry):
  key=entry["id"]
  target=EXCEPTIONS.get(key) or entry.get("recovery_20261013",{}).get("preferred_url") or entry["url"]
  result={"id":key,"name":entry["name"],"url":target,"tested_at":datetime.now(timezone.utc).isoformat(),
          "http_status":None,"type":None,"bytes":0,"success":False,"state":"UNTESTED","sample":None}
  req=urllib.request.Request(target,headers={"User-Agent":"NeicanOpenSourceAccessAudit/1.0 (noncommercial source verification)","Accept":"application/json,application/rss+xml,application/atom+xml,text/xml,application/xml,text/html;q=0.9,*/*;q=0.2"})
  try:
    with urllib.request.urlopen(req,timeout=9) as resp:
      b=resp.read(400000)
      result["http_status"]=resp.status;result["type"]=resp.headers.get("Content-Type","")
      result["bytes"]=len(b);result["final_url"]=resp.url
    raw=b.decode("utf-8","replace")
    mime=result["type"].lower()
    if "json" in mime or raw.strip().startswith(("{","[")):
      obj=json.loads(raw)
      if isinstance(obj,dict):
        result["sample"]=", ".join(list(obj.keys())[:8])
        result["success"]=True
      elif isinstance(obj,list):
        result["sample"]="array_len="+str(len(obj));result["success"]=len(obj)>0
      result["state"]="JSON_VALID" if result["success"] else "JSON_EMPTY"
    elif "xml" in mime or "rss" in mime or raw.lstrip().startswith("<?xml"):
      root=ET.fromstring(raw)
      item=root.find(".//item")
      if item is None: item=root.find(".//{http://www.w3.org/2005/Atom}entry")
      t=item.find("title") if item is not None else None
      if item is not None and t is None: t=item.find("{http://www.w3.org/2005/Atom}title")
      result["sample"]=(t.text or "")[:160] if t is not None else root.tag
      result["success"]=item is not None
      result["state"]="XML_HAS_ITEMS" if result["success"] else "XML_NO_ITEMS"
    elif "<html" in raw[:2000].lower() or "html" in mime:
      from html.parser import HTMLParser
      class T(HTMLParser):
        def __init__(self):super().__init__();self.text=[];self.skip=0
        def handle_starttag(self,t,a):
          if t in ("script","style","noscript"):self.skip+=1
        def handle_endtag(self,t):
          if t in ("script","style","noscript"):self.skip=max(0,self.skip-1)
        def handle_data(self,data):
          if not self.skip and data.strip():self.text.append(data.strip())
      parser=T();parser.feed(raw)
      joined=" ".join(parser.text)
      result["sample"]=joined[:160]
      result["success"]=len(joined)>500 and not ("please enable javascript" in joined.lower())
      result["state"]="HTML_TEXT" if result["success"] else "HTML_THIN"
    else:result["state"]="OTHER_RESPONSE"
  except Exception as exc:
    result["state"]="REQUEST_ERROR"
    result["error"]=str(exc)[:220]
    if hasattr(exc,"code"):result["http_status"]=exc.code
  return result
def main():
  start=time.monotonic()
  with ThreadPoolExecutor(max_workers=4) as pool:
    results=list(pool.map(inspect,PROBLEM))
  out={"generated_at":datetime.now(timezone.utc).isoformat(),"test_type":"GitHub Actions one-shot isolated audit branch",
       "source_count":len(PROBLEM),"note":"Single HTTP request is not approval for AI training, redistributing fulltext, or stable production ingestion.",
       "elapsed_seconds":round(time.monotonic()-start,2),"results":results}
  p=BASE/"audits"/"source-smoke-20261013.json";p.parent.mkdir(exist_ok=True)
  p.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf8")
  print("TESTED",len(results),"HTTP_CONTENT_SUCCESSES",sum(r["success"] for r in results),"RESULTS",str(p))
  for r in results:print(r["id"],r["state"],r["http_status"],r["bytes"],r.get("error",""))
if __name__=="__main__":main()
