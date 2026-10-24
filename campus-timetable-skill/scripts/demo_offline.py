#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线演示：不调用任何模型，用内置样例把整条管道跑一遍。

用途只有两个：
  1. 网络不通 / 没有 API Key 时，让人看见"这个包能跑出东西"
  2. 验证除模型调用之外的环节（校验、写文件、报错）

**它不验证识别效果。** 真实识别请用：
    run.cmd scripts/parse.py --image kebiao.png --out courses.json
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parse as parser  # noqa: E402  复用同一个 validate，不重复实现

EXAMPLE = os.path.join(HERE, "..", "examples", "26软件5.json")


def main(argv=None):
    ap = argparse.ArgumentParser(description="离线演示：用内置样例跑通管道（不调模型）")
    ap.add_argument("--out", default="courses.json", help="输出文件名（默认 courses.json）")
    ap.add_argument("--quiet", action="store_true", help="不打印横幅")
    args = ap.parse_args(argv)

    src = os.path.abspath(EXAMPLE)
    if not os.path.exists(src):
        raise SystemExit("[demo] 找不到内置样例：" + src)

    if not args.quiet:
        print("=" * 66)
        print("  [offline] 未调用任何模型。以下结果读自 examples/26软件5.json")
        print("            真实课表，已人工校对。它证明的是【管道通】，不是【识别准】。")
        print("=" * 66)

    with open(src, encoding="utf-8") as f:
        doc = json.load(f)

    # 打上标记，防止这份文件被当成"模型输出"交出去或被误用
    doc.setdefault("meta", {})["offline_demo"] = True

    n_course, n_sess = parser.validate(doc)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"写出 {args.out}：{n_course} 门课 / {n_sess} 条 session"
          "（meta.offline_demo = true）")
    print()
    print("下一步：")
    print(f"  生成日历   run.cmd scripts/to_ics.py {args.out} -o courses.ics")
    print("  真实识别   run.cmd scripts/parse.py --image kebiao.png --out courses.json")
    print("  （真实识别需要 FINCH_AI_API_KEY 与一个支持视觉的模型）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
