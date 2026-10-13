#!/usr/bin/env python3
"""One-shot targeted retest, public endpoints only; run on isolated audit branch."""
from __future__ import annotations
import json,urllib.request,urllib.error,xml.etree.ElementTree as ET,html.parser,datetime,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
TESTS=[
("SRC-005","BBC RSS","https://feeds.bbci.co.uk/news/world/rss.xml","rss"),
("SRC-084","NPR RSS","https://feeds.npr.org/1001/rss.xml","rss"),
("SRC-085","France24 RSS","https://www.france24.com/en/rss","rss"),
("SRC-086","NHK RSSHub demo","https://rsshub.app/nhk/news/en","rss"),
("SRC-089","DW English RSS","https://rss.dw.com/xml/rss-en-all","rss"),
("SRC-106","European Parliament RSS","https://www.europarl.europa.eu/rss/doc/press-releases/en.xml","rss"),
("SRC-116","medRxiv Atom","https://connect.medrxiv.org/medrxiv_xml.php?subject=epidemiology","rss"),
("SRC-053","arXiv Atom","https://export.arxiv.org/api/query?search_query=all%3Acat&max_results=1","rss"),
("SRC-062","PubMed ESearch","https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=cancer&retmax=1","pubmed"),
("SRC-060","ClinicalTrials.gov","https://clinicaltrials.gov/api/v2/studies?pageSize=1","clinical"),
("SRC-061","Europe PMC","https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=malaria&format=json&pageSize=1","epmc"),
("SRC-087","澎湃公开JSON","https://cache.thepaper.cn/contentapi/wwwIndex/rightSidebar","thepaper"),
("SRC-088","第一财经公开JSON","https://www.yicai.com/api/ajax/getlatest?page=1&pagesize=10","yicai"),
("SRC-045","IISS Strategic Comments","https://www.iiss.org/publications/strategic-comments/","html"),
("SRC-113","IISS Strategic Dossiers","https://www.iiss.org/publications/strategic-dossiers/","html"),
("SRC-132","UN Population static report","https://www.un.org/development/desa/pd/content/world-population-prospects-2024","html"),
("SRC-034","Congress official public page","https://www.congress.gov/","html"),
]
class V(html.parser.HTMLParser):
 def __init__(self):super().__init__();self.txt=[];self.skip=0
 def handle_starttag(self,t,a):
  if t in ("script","style","noscript"):self.skip+=1
 def handle_endtag(self,t):
  if t in ("script","style","noscript"):self.skip=max(0,self.skip-1)
 def handle_data(self,d):
  if not self.skip and d.strip():self.txt.append(d.strip())
def test(task):
 ident,name,url,kind=task
 r={"id":ident,"source":name,"url":url,"kind":kind,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"result":"NOT_VERIFIED","http":None,"items":0,"date":None,"sample":None,"error":None}
 req=urllib.request.Request(url,headers={"User-Agent":"NeicanGSI/1.0 (public low-rate source smoke test)","Accept":"application/json,application/atom+xml,application/rss+xml,application/xml,text/xml,text/html,*/*"})
 try:
  with urllib.request.urlopen(req,timeout=11) as o:
   b=o.read(600000);r["http"]=o.status;r["bytes"]=len(b);r["content_type"]=o.headers.get("content-type");r["final_url"]=o.url
  s=b.decode("utf8","replace")
  if kind in ("rss","pubmed"):
   root=ET.fromstring(b)
   if kind=="pubmed":
    n=root.findtext(".//Count");ids=[x.text for x in root.findall(".//IdList/Id")]
    r.update(items=len(ids),result="PUBMED_RESULT_OK" if ids and n else "XML_NO_IDS",sample=", ".join(ids)[:140],date=None)
   else:
    items=root.findall(".//item")
    atom=root.findall(".//{http://www.w3.org/2005/Atom}entry")
    es=items or atom
    r["items"]=len(es)
    if es:
     q=es[0]; nstag="{http://www.w3.org/2005/Atom}" if atom else ""
     r["sample"]=(q.findtext(nstag+"title") or "").strip()[:170]
     r["date"]=(q.findtext(nstag+"published") or q.findtext("pubDate") or q.findtext(nstag+"updated") or "")[:80]
    r["result"]="RSS_ITEMS_OK" if r["items"] else "XML_ZERO_ITEMS"
  elif kind in ("clinical","epmc","thepaper","yicai"):
   v=json.loads(s)
   if kind=="clinical": a=v.get("studies",[]);r.update(items=len(a),sample=a[0].get("protocolSection",{}).get("identificationModule",{}).get("nctId") if a else None)
   elif kind=="epmc": a=v.get("resultList",{}).get("result",[]);r.update(items=len(a),sample=a[0].get("title","")[:160] if a else None)
   elif kind=="thepaper":
    data=v.get("data",{});r["items"]=sum(len(q) for q in data.values() if isinstance(q,list));r["sample"]=",".join(data.keys())[:170]
   else:
    r["sample"]=(str(v)[:160]);r["items"]=len(v.get("data",[])) if isinstance(v,dict) and isinstance(v.get("data"),list) else 0
   r["result"]="JSON_RECORDS_OK" if r["items"]>0 else "JSON_NO_RECORDS"
  elif kind=="html":
   p=V();p.feed(s);v=" ".join(p.txt)
   r["items"]=len(v);r["sample"]=v[:160]
   r["result"]="HTML_CONTENT_OK" if len(v)>600 else "HTML_THIN"
  else:r["result"]="OTHER"
 except Exception as ex:
  r["result"]="REQUEST_OR_PARSE_FAILED";r["error"]=str(ex)[:230];r["http"]=getattr(ex,"code",r["http"])
 return r
def main():
 st=time.monotonic()
 with ThreadPoolExecutor(max_workers=4) as p: results=list(p.map(test,TESTS))
 o={"generated_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"type":"targeted second test isolated branch", "duration":round(time.monotonic()-st,2),"results":results,"limits":"Individual live HTTP responses only. No content license or sustainable production claims."}
 dest=Path(__file__).resolve().parents[1]/"audits"/"source-smoke-round2-20261013.json"
 dest.parent.mkdir(exist_ok=True);dest.write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding="utf8")
 for r in results:print(r["id"],r["result"],r["http"],r["items"],r["sample"],r["error"])
if __name__=="__main__":main()
