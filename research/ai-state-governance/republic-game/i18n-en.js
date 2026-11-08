/* Republic EN locale — original, human-readable translation; no network translation API. */
window.REPUBLIC_EN = {
  ui:{
    "gameVersion":"Public interactive thought experiment · v0.6",
    "brand":"Republic",
    "tagline":"You are the AI head of state. Human specialists govern; you review exceptional decisions, appointments, oversight and institutional failures.",
    "reportLink":"Research paper",
    "discussLink":"Discuss / Suggest changes",
    "sourceLink":"Open source",
    "state":"State of the Republic",
    "disclaimer":"Indicators are narrative game mechanics, not a prediction of real policy outcomes. Audits have costs; blind approval and endless delay also carry risks.",
    "introTag":"International bulletin · Random opening",
    "introRules":"HOW TO PLAY: Twelve working days, with several reports each day. Departments design and execute policies; you can ask for an independent investigation, return a proposal or rule on a major dispute. Earlier choices return as implementation reports and new hearings.",
    "introSave":"International crises, domestic cases and later branches vary. Progress is saved in this browser; no account or live news connection.",
    "start":"Begin your first day in office",
    "restartIntro":"Draw a new world event",
    "morningTag":"Office of the President · Morning briefing",
    "morningButton":"Receive today's cabinet reports",
    "cabinetTag":"Cabinet agenda",
    "reportHeader":"Department submission",
    "positionsHeader":"Views from the cabinet",
    "questionHeader":"Decision requested",
    "auditHeader":"Independent audit findings",
    "auditButton":"Request an independent audit (Treasury −1)",
    "auditedButton":"Audit received (cost already charged)",
    "decisionHeader":"Your ruling",
    "auditHint":"Reviewing evidence sometimes unlocks another option. All facts and scores are fictional.",
    "decisionTag":"Order issued · Implementation begins",
    "followHeader":"Expected next development",
    "continue":"Continue to the next report",
    "eveningTag":"End-of-day record",
    "eveningNote":"A decision is not the end of an event. Departments may return with results, audit concerns or changed budgets.",
    "nextDay":"Close today and begin the next working day",
    "endingTag":"End of term · Interim review",
    "crisisHeader":"International crisis: decisions",
    "otherHeader":"Other government decisions",
    "endingNote":"The twelve-day chapter has ended. Unresolved matters do not magically disappear, and this game does not establish that AI can govern a real state.",
    "again":"Start a new fictional administration",
    "footer":"Open, original text game · No accounts or ads · No live news feed · Contributions welcome on GitHub",
    "life":"Well-being","treasury":"Treasury","integrity":"Integrity","trust":"Public trust"
  },
  world:{
    coldchain:{title:"International cold-chain network disrupted",agency:"Health and International Cooperation Cabinet",
      intro:"Several fictional international refrigerated shipping routes have stopped operating. Specialist medicines are delayed, and hospitals are calling for emergency assistance.",stakes:"The nation is not yet out of all medicines. The urgent task is to find which patients are at risk, prevent panic buying, and keep emergency spending accountable.",
      stages:[
        ["The Health Ministry reports that three refrigerated air routes have stopped. Deliveries to seven hospitals are delayed, and three have requested national reserves. An emergency purchase could cost 240 million republic credits, but the reported inventory figures are inconsistent.","The Health Minister wants to buy immediately to prevent treatment interruptions. The Treasury Minister warns that buying against unverified orders may drive prices higher. Smaller specialist hospitals fear allocation by bed count will bypass their patients.","Auditors sampled four hospitals: two have about a week's supply, while another omitted substitute medicines from its declaration. Part of the price increase is consistent with shipping costs; corruption has not been established.","Should the first emergency purchase be fully authorized now, or capped and released in stages against verified shortages?"],
        ["The first medicines have left the national warehouse, yet two specialist hospitals are still running short. A large city hospital has supplies it has not used. Dispatch schedules were based on hospital size rather than actual clinical need.","The distribution centre wants to keep the schedule, fearing delays if it changes truck routes. Specialist doctors say even a few untreated patients could face serious harm. Treasury opposes another purchase before existing stock is redistributed.","Sampling shows roughly one third of the first shipment reached three large hospitals, some still unused. Two specialist hospitals have fewer than five days of key medicine. Re-routing vehicles could help.","Should the country buy more medicines, or first reallocate existing stocks and reprioritize transport?"],
        ["International routes are partly recovering, but three early emergency contracts cost about 18% more than later comparable offers. Procurement officials cite emergency airfreight. Auditors have also received a tip about linked suppliers; hospitals fear cancellation of shipments still in transit.","Treasury wants expensive contracts cancelled. Health officials say a life-saving shipment is still in transit. Legal advisers insist that genuine emergency costs, procedural errors and proven illegal conduct must be treated differently.","Two contracts included documented urgent air transport; one lacks required comparative quotations. Further inquiry is justified, but there is no basis to declare every contract illegal.","Should disputed contracts all be cancelled, all paid, or reviewed separately while vital deliveries continue?"],
        ["Health officials propose a single national medicine reserve centre costing about 800 million credits. The central warehouse worked quickly, but distant hospitals received stock too slowly. Regional hospitals propose smaller backup sites.","The Health Minister argues one warehouse is cheaper and easier to audit. Regional hospitals emphasize delivery time. Treasury reminds everyone that medicines expire and storage costs recur every year.","Exercises suggest one large warehouse can lower purchase costs but creates a single logistical bottleneck during widespread transport disruption. Distributed reserves cost more to maintain.","Should the Republic build one giant reserve, or a risk-tiered network of regional reserves with recurring audits?"]
      ]},
    data:{title:"Intercontinental data link failure",agency:"Digital Services and Social Protection Cabinet",
      intro:"A fictional international communications backbone has failed. Identity checks are rejecting legitimate citizens, and some remote communities cannot access urgent public services.",stakes:"The concern is not just average uptime; it is whether people can actually obtain public services without losing privacy or security.",
      stages:[
        ["The Digital Services Ministry says the international outage has lasted 36 hours. Online forms still show 92% completion, but three remote service offices cannot verify identities. Pension payments and urgent hospital referrals are delayed.","The network operator wants staff to focus exclusively on technical repairs. Public Services opposes closing physical counters. Treasury wants to know the price and duration of temporary in-person service.","Auditors reviewed 180 rejected applications: most applicants were legitimate, with disproportionate failures on low-bandwidth networks and accessibility devices. Emergency in-person checks are feasible.","Should the nation focus only on technical repairs, or keep essential in-person services running during recovery?"],
        ["Temporary counters have reduced queues, but staff recorded eleven duplicate identity forms and two suspected fraudulent claims. Security officials want strict online checks restored; local offices warn elderly residents would again be cut off.","Cybersecurity officials insist high-value payments need stronger checks. Service staff argue ordinary inquiries and urgent referrals do not require identical authentication procedures.","Suspected fraud is concentrated in a few higher-value claims. Lower-risk services can use simpler manual checks if staff powers are carefully specified.","Should manual services close altogether, or should identity checks vary according to the risk of each service?"],
        ["One supplier offers a five-year exclusive upgrade contract at 28% above the previous plan, promising also to maintain backup links. The operator welcomes simpler coordination, but the contract makes switching suppliers costly.","Procurement wants one contractor appointed quickly. The privacy commissioner warns that placing authentication and failure response in one company's hands could make future replacement impractical.","Engineers confirm the backup interfaces can be built in phases. Some migration cost is real, but open standards would substantially lower future lock-in.","Should the state sign an exclusive five-year contract, or stage procurement and preserve the ability to change suppliers?"],
        ["The international network has recovered. The Digital Services Ministry requests funding for offline service desks, data backup and emergency exercises. Treasury argues that permanently maintaining standby capacity is expensive.","Service departments fear another outage will again disrupt pensions and medical referrals. Treasury says annual reserve costs could crowd out other public services.","The failure was concentrated in a critical identity gateway, rather than every application. Backup levels can be differentiated according to service importance.","Which services must maintain offline alternatives permanently, and who should test them?"]
      ]},
    grain:{title:"Global grain freight costs surge",agency:"Treasury, Agriculture and Social Affairs Cabinet",
      intro:"Congestion across several fictional trade corridors has driven up the cost of grain shipments. Local governments request emergency support as some households reduce basic purchases.",stakes:"Regions differ in existing inventories and household incomes. Equal subsidies can miss urgent needs, while broad subsidies may quickly exhaust the budget.",
      stages:[
        ["International grain freight costs have risen roughly 23% over ten days. Six regions seek subsidies totaling 40% more than the available emergency budget. Two regions have only nine days of public grain reserves; two others have healthy stocks.","Treasury proposes fast payments based on population. Agriculture wants near-empty reserves prioritized. Local auditors report duplicate declarations in storage and freight applications.","Inspectors confirmed serious shortages in two areas and duplicate transport claims in another. Part of the increase follows global freight costs; broad corruption has not been established.","Should the first emergency funds be divided equally, targeted at actual shortages, or released in stages after checking inventories?"],
        ["The first grain shipments reached five regions. One warehouse has trucks queued for two days, while another district still has empty store shelves. Transport officials say there are enough vehicles; unloading schedules are the bottleneck.","Agriculture requests more money for trucks. Transport officials argue more trucks will simply join the queue. Social Affairs wants vulnerable households supplied first.","Four logistics hubs were sampled. Two have unused night unloading capacity, and one region received more support than its verifiable shortage justified.","Should the state finance more vehicles, or change unloading schedules and routes to prioritize genuinely underserved areas?"],
        ["Prices are stabilizing, but early emergency contracts are still being billed at high rates. Traders warn abrupt cancellations would harm future supply. Auditors are investigating possible inflated shipping charges.","Treasury seeks refunds. Commerce wants lawful contracts honoured. Legal advisers say price alone cannot establish wrongdoing; actual delivery and related-party dealings matter.","Most price differences reflect routes, deadlines or fuel costs. Two contracts lack complete public bidding records and merit further investigation.","Should all contracts be cancelled, all prices paid, or individual contracts reviewed against evidence?"],
        ["Agriculture wants a permanent grain and transport reserve after repeated global price swings. Treasury fears spoilage and annual costs; remote regions worry one national storehouse will be too far away.","Agriculture favors centralized stocks. Treasury wants strict activation thresholds. Regional officials suggest combining local depots with temporary freight agreements.","Neither total centralization nor purely ad hoc buying performs well in every scenario. Stock triggers, regional capacity and periodic audits can be designed together.","Should emergency subsidies become a permanent system, and how can long-term waste be limited?"]
      ]},
    energy:{title:"International energy supply shock",agency:"Energy, Transport and Treasury Cabinet",
      intro:"Disruption to fictional international fuel routes is driving up the cost of transport, backup electricity and hospital operations. Emergency budget requests exceed available funds.",stakes:"Engineers decide how energy systems work; elected institutions and the cabinet must still decide priority, spending authority and public safeguards.",
      stages:[
        ["International fuel supply is tight and public-facility costs may rise 17% over two weeks. Twenty-eight facilities seek emergency grants, exceeding the budget. The list includes hospitals and water plants but also offices and parking buildings.","Energy favors equal grants for speed. Treasury wants facilities where interruption would endanger lives to go first. Regional officials note that a small town's water plant can be essential.","Of eight facilities audited, two hospitals have under three days of reserve fuel, while several offices have sufficient backup. Some requests double-count fuel and shipping allowances.","Should emergency grants be evenly spread, or first protect hospitals, water supply and other critical services?"],
        ["Most hospitals regained energy after the first grants, but three remote water plants still stop intermittently. Local governments ask for another round; some prior grants have not been fully reconciled.","Local officials want more money quickly. Water departments suspect poor delivery routes rather than defective generators. Treasury fears double payments.","All three plants' equipment is operational. Delivery delays cause their interruptions, and one application includes fuel already reimbursed.","Should the state increase grants, or change delivery arrangements and verify existing payments first?"],
        ["Suppliers want short-term fuel contracts extended for three years in exchange for guaranteed priority supply. Auditors find two companies were introduced by the same broker but have not proven a violation.","Energy argues longer contracts secure fuel. Treasury fears being locked into high prices after the market recovers. Oversight asks to retain multiple supply routes.","Some guaranteed-supply costs are reasonable; fixed high prices for three years may create major fiscal risk. Broker links warrant inquiry but do not establish bid rigging.","Should the state sign the long deals now, or retain renegotiation rights and independent reviews?"],
        ["Energy officials propose a giant reserve-energy facility requiring ten years of investment. Regions favor smaller batteries and efficiency improvements. Both approaches require long-term funding.","Central planners expect economies of scale. Local operators fear a single point of failure. Treasury requests lifetime construction, maintenance and interruption costs.","Both centralized and distributed backup have legitimate use cases. One brief crisis is insufficient evidence to choose a permanent national energy architecture.","Should a major project be approved now, or should specialists compare layered backup plans first?"]
      ]}
  },
  domestic:{
    appointments:{title:"Competition for an emergency agency director",agency:"Senior Appointments Commission",
      report:"The emergency agency has lacked a director for twelve days. An internal deputy was nominated, while an experienced regional rescue manager applied through the open process. After applications closed, personnel officers added a requirement for experience in a central ministry.",
      views:"The former director values the internal candidate's familiarity. The selection panel argues that strong regional command experience deserves review and that criteria must not change after applications. Everyone agrees the role needs cross-agency leadership.",
      audit:"Appointment records confirm the qualification was added after applications opened without a complete approval trail. Both candidates have verifiable achievements, but neither is automatically the right choice.",
      question:"Approve the internal nominee now, or restore the published rules and assess all qualified candidates fairly?",
      follow:"The applicant requests an explanation of the new qualification rule while the agency urgently needs a director for upcoming emergency drills. The complaints procedure still has to be honoured."},
    schools:{title:"How fair is access to public education?",agency:"Education and Public Services Committee",
      report:"The Education Ministry says standardized examinations are operating normally. Yet visits to forty schools found remote classrooms without enough laboratory equipment and students borrowing computers for exam preparation. The education budget is nearly exhausted.",
      views:"Examination officials argue that common tests create equal rules. Teachers say pupils arrive with unequal learning opportunities. Treasury requests an affordable, prioritized improvement plan.",
      audit:"Seven schools cannot deliver the prescribed practical curriculum; several others have equipment sitting unused. Funding and management both matter, and test scores alone cannot capture potential.",
      question:"Protect only the examination process, or ask specialists to improve conditions at disadvantaged schools in stages?",
      follow:"Some schools request new computers and equipment, while others already own equipment but have no teachers trained to use it. The budget office needs to separate shortages from poor management."},
    water:{title:"Drinking-water infrastructure renewal",agency:"Interregional Urban Services Committee",
      report:"Two regions seek 600 million credits to renew old pipes. The populous first region loses substantial water; the second has two disinfection facilities on an urgent-repair list. Treasury cannot fund every project immediately.",
      views:"The first region argues that repairs there would help more people. The second says safe drinking water should not depend only on population size. Both insist their projects are important.",
      audit:"Independent tests confirm the second region faces higher immediate shutdown risk, while losses in the first region are also real. Allocating everything to either side would leave serious problems.",
      question:"Allocate by population, divide the money equally, or protect minimum water safety first and phase longer-term repairs?",
      follow:"High-risk disinfection facilities have repair schedules, but network leakage in another region has worsened. Engineers need separate budgets for immediate safety and long-term renewal."},
    procurement:{title:"Unusual bids for medical equipment",agency:"National Procurement Office",
      report:"Five medical equipment suppliers submitted unusually similar bids, and two use the same agent. Procurement says import freight has increased. Three hospitals say essential surgical equipment will run out this week.",
      views:"Auditors demand the original bidding records. Health authorities object to blocking all supplies and delaying operations. Procurement wants uncontested deliveries released.",
      audit:"The two companies do share an intermediary, but some common pricing is explained by freight costs. Further investigation is warranted; the evidence does not establish that all suppliers broke the law.",
      question:"How should hospitals keep receiving vital equipment while suspicious relationships and prices are investigated?",
      follow:"Some instruments have reached hospitals while other contracts remain under inquiry. Suppliers want uncontested invoices paid; auditors insist the bidding evidence be retained."},
    housing:{title:"Where should affordable housing funds go?",agency:"Housing and Treasury Committee",
      report:"Three districts ask to build subsidized homes. The eastern district has high rents, the western district already has vacant units, and the southern district has long commutes. The budget can fund only two priority projects.",
      views:"The housing agency favors a uniform building program. Local representatives argue the west needs transport upgrades while the east needs homes. Treasury worries about building more empty units.",
      audit:"The eastern district faces a genuine housing shortage. Existing stock is underused in the west, while transport costs burden southern households. A single construction target would miss these differences.",
      question:"Approve the same building plan everywhere, or let specialists redesign housing and transport investments by district?",
      follow:"Applications for homes remain strong, yet some new neighborhoods have vacancies because journeys are too long. Local officials need to decide between building, renovation and better transport."},
    oversight:{title:"Should auditors have unrestricted data access?",agency:"National Audit and Oversight Office",
      report:"The audit authority requests permanent access to every record in more than twenty departmental databases to detect procurement and staffing anomalies. The privacy commissioner notes the request lacks limits on fields, retention and users.",
      views:"Auditors say individual approvals can delay time-sensitive investigations. Privacy officials warn that unchecked access exposes citizens and that overseers themselves must be accountable.",
      audit:"Targeted sampling has already found some anomalies. Unlimited permanent access has not been justified; time-limited, case-specific permissions and access logs are possible.",
      question:"Grant blanket data access, or define narrow investigative powers with independent review of how they are used?",
      follow:"Privacy officials request a log of recent database searches. Auditors found questionable contracts but say some ministries have not supplied all records on time."},
    research:{title:"Choosing a national research budget",agency:"Science and Treasury Committee",
      report:"A scientific funding panel is split: one group wants a large shared laboratory facility, while another would support ten smaller research teams. Both submitted technical cases, but neither can guarantee a breakthrough.",
      views:"The facility team says individual labs cannot afford the equipment. Smaller teams fear access queues and a bias toward fashionable research. Treasury demands clear milestones.",
      audit:"Independent specialists find credible scientific paths for both approaches but cannot predict which will deliver the greatest discovery. Staged financing and transparent access rules reduce lock-in.",
      question:"Commit the budget to one plan, suspend all grants, or let experts phase funding under published review rules?",
      follow:"The large facility team has started procurement preparations. Small teams ask for fair access and independent peer review of future allocations."},
    cyber:{title:"Suspicious activity in public appointments",agency:"Cybersecurity and Public Services Board",
      report:"A public appointment system detected intense suspicious sign-ins overnight. Security engineers want every service disconnected. Public counters have thousands of medical and identity bookings scheduled today.",
      views:"Cybersecurity wants to prevent any wider attack. Public Services says abnormalities are concentrated in one identity interface and questions whether all appointments must stop.",
      audit:"An independent check finds suspicious traffic concentrated in one authentication service. Other business functions do not show the same exposure. The affected interface can be isolated while manual essential services continue.",
      question:"Shut down every public service, keep everything running, or isolate high-risk systems while protecting essential appointments?",
      follow:"The affected identity interface is gradually returning, but many appointments remain backlogged. Citizens want clear service updates; engineers do not want to reveal unpatched vulnerabilities."},
    transit:{title:"Fair performance targets for regional transport",agency:"Regional Transport Council",
      report:"A dense urban region and a remote region are both judged on passengers per vehicle per day. The remote authority says it can only meet the target by cancelling sparsely used routes needed for hospital visits.",
      views:"Treasury likes easy-to-compare numbers. Social Services warns that cutting a low-ridership route could leave residents unable to reach healthcare. Local representatives demand basic-service guarantees.",
      audit:"The urban region needs peak-hour reliability measures. The remote region needs hospital access and minimum route coverage. Both still need common safety standards.",
      question:"Keep identical ridership targets, or let experts choose region-specific measures while maintaining national minimum service levels?",
      follow:"Remote routes still require subsidies, and some authorities are preparing cuts to meet their targets. Residents request disclosure of real service frequency and travel times."}
  }
};
window.REPUBLIC_EN.options = {
 crisis:[
 [
  ["Give the ministry unlimited emergency purchasing authority","Procurement accelerates and large funds are released immediately.","The authority covers many purchases that were not urgent, leaving some essential services underfunded."],
  ["Grant limited emergency powers after specialists verify priority needs","Agencies receive time-limited spending powers with defined responsibilities.","The most urgent services improve, although Treasury receives further budget requests."],
  ["Leave emergency coordination to each ministry","The central emergency budget is largely untouched.","Ministries compete for supplies and follow incompatible standards."],
  ["Create a joint response group and phase aid using verified evidence","A joint team directs initial help to those most at risk; auditors track approvals.","Shared records improve the next response, although additional coordination costs money."]
 ],
 [
  ["Increase emergency funding and extend authority across the board","Ministries quickly gain more money and discretion.","Some urgent needs are met, but extended emergency powers create fresh concerns."],
  ["Correct the rollout based on field reports and keep an appeal route","Departments adjust implementation and support affected people.","New evidence reduces waste, though frontline workers face extra work."],
  ["Declare the crisis controlled and dismiss local complaints","The administration resumes normal procedures quickly.","Unresolved service gaps become visible and public confidence declines."],
  ["Publish independently verified regional evidence and amend the order","Auditors report differences between local needs and spending.","Departments correct inaccurate reports and build a better response process."]
 ],
 [
  ["Cancel every early emergency contract","Treasury stops disputed payments quickly.","Lawful suppliers seek compensation and some essential deliveries are interrupted."],
  ["Review each contract against the law and preserve essential services","Legal, audit and delivery teams separate their responsibilities.","Some waste is corrected while necessary contracts remain; the investigation costs money."],
  ["Ignore the dispute to protect relationships with suppliers","Purchasing continues as before.","Poor long-term commitments remain and questions from the public multiply."],
  ["Publish releasable audit evidence and review contracts case by case","Auditors release permitted findings while protecting legally confidential materials.","Disputed contracts receive proper review and confidence begins to recover."]
 ],
 [
  ["Put all responsibility into one enormous central agency","A single organization takes over the emergency system.","Concentrated powers remove independent checks and running costs grow."],
  ["Create shared emergency plans with independent exercises","Departments keep their technical jobs within common emergency standards.","The system responds more reliably, but backup capability has annual costs."],
  ["Close the crisis file and remove all emergency preparedness","Immediate recurring spending falls.","The next disruption catches ministries without a coordinated plan."],
  ["Build a tiered reserve and reviewable authorization system","Budgets, operational agencies and auditors receive separate responsibilities.","A system with clear review dates can adapt when evidence changes."]
 ]
 ],
 domestic:{
 appointments:[
  ["Appoint the internally nominated candidate immediately","A new director begins work; the procedural dispute remains unresolved.","The outside applicant demands reasons for the changed eligibility standard."],
  ["Restart the competition using the originally published rules","A deputy temporarily leads while both candidates undergo comparable assessment.","An independent panel gives an evidence-based appointment recommendation."],
  ["Leave the deputy in charge indefinitely","No controversial appointment is made, but the vacancy remains.","Cross-department coordination suffers without a permanent director."],
  ["Audit the rules and conduct a time-limited open leadership exercise","Selection and independent review proceed in parallel.","The new rules are easier to defend, but the process costs more."]
 ],
 schools:[
  ["Protect the examination rules without new educational investment","The examinations remain orderly and spending stays controlled.","Existing inequalities in learning opportunities remain."],
  ["Ask specialists to propose a phased plan for underserved schools","Education and Treasury prepare staged teacher and equipment investments.","Some course access improves, but future budgets face pressure."],
  ["Abolish standardized examinations and let every school recommend students","Schools gain discretion quickly.","Inconsistent recommendation criteria generate new complaints."],
  ["Commission an independent review of learning opportunities","Evaluators distinguish exam integrity from resource gaps.","Targeted corrections become possible, with additional inspection costs."]
 ],
 water:[
  ["Fund only the populous first region","Repairs reduce leakage in the main urban network.","An urgent failure in the second region requires additional emergency spending."],
  ["Protect minimum drinking-water safety and phase the repairs","Highest-risk facilities receive priority while the longer plan is reordered.","Health risks fall, though phased construction is somewhat more expensive."],
  ["Split the budget equally between the two regions","Both regions start projects with equal allocations.","Critical works in the more dispersed region still lack adequate funds."],
  ["Independently test all critical sites and set a repair deadline","Inspectors and engineers prioritize verified risks.","Later evidence shows funding aligns better with public safety needs."]
 ],
 procurement:[
  ["Declare corruption proven and punish suppliers immediately","Payments stop and officials announce penalties before the inquiry is complete.","Hospitals face shortages while suppliers challenge the unsupported finding."],
  ["Investigate independently while essential purchasing continues","Auditors secure evidence and urgent supplies remain available under controls.","Contracts are separated by risk and affected parties retain appeal rights."],
  ["Accept the department's explanation and close the inquiry","Procurement proceeds quickly.","New links between suppliers emerge and confidence in oversight falls."],
  ["Require independent price checks and conflict declarations","Necessary procurement continues with clearer checks.","Review costs rise, but unexplained pricing anomalies are narrowed."]
 ],
 housing:[
  ["Subsidize the same new-building program everywhere","Public construction funds are released quickly.","Some new units remain empty while central rents stay high."],
  ["Let specialists design different housing and transport plans by district","Local teams justify projects against actual need.","Transport improvements and targeted renovation outperform a uniform building plan."],
  ["Suspend all support and leave allocation to the market","Treasury's short-term spending falls.","Acute housing needs in some districts remain unresolved."],
  ["Publish demand data and commission independent project review","Projects are reordered with resident input.","Transparency improves, but redesign and investigation cost money."]
 ],
 oversight:[
  ["Give auditors unrestricted permanent access to every database","Wide data feeds become available immediately.","Privacy complaints grow and the watchdog's own power lacks checks."],
  ["Authorize limited access by case, purpose and time","High-risk investigations obtain controlled data access.","Some irregularities are proven and access rules become clearer."],
  ["Deny every request for new data access","Potential privacy intrusions are avoided for now.","Investigators miss links between ministries."],
  ["Create an external body to review audit access and major searches","Investigators and privacy officers retain distinct appeal channels.","Important cases continue, but oversight reviews take time."]
 ],
 research:[
  ["Invest the entire grant in the big shared facility","The facility gains sufficient funding to begin procurement.","Small teams encounter expensive and slow access."],
  ["Fund both approaches in stages against scientific milestones","Teams receive limited resources to test their ideas.","Evidence improves over time, but major construction is delayed."],
  ["Suspend every research grant","The treasury avoids new spending.","Researchers lose opportunities for collaboration and equipment access."],
  ["Have specialists vote under published rules and retain dissent","The expert panel selects a lawful funding path with a review record.","Scientific uncertainty remains, but the decision procedure is credible."]
 ],
 cyber:[
  ["Shut down every public digital service immediately","Security teams can inspect systems without live traffic.","Appointments accumulate and residents lose access to essential services."],
  ["Isolate the risky interface and keep essential manual services open","Engineers apply a targeted repair plan.","Most public services recover as investigators identify the failure."],
  ["Keep all systems running with no precautions","Appointments continue without disruption at first.","Suspicious activity spreads and recovery becomes harder."],
  ["Ask independent security specialists to verify the cause and publish safe notices","Repairs proceed alongside carefully limited public information.","Users receive better recovery information while investigation costs rise."]
 ],
 transit:[
  ["Keep the same passenger-volume target in every region","Reports remain simple and comparable.","Remote authorities cut essential routes with low ridership."],
  ["Allow different regional indicators, verified independently","Local transport plans are revised for real service needs.","Basic access improves, though evaluation becomes more complex."],
  ["Remove all performance reviews","Local administrators gain broad discretion.","Underserved routes and waste become harder to identify."],
  ["Set binding minimum service standards before local indicators","Departments specify essential coverage, then choose appropriate metrics.","Regional disputes decrease but monitoring remains necessary."]
 ]
 },
 follow:[
  ["Keep the earlier decision and set a fixed review date","The department continues, with a new evidence deadline.","If results fail to improve, the case will need more oversight."],
  ["Order targeted correction with a deadline for affected people","Specialists revise implementation and publish remedial steps.","Some harm is reduced, with additional administrative costs."],
  ["Reverse the earlier order without a transition plan","The department stops following the old order immediately.","Existing commitments are disrupted, potentially worsening the problem."],
  ["Commission an independent performance and procedure review","Investigators examine what happened and who held responsibility.","Public records improve, but the audit cannot solve every underlying issue."]
 ],
 review:[
  ["Merge all review bodies into one authority","Administrative steps become faster, but powers are concentrated.","Weak checks may allow similar failures to return."],
  ["Remove duplicate steps while preserving independent audit powers","Departments simplify work without merging supervision into procurement.","Costs may fall while the ability to challenge decisions remains."],
  ["Leave all current procedures unchanged","The same reporting arrangements remain in place.","Repeated forms and unclear accountability keep consuming resources."],
  ["Order a time-limited independent review and public summary","An external panel maps unresolved issues and responsibilities.","Reform becomes more transparent, even if not every problem is solved immediately."]
 ]
};
window.REPUBLIC_EN.review = {
 normal:{
  category:"Organizational oversight · System review",title:"Overlapping approvals across ministries",agency:"Administrative Reform Commission",
  report:"Six cross-ministry programs use different data forms, and three require entering the same information twice. Treasury estimates shared data entry could lower costs; auditors warn that merging approval and review powers could remove essential checks.",
  views:"Departments want to simplify every approval. The audit authority argues that a team signing a contract should not also conduct the only review of that contract.",
  question:"Should duplicate paperwork be eliminated while independent audit powers remain separate?",
  audit:"Sampling shows that inconsistent form definitions create much of the duplicate effort. Data interfaces can be shared while procurement and independent contract review remain distinct."
 },
 final:{
  category:"Independent oversight · End-of-term handover",title:"Independent review before the handover",agency:"Public Representatives and Audit Panel",
  report:"The oversight panel has submitted the term-end register. Some programs have been completed, while others still await inspection or a final response. Representatives want every open matter assigned to a responsible office and a deadline.",
  views:"Departments want to announce the administration's results quickly. Auditors insist that unresolved investigations, contracts and appeals stay in the handover records.",
  question:"Declare everything finished, or require a clear list of outstanding work, responsible officials and review dates?",
  audit:"Some measures were implemented but not formally verified. Several appeals must continue under the law. An anonymized public status register is possible."
 }
};
window.REPUBLIC_EN.common={
  phases:["Emergency response","Implementation gaps","Accountability and contracts","Long-term safeguards"],
  prior:[
    "The earlier phase granted broad emergency powers. Action was fast, but spending and procedural questions remain.",
    "The earlier phase used limited, staged authorization. Some needs improved, but costs and practical obstacles are emerging.",
    "The earlier phase lacked effective national coordination. Ministries competed for resources, and citizens have filed complaints.",
    "The earlier phase used independently checked evidence to revise the policy. Some conditions improved, but the new approach has its own costs."
  ],
  categoryCrisis:"International crisis · ",
  categoryDomestic:"Domestic policy and administration",
  categoryFollow:"Case reopened · Second ruling",
  followTitle:" · Implementation review",
  followAgency:" · Audit Secretariat",
  followReportStart:"Previous order: ",
  followReportMiddle:". Department's latest report: ",
  followViews:"The responsible department wants to keep the original plan to avoid transition costs. Auditors say new findings require a responsible officer, deadline and verifiable correction—not just optimistic progress reports.",
  followQuestion:"Can this case now close, or should the ministry correct its work or face further inquiry?",
  followAudit:"Auditors checked the earlier order, operational records and a sample of field evidence. Some reports lack clear spending or accountability details. These gaps need correction but do not in themselves prove deliberate wrongdoing.",
  morningFirst:"Several urgent submissions have reached the cabinet office this morning. They are ordered by decision deadline.",
  morningLater:"New submissions and implementation reports have arrived. Today's agenda follows.",
  morningNone:"No earlier case is due today. International and domestic risks are still evolving.",
  dayTitle:"Day {day} · Cabinet morning report",
  agendaCount:"{total} matters need decisions today; {follow} are reopened cases.",
  casePosition:"Day {day} · Matter {num} of {total}",
  caseSpeaker:" · Submission",
  clock:"Day {day} of 12 · {status}",
  clockStatus:{case:"Under review",end:"Term review",other:"State bulletin"},
  decisionReminder:{
    crisis:"This decision will shape later crisis stages. Implementation costs and reports will return in subsequent days.",
    domestic:"This case has been added to the follow-up register. A later report will require another decision.",
    follow:"This review is recorded. Its result will contribute to the term assessment."
  },
  eveningTitle:"Day {day} · Orders issued",
  reportLabel:"IMPLEMENTATION REPORT · ",
  crisisReportLabel:"INTERNATIONAL CRISIS FOLLOW-UP · ",
  endingTitles:["Term review: some institutional gains","Term review: progress with trade-offs","Term review: rising pressure on the Republic"],
  endingBody:"The Republic has completed twelve working days, with {decisions} rulings and {audits} independent audits. The mean of four fictional indicators is {avg}. There are {pending} unresolved cases. Scores cannot establish which real-world governance model works best.",
  crisisResume:"World crisis for this administration: ",
  timelineDay:"Day {day} · "
};
