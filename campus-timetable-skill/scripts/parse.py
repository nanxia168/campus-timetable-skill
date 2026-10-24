#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""课表截图 -> courses.json（调用 OpenAI 兼容的视觉模型）

环境变量：
    FINCH_AI_API_KEY   必填
    FINCH_AI_BASE_URL  可选，默认 https://api.openai.com/v1
    FINCH_AI_MODEL     必填，必须是支持视觉的模型（名字里常带 vision / vl / pro-vision）

用法：
    run.cmd scripts/parse.py --image kebiao.png --out courses.json
"""

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPT_FILE = os.path.join(HERE, "..", "references", "parse-prompt.md")
REQUIRED_META = ("semester_start_date", "assumptions")


def die(msg):
    raise SystemExit("[parse] 错误：" + msg)


def load_prompt():
    path = os.path.abspath(PROMPT_FILE)
    if not os.path.exists(path):
        die("找不到提示词文件：" + path)
    text = open(path, encoding="utf-8").read()
    m = re.search(r"```[a-zA-Z]*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


def call_model(image_path, prompt, base, key, model):
    raw = open(image_path, "rb").read()
    if len(raw) > 8 * 1024 * 1024:
        die("图片超过 8MB，先压缩或裁剪再传")
    mime = "image/png" if raw[:4] == b"\x89PNG" else "image/jpeg"
    b64 = base64.b64encode(raw).decode()
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": [
                {"type": "text", "text": "按格式解析这张课表，只输出 JSON。"},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ]},
        ],
    }
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        die(f"模型接口返回 {e.code}：{detail}")
    except urllib.error.URLError as e:
        die(f"连不上 {base}：{e.reason}")
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        die("接口返回结构异常：" + json.dumps(body, ensure_ascii=False)[:400])
    text = ""
    for part in content if isinstance(content, list) else [content]:
        if isinstance(part, dict):
            text += part.get("text", "")
        else:
            text += str(part)
    return text, body.get("usage")


def extract_json(text):
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    raw = m.group(1) if m else text[text.find("{"): text.rfind("}") + 1]
    if not raw:
        die("模型输出里没有找到 JSON")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        die(f"模型返回的不是合法 JSON（{e}）。原始输出片段：{text[:300]}")


def validate(doc):
    meta = doc.get("meta") or {}
    for k in REQUIRED_META:
        if k not in meta:
            die(f"meta 缺字段 {k}")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(meta.get("semester_start_date", ""))):
        die("meta.semester_start_date 必须是 YYYY-MM-DD")
    courses = doc.get("courses")
    if not isinstance(courses, list) or not courses:
        die("courses 必须是非空数组")
    sess = 0
    for i, c in enumerate(courses):
        if not c.get("name"):
            die(f"courses[{i}] 缺 name")
        if not c.get("sessions"):
            die(f"courses[{i}]（{c.get('name')}）没有 sessions")
        sess += len(c["sessions"])
    return len(courses), sess


def main(argv=None):
    ap = argparse.ArgumentParser(description="课表截图 -> courses.json")
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", default="courses.json")
    ap.add_argument("--base", default=os.environ.get("FINCH_AI_BASE_URL", "https://api.openai.com/v1"))
    ap.add_argument("--model", default=os.environ.get("FINCH_AI_MODEL"))
    args = ap.parse_args(argv)

    key = os.environ.get("FINCH_AI_API_KEY")
    if not key:
        die("未设置 FINCH_AI_API_KEY。示例：\n"
            '  PowerShell : $env:FINCH_AI_API_KEY="sk-..."\n'
            "  bash       : export FINCH_AI_API_KEY=sk-...")
    if not args.model:
        die("未指定模型。用 FINCH_AI_MODEL 或 --model 指定一个支持视觉的模型")
    if not os.path.exists(args.image):
        die("找不到图片：" + args.image)

    prompt = load_prompt()
    text, usage = call_model(args.image, prompt, args.base, key, args.model)
    doc = extract_json(text)
    n_course, n_sess = validate(doc)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"已写出 {args.out}：{n_course} 门课，{n_sess} 条 session")
    if usage:
        print("token 用量：" + json.dumps(usage, ensure_ascii=False))
    tail = text[text.rfind("}"):].strip()
    if tail:
        print("\n模型自检说明：\n" + tail[:800])
    print("\n下一步（不要跳过校验）：\n"
          f"  run.cmd scripts/to_ics.py {args.out} --check\n"
          "然后对照原图核三件事：课程数量 / 随机 3 条节次 / 单双周标签")
    return 0


if __name__ == "__main__":
    sys.exit(main())
