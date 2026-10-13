"""Checks for the agreed newspaper editorial contract and independent schedule."""
import datetime as dt
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from newsroom import SECTIONS,prepare_pool,select_readable
from brief_editor import edit_article
from digest import edition_window,BEIJING_TZ

class EditorialContract(unittest.TestCase):
    def test_approved_seven_sections(self):
        self.assertEqual(list(SECTIONS),[
            "美股·全球金融市场","中国与美国","国际政治与全球事件",
            "AI与数字产业","科技、能源与前沿科学",
            "创业、商业与企业竞争","医疗、生命科学与公共健康"])
        self.assertEqual(SECTIONS["中国与美国"],3)
        self.assertEqual(sum(SECTIONS.values()),16)

    def test_us_china_events_do_not_repeat_in_other_domains(self):
        inputs=[
            dict(title="US Federal Reserve approves national financial regulation",
                 summary="banking and markets",source="Outlet 1",url="https://a.example/1"),
            dict(title="China government announces new semiconductor export policy",
                 summary="chip trade",source="Outlet 2",url="https://b.example/2"),
            dict(title="US government announces new AI chip regulation",
                 summary="artificial intelligence and technology",source="Outlet 3",url="https://c.example/3"),
        ]
        pool=prepare_pool(inputs)
        found={a["url"]:a for items in pool.values() for a in items}
        result,_=select_readable(pool,found)
        self.assertEqual(len(result["中国与美国"]),3)
        keys=[a["event_key"] for items in result.values() for a in items]
        self.assertEqual(len(keys),len(set(keys)))

    def test_no_abstract_and_qualifiers_retained(self):
        chunks=[
            "The regulator issued a preliminary proposal that may affect 500 participants. "*16,
            "However, officials cautioned that the proposal is not yet approved. "*12,
            "The statement explains the timetable for parliamentary review and implementation. "*16,
            "Analysts and participants described conflicting views about the potential effect. "*16,
        ]
        result=edit_article({"reading_en":"\n\n".join(chunks),"importance_score":90})
        self.assertGreaterEqual(result["retained_words"],330)
        self.assertIn("not yet approved",result["reading_en"])
        self.assertTrue(result["source_map"])

    def test_0100_beijing_schedule_is_not_regressed(self):
        start,end,_=edition_window(dt.datetime(2026,10,14,1,25,tzinfo=BEIJING_TZ))
        self.assertEqual((start.hour,end.hour),(1,1))
        workflow=(Path(__file__).resolve().parent.parent/".github/workflows/newspaper.yml").read_text()
        # Latest deployed policy is authoritative: 01:00 cutoff, off-hour
        # triggers between 01:00 and 02:00; do not lock tests to old minutes.
        import re
        schedules = re.findall(r"cron: '([0-9]+) ([0-9]+) \\* \\* \\*'", workflow)
        self.assertGreaterEqual(len(schedules), 3)
        minutes = [int(minute) for minute, hour in schedules if int(hour) == 17]
        self.assertEqual(len(minutes), len(schedules))
        self.assertTrue(all(0 < minute < 60 for minute in minutes))
        self.assertLessEqual(min(minutes), 10)
        self.assertLessEqual(max(minutes), 50)
        self.assertEqual(len(set(minutes)), len(minutes))

if __name__=="__main__": unittest.main()
