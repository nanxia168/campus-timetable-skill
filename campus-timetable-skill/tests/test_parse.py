#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""parse.py 里"非模型部分"的测试：JSON 提取 + 结构校验。

模型那一步必须真调一次才算验证，这里不假装覆盖它。
这些测试全是真断言——负例必须报错退出，正例必须原样通过。
"""

import importlib.util
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location("parse_mod", os.path.join(ROOT, "scripts", "parse.py"))
parse_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parse_mod)

EXAMPLE = os.path.join(ROOT, "examples", "26软件5.json")


def good():
    with open(EXAMPLE, encoding="utf-8") as f:
        return json.load(f)


class TestExtractJson(unittest.TestCase):
    def test_plain_json(self):
        doc = parse_mod.extract_json('{"a": 1}')
        self.assertEqual(doc, {"a": 1})

    def test_fenced_json(self):
        text = '好的，解析完成：\n```json\n{"a": 2}\n```\n以上。'
        self.assertEqual(parse_mod.extract_json(text), {"a": 2})

    def test_chatter_around(self):
        text = '这是结果：\n{"b": [1, 2]}\n希望有帮助。'
        self.assertEqual(parse_mod.extract_json(text), {"b": [1, 2]})

    def test_no_json_raises(self):
        with self.assertRaises(SystemExit):
            parse_mod.extract_json("抱歉，我看不到这张图片。")

    def test_broken_json_raises(self):
        with self.assertRaises(SystemExit):
            parse_mod.extract_json('{"a": 1,}')


class TestValidate(unittest.TestCase):
    def test_example_passes(self):
        n_course, n_sess = parse_mod.validate(good())
        self.assertEqual((n_course, n_sess), (11, 19))

    def test_missing_meta_field(self):
        doc = good()
        del doc["meta"]["assumptions"]
        with self.assertRaises(SystemExit):
            parse_mod.validate(doc)

    def test_bad_date_format(self):
        doc = good()
        doc["meta"]["semester_start_date"] = "2026/08/31"
        with self.assertRaises(SystemExit):
            parse_mod.validate(doc)

    def test_date_not_a_date(self):
        doc = good()
        doc["meta"]["semester_start_date"] = "2026-13-45"
        # 格式合法但日期非法：validate 只查格式，交给 to_ics 拦
        parse_mod.validate(doc)

    def test_empty_courses(self):
        doc = good()
        doc["courses"] = []
        with self.assertRaises(SystemExit):
            parse_mod.validate(doc)

    def test_course_without_name(self):
        doc = good()
        del doc["courses"][0]["name"]
        with self.assertRaises(SystemExit):
            parse_mod.validate(doc)

    def test_course_without_sessions(self):
        doc = good()
        doc["courses"][1]["sessions"] = []
        with self.assertRaises(SystemExit):
            parse_mod.validate(doc)

    def test_optional_fields_may_be_null(self):
        """teachers / code / room 允许为 null，不该因此报错。"""
        doc = good()
        self.assertIsNone(doc["courses"][2]["teachers"])   # 实用英语1 原图无教师
        parse_mod.validate(doc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
