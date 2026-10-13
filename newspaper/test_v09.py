"""Regression tests for missed/double mail and editorial loss of meaning."""
import datetime as dt
import json
import smtplib
import unittest
from email.message import EmailMessage
from unittest.mock import Mock
from brief_editor import edit_article
from newsroom import prepare_pool, select_readable, countries, publisher, score, SECTIONS
from reliable_mail import deliver, AcceptanceUncertain
from edition_ai import edit_and_analyze

def item(title, n, **extra):
    return dict(title=title, summary=title, source="Outlet "+str(n),
                url=f"https://outlet{n}.com/news/{n}", **extra)

class MemoryJournal:
    day = "2026-10-13"
    def __init__(self): self.state = {}; self.history = []
    def decision(self):
        return "accepted" if self.state.get("status")=="accepted" else "review_required" if self.state.get("status") in {"sending","uncertain"} else "send"
    def write(self, **kw): self.state.update(kw); self.history.append(dict(self.state))

class V09Tests(unittest.TestCase):
    def test_us_pronoun_is_not_united_states(self):
        self.assertNotIn("美国", countries(item("Researchers tell us about a new experiment",1)))
        self.assertIn("美国", countries(item("US company launches a new AI service",1)))

    def test_publishers_not_feed_names(self):
        a = item("China announces new trade policy",1)
        b = dict(a,source="BBC China",url="https://www.bbc.co.uk/news/a")
        c = dict(a,source="BBC World",url="https://www.bbc.com/news/a")
        self.assertEqual(publisher(b),publisher(c))

    def test_systemic_change_above_local_keyword_noise(self):
        small=item("India local election candidates announce funding for a festival",1)
        large=item("India announces grain export ban affecting global food supply chain",2)
        self.assertGreater(score(large,1)[0],score(small,5)[0])

    def test_three_china_us_and_unique_events_across_all_sections(self):
        titles=["China announces central bank policy rate cut", "US Congress approves national financial regulation",
                "China company announces international acquisition", "Japan government announces national election",
                "Russia president signs military treaty", "France parliament approves national policy",
                "India parliament approves new law", "India president signs national law"]
        articles=[item(t,i) for i,t in enumerate(titles)]
        # Same event from a different publisher must not occupy another section.
        articles.append(item(titles[0],20))
        pool=prepare_pool(articles)
        enriched={a['url']:a for v in pool.values() for a in v}
        selected,diag=select_readable(pool,enriched)
        self.assertEqual(len(selected['中国与美国']),3)
        self.assertFalse(diag['中国与美国']['missing_regions'])
        all_events=[a['event_key'] for v in selected.values() for a in v]
        self.assertEqual(len(all_events),len(set(all_events)))
        self.assertLessEqual(diag['国际政治与全球事件']['country_counts'].get('印度',0),1)

    def test_shortage_is_recorded_instead_of_fabricated(self):
        pool=prepare_pool([item("India government announces new local law",1)])
        selected,diag=select_readable(pool,{a['url']:a for v in pool.values() for a in v})
        self.assertEqual(selected['中国与美国'],[])
        self.assertEqual(diag['中国与美国']['shortfall'],3)
        self.assertEqual(diag['中国与美国']['missing_regions'],['中国','美国'])

    def test_edit_preserves_limits_attribution_and_source_spans(self):
        ps=["A company announced a new treatment trial with 500 participants. "*8,
            "The report describes the trial design and its planned timetable. "*8]
        ps += ["The ceremony had decorative lighting and a long history of evening receptions. "*10 for _ in range(10)]
        ps += ["However, the treatment is not approved and the preliminary trial could fail. Researchers cautioned that the sample is small."]
        a=edit_article({'reading_en':'\n\n'.join(ps)},[0,1])
        self.assertIn(ps[-1],a['reading_en'])
        self.assertGreaterEqual(a['retained_words'],330)
        self.assertLess(a['retained_words'],a['captured_words'])
        self.assertEqual(a['reading_en'].split('\n\n'),[ps[i] for i in a['original_paragraphs_kept']])
        self.assertTrue(a['source_map'])
        with self.assertRaises(ValueError): edit_article({'reading_en':'source'},[900])

    def message(self):
        m=EmailMessage();m['To']='reader@example.com';m['From']='sender@example.com';m.set_content('edition')
        return m

    def test_quit_failure_does_not_resend_accepted_mail(self):
        smtp=Mock();smtp.send_message.return_value={};smtp.quit.side_effect=OSError('network')
        journal=MemoryJournal()
        result=deliver(self.message(),'sender@example.com','secret','host',465,journal,factory=Mock(return_value=smtp))
        self.assertEqual(result,'accepted');self.assertEqual(journal.state['status'],'accepted')
        smtp.send_message.assert_called_once()
        factory=Mock()
        self.assertEqual(deliver(self.message(),'sender@example.com','secret','host',465,journal,factory=factory),'already_accepted')
        factory.assert_not_called()

    def test_connect_retry_does_not_regenerate_edition(self):
        smtp=Mock();smtp.send_message.return_value={}
        factory=Mock(side_effect=[OSError('down'),smtp]);journal=MemoryJournal()
        deliver(self.message(),'sender@example.com','secret','host',465,journal,factory=factory,pause=lambda _:None)
        self.assertEqual(factory.call_count,2);smtp.send_message.assert_called_once()

    def test_ambiguous_data_response_requires_review(self):
        smtp=Mock();smtp.send_message.side_effect=TimeoutError('response lost')
        factory=Mock(return_value=smtp);journal=MemoryJournal()
        with self.assertRaises(AcceptanceUncertain):
            deliver(self.message(),'sender@example.com','secret','host',465,journal,factory=factory,pause=lambda _:None)
        self.assertEqual(journal.state['status'],'uncertain');self.assertEqual(factory.call_count,1)
        with self.assertRaises(AcceptanceUncertain):
            deliver(self.message(),'sender@example.com','secret','host',465,journal,factory=factory)
        self.assertEqual(factory.call_count,1)

    def test_auth_failure_never_retries_or_leaks_password(self):
        smtp=Mock();smtp.login.side_effect=smtplib.SMTPAuthenticationError(535,b'bad')
        factory=Mock(return_value=smtp)
        with self.assertRaises(RuntimeError) as cm:
            deliver(self.message(),'sender@example.com','secret','host',465,MemoryJournal(),factory=factory)
        self.assertNotIn('secret',str(cm.exception));self.assertEqual(factory.call_count,1)

    def test_one_paid_call_handles_editing_and_commentary(self):
        a=item('Company announces new AI platform',1,reading_en='The company announced an international launch. '*70,event_key='e1')
        response=Mock(status_code=200)
        response.json.return_value={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(
            {'plans':{'e1':[0]},'commentary':'根据来源事实分析，仍需关注不确定条件。'*50})}}],
            'usage':{'prompt_tokens':3000,'completion_tokens':1800}}
        request=Mock(return_value=response);before=Mock()
        plans,commentary,usage=edit_and_analyze({'AI与数字产业':[a]},dt.date(2026,10,12),'fake',transport=request,before_request=before)
        self.assertEqual(plans,{'e1':[0]});self.assertEqual(usage['request_count'],1)
        request.assert_called_once();before.assert_called_once()
        self.assertEqual(request.call_args.kwargs['json']['max_tokens'],3400)

if __name__=='__main__': unittest.main()
