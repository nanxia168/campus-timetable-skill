#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""to_ics.py 的回归测试。

    python -m unittest discover -s tests -v

这些数字不是随便写的，是 2026 级 26软件5 班真实课表的正确答案。
改脚本之后跑一遍，任何一条挂了就说明改坏了。
"""

import datetime as dt
import importlib.util
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPT = os.path.join(ROOT, "scripts", "to_ics.py")
EXAMPLE = os.path.join(ROOT, "examples", "26软件5.json")

spec = importlib.util.spec_from_file_location("to_ics", SCRIPT)
to_ics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(to_ics)


def build(stamp="20260101T000000Z"):
    doc = to_ics.load(EXAMPLE)
    start, events, occurrences = to_ics.collect(doc)
    meta = doc["meta"]
    return doc, start, events, occurrences, to_ics.render(events, meta["calendar_name"], stamp)


class TestExampleTimetable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc, cls.start, cls.events, cls.occurrences, cls.ics = build()
        cls.lines = cls.ics.split("\r\n")

    def test_week1_monday(self):
        """第 1 周必须是星期一，且能反推出校历的开学日。"""
        self.assertEqual(self.start, dt.date(2026, 8, 31))
        self.assertEqual(self.start.isoweekday(), 1)
        # 第 3 周周三 = 2026-09-16，正是 2026 级正式上课日
        self.assertEqual(self.start + dt.timedelta(days=16), dt.date(2026, 9, 16))

    def test_event_and_occurrence_counts(self):
        self.assertEqual(len(self.events), 31, "VEVENT 数量变了，检查 RRULE 分段")
        self.assertEqual(len(self.occurrences), 150, "上课次数变了，检查周次展开")

    def test_no_conflicts(self):
        occ = sorted(self.occurrences, key=lambda o: o["start"])
        for a, b in zip(occ, occ[1:]):
            self.assertGreaterEqual(b["start"], a["end"], f"{a['name']} 与 {b['name']} 时间重叠")

    def test_single_week_is_compressed(self):
        """单周课必须压成一条 INTERVAL=2，不能展开成 9 条。"""
        rrules = [l for l in self.lines if l.startswith("RRULE:")]
        self.assertIn("RRULE:FREQ=WEEKLY;INTERVAL=2;COUNT=9", rrules)
        self.assertEqual(len([r for r in rrules if "INTERVAL=2" in r]), 1)

    def test_first_class(self):
        first = min(self.occurrences, key=lambda o: o["start"])
        self.assertEqual(first["start"], dt.datetime(2026, 9, 16, 8, 30))
        self.assertEqual(first["name"], "思想道德与法治")
        self.assertEqual(first["room"], "I402")

    def test_holiday_shift(self):
        """调休：程序设计基础 第6周周五 应落在 10/10 周六，且 10/9 没有它。"""
        tenth = [o for o in self.occurrences
                 if o["start"].date() == dt.date(2026, 10, 10)]
        names = {o["name"] for o in tenth}
        self.assertIn("程序设计基础", names)
        self.assertIn("实用英语1", names)
        ninth = {o["name"] for o in self.occurrences if o["start"].date() == dt.date(2026, 10, 9)}
        self.assertNotIn("程序设计基础", ninth)

    def test_odd_week_course(self):
        """单周课：9/16 有、9/23 没有、9/30 有。"""
        def has(day):
            return any(o["name"] == "思想道德与法治" and o["start"].date() == day
                       and o["start"].hour == 8 for o in self.occurrences)
        self.assertTrue(has(dt.date(2026, 9, 16)))
        self.assertFalse(has(dt.date(2026, 9, 23)))
        self.assertTrue(has(dt.date(2026, 9, 30)))

    def test_line_folding(self):
        self.assertTrue(self.ics.startswith("BEGIN:VCALENDAR"))
        self.assertTrue(self.ics.endswith("END:VCALENDAR\r\n"))
        worst = max(len(l.encode("utf-8")) for l in self.lines)
        self.assertLessEqual(worst, 75, f"最长行 {worst} octets，超过 75")
        self.assertNotIn("\n\n", self.ics.replace("\r\n", "\n"), "不该出现空行")

    def test_required_properties(self):
        for ev in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", self.ics, re.S):
            for prop in ("UID:", "DTSTAMP:", "DTSTART;TZID=", "DTEND;TZID=", "SUMMARY:"):
                self.assertIn(prop, ev, f"事件缺 {prop}")
        self.assertIn("BEGIN:VTIMEZONE", self.ics)
        self.assertIn("TRIGGER:-PT10M", self.ics)

    def test_bad_start_date_rejected(self):
        """0807 不是星期一（2026-09-07 是星期一，09-08 不是）。"""
        bad = {"meta": {"semester_start_date": "2026-09-08"}, "courses": []}
        with self.assertRaises(SystemExit):
            to_ics.collect(bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
