// Dependency-free smoke test for the public Republic single-file text game.
// Run: node research/ai-state-governance/republic-game/smoke-test.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/);
assert(script, "Game must have exactly one inline script");
new vm.Script(script[1], { filename: "republic-game.js" });

function testRun(seedValue) {
  class Element {
    constructor(id="") { this.id=id;this.textContent="";this.hidden=false;this.disabled=false;this.className="";this.children=[];this.listeners={}; }
    addEventListener(name,handler) { this.listeners[name]=handler; }
    click() { if(!this.disabled) { assert(this.listeners.click, "Missing click handler for "+this.id); this.listeners.click(); } }
    appendChild(el) {this.children.push(el);}
    replaceChildren(...xs) {this.children=xs.slice();}
  }
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
  const elements=Object.fromEntries(ids.map(id=>[id,new Element(id)]));
  const document={getElementById(id){assert(elements[id], "Unknown DOM id "+id);return elements[id];},createElement(){return new Element();}};
  const storage={};const localStorage={getItem:k=>storage[k]||null,setItem:(k,v)=>storage[k]=v};
  let seed=seedValue;
  const math=Object.create(Math);math.random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};
  vm.runInNewContext(script[1],{document,localStorage,Math:math,console},{timeout:3000});
  const by=id=>elements[id];
  const current=()=>JSON.parse(storage["republic-ai-presidency-0.4"]);
  assert(current().world>=0&&current().world<4,"Should draw one fictional international event");
  by("begin").click();
  let steps=0, audits=0, caseCount=0,followCount=0,crisisCount=0,reportCount=0;
  while(current().view!=="ending"&&steps++<220){
    const v=current().view;
    if(v==="briefing"){
      reportCount += current().reports.length;
      by("enter-agenda").click();
    } else if(v==="case-screen"){
      const s=current();
      const desc=s.queue[s.slot];if(desc.kind==="follow")followCount++;if(desc.kind==="crisis")crisisCount++;
      if(caseCount%3===0){by("audit-btn").click();audits++;}
      const options=by("options").children;
      assert(options.length>=3&&options.length<=4,"Must give three decisions plus an optional audited choice");
      options[(caseCount+seedValue)%options.length].click();
      caseCount++;
    } else if(v==="decision-screen")by("proceed").click();
    else if(v==="evening")by("next-day").click();
    else throw new Error("Unexpected view "+v);
  }
  const s=current();
  assert.equal(s.view,"ending","Game must end after 12 workdays");
  assert.equal(s.day,12);
  assert.equal(crisisCount,4,"Should have exactly four connected international crisis chapters");
  assert(followCount>=5,"Past domestic decisions should reopen after several days");
  assert(reportCount>=7,"Later days should include implementation reports and delayed effects");
  assert(caseCount>=17,"Must involve substantially more than fixed five choices");
  assert(audits>=5,"Independent audit must work");
  for(const k of ["life","treasury","integrity","trust"])assert(s.score[k]>=0&&s.score[k]<=100,"Score bounds");
  return {seedValue,world:s.world,cases:caseCount,followups:followCount,crisisStages:crisisCount,reports:reportCount,audits,days:s.day};
}
const results=[1,8,42,1337,2026,93321].map(testRun);
console.log("Republic storyline smoke test PASS:\n"+results.map(r=>JSON.stringify(r)).join("\n"));
