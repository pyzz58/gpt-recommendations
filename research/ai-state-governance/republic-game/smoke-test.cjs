// Dependency-free smoke test for the public Republic bilingual text game.
// Run: node research/ai-state-governance/republic-game/smoke-test.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/);
const localeCode = fs.readFileSync(path.join(__dirname, "i18n-en.js"), "utf8");
new vm.Script(localeCode, {filename:"i18n-en.js"});
assert(script, "Game must have exactly one inline script");
new vm.Script(script[1], { filename: "republic-game.js" });

function testRun(seedValue, locale="zh-CN") {
  class Element {
    constructor(id="") { this.id=id;this.textContent="";this.hidden=false;this.disabled=false;this.className="";this.children=[];this.listeners={};this.value=""; }
    addEventListener(name,handler) { this.listeners[name]=handler; }
    click() { if(!this.disabled) { assert(this.listeners.click, "Missing click handler for "+this.id); this.listeners.click(); } }
    appendChild(el) {this.children.push(el);}
    replaceChildren(...xs) {this.children=xs.slice();}
  }
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
  const elements=Object.fromEntries(ids.map(id=>[id,new Element(id)]));
  const document={title:"",documentElement:{lang:""},getElementById(id){assert(elements[id], "Unknown DOM id "+id);return elements[id];},createElement(){return new Element();}};
  const storage={};const localStorage={getItem:k=>storage[k]||null,setItem:(k,v)=>storage[k]=v};
  let seed=seedValue;
  const math=Object.create(Math);math.random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};
  const window={};const navigator={language:locale,languages:[locale]};
  const ctx=vm.createContext({document,localStorage,Math:math,console,window,navigator});
  vm.runInContext(localeCode,ctx,{timeout:3000});
  vm.runInContext(script[1],ctx,{timeout:3000});
  assert.equal(document.documentElement.lang,locale.startsWith("zh")?"zh-CN":"en");
  assert.equal(elements["language-select"].value,locale.startsWith("zh")?"zh":"en");
  const by=id=>elements[id];
  const current=()=>JSON.parse(storage["republic-ai-presidency-0.4"]);
  assert(current().world>=0&&current().world<4,"Should draw one fictional international event");
  const en=!locale.startsWith("zh");
  if(en){
    assert(!/[\u4e00-\u9fff]/.test(by("world-intro").textContent),"English opening should be translated");
    assert.equal(by("ui-brand").textContent,"Republic");
    by("language-select").value="zh";by("language-select").listeners.change();
    assert(/[\u4e00-\u9fff]/.test(by("world-intro").textContent),"Manual Chinese switch should work");
    by("language-select").value="en";by("language-select").listeners.change();
    assert(!/[\u4e00-\u9fff]/.test(by("world-intro").textContent),"Returning to English should work");
  }
  by("begin").click();
  let steps=0, audits=0, caseCount=0,followCount=0,crisisCount=0,reportCount=0;
  while(current().view!=="ending"&&steps++<220){
    const v=current().view;
    if(v==="briefing"){
      reportCount += current().reports.length;
      if(en) assert(!/[\u4e00-\u9fff]/.test(by("briefing-title").textContent),"English briefing title");
      by("enter-agenda").click();
    } else if(v==="case-screen"){
      const s=current();
      const desc=s.queue[s.slot];if(desc.kind==="follow")followCount++;if(desc.kind==="crisis")crisisCount++;
      if(en){
        for(const id of ["case-title","speaker","proposal","objection","secretary","category"]){
          assert(!/[\u4e00-\u9fff]/.test(by(id).textContent),"Untranslated English case field: "+id+" ("+s.day+")");
        }
      }
      if(caseCount===3){
        const snapshot=JSON.stringify(s.score);
        by("language-select").value=en?"zh":"en";by("language-select").listeners.change();
        by("language-select").value=en?"en":"zh";by("language-select").listeners.change();
        assert.equal(JSON.stringify(current().score),snapshot,"Language switching must not change scores");
      }
      if(caseCount%3===0){by("audit-btn").click();audits++;}
      if(en&&current().audited)assert(!/[\u4e00-\u9fff]/.test(by("evidence").textContent),"Untranslated English audit");
      const options=by("options").children;
      if(en)for(const el of options)assert(!/[\u4e00-\u9fff]/.test(el.textContent),"Untranslated English choice");
      assert(options.length>=3&&options.length<=4,"Must give three decisions plus an optional audited choice");
      options[(caseCount+seedValue)%options.length].click();
      caseCount++;
    } else if(v==="decision-screen"){
      if(en)for(const id of ["decision-title","decision-immediate","decision-later","decision-reminder"]){
        assert(!/[\u4e00-\u9fff]/.test(by(id).textContent),"Untranslated decision receipt: "+id);
      }
      // A reload of a receipt must not consume the next case or apply its effect twice.
      if(caseCount===1){const before=JSON.stringify(current().score);vm.runInContext(script[1],ctx,{timeout:3000});assert.equal(JSON.stringify(current().score),before);}
      by("proceed").click();
    }
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
  if(en)for(const id of ["ending-title","ending-body"]){assert(!/[\u4e00-\u9fff]/.test(by(id).textContent),"Untranslated English ending");}
  return {seedValue,locale,world:s.world,cases:caseCount,followups:followCount,crisisStages:crisisCount,reports:reportCount,audits,days:s.day};
}
const results=[1,8,42,1337,2026,93321].flatMap(seed=>[testRun(seed,"zh-CN"),testRun(seed,"en-US")]);
console.log("Republic storyline smoke test PASS:\n"+results.map(r=>JSON.stringify(r)).join("\n"));
