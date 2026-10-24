#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把模型网页上复制下来的整段回答，变成合法的 courses.json。

省掉"记事本另存为 UTF-8"那一步——中文 Windows 记事本默认存 GBK，
存错了下一步读文件就会报编码错误。

用法：
    run.cmd scripts/from_text.py --clipboard -o courses.json
    run.cmd scripts/from_text.py --file pasted.txt -o courses.json
"""

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parse as parser  # noqa: E402  复用同一份 JSON 提取与校验


def read_clipboard():
    """Windows 剪贴板：用 # 分隔多行，避免换行被吃掉。"""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "$t = Get-Clipboard -Raw; if ($t) { $t }"],
            capture_output=True, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise SystemExit("[from_text] 读剪贴板失败：" + str(e))
    text = out.stdout.decode("utf-8", "replace")
    if not text.strip():
        raise SystemExit("[from_text] 剪贴板是空的。先在网页上全选复制模型那段回答。")
    return text


def read_file(path):
    if not os.path.exists(path):
        raise SystemExit("[from_text] 找不到文件：" + path)
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise SystemExit("[from_text] 认不出这个文件的编码（试过 utf-8 / gbk）")


def main(argv=None):
    ap = argparse.ArgumentParser(description="把复制下来的模型回答转成 courses.json")
    ap.add_argument("--clipboard", action="store_true", help="从剪贴板读取")
    ap.add_argument("--file", help="从文本文件读取")
    ap.add_argument("-o", "--out", default="courses.json")
    args = ap.parse_args(argv)

    if args.clipboard:
        text = read_clipboard()
        src = "剪贴板"
    elif args.file:
        text = read_file(args.file)
        src = args.file
    else:
        ap.error("要么 --clipboard，要么 --file <路径>")

    doc = parser.extract_json(text)
    n_course, n_sess = parser.validate(doc)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"来源：{src}（{len(text)} 字符）")
    print(f"已写出 {args.out}：{n_course} 门课 / {n_sess} 条 session")
    print()
    print("下一步（校验 + 生成）：")
    print(f"  run.cmd scripts/\to_ics.py {args.out} -o courses.ics")
    return 0


if __name__ == "__main__":
    sys.exit(main())
