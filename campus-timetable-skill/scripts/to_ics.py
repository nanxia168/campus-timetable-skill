#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""courses.json -> iCalendar (.ics)

确定性生成：不使用任何语言模型。规则依据见 references/ics-rules.md。

用法：
    python scripts/to_ics.py courses.json -o courses.ics
    python scripts/to_ics.py courses.json --check
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys

TZ = "Asia/Shanghai"
WEEKDAY_CN = "一二三四五六日"
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def die(msg):
    raise SystemExit("[to_ics] 错误：" + msg)


# ----------------------------------------------------------------- 读入与校验
def load(path):
    if not os.path.exists(path):
        die("找不到文件：" + path)
    with open(path, encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            die(f"{path} 不是合法 JSON：{e}")


def norm_weeks(w, where):
    w = w or {}
    t = w.get("type", "ranges")
    if t not in ("all", "odd", "even", "ranges"):
        die(f"{where}.weeks.type 非法：{t!r}")
    weeks = []
    for r in w.get("ranges") or []:
        if not (isinstance(r, list) and len(r) == 2):
            die(f"{where}.weeks.ranges 里 {r!r} 不是 [起, 止]")
        a, b = int(r[0]), int(r[1])
        if a < 1 or b < a or b > 60:
            die(f"{where}.weeks.ranges 区间非法：{r!r}")
        weeks.extend(range(a, b + 1))
    weeks.extend(int(x) for x in (w.get("explicit") or []))
    weeks = sorted(set(weeks))
    if t == "odd":
        weeks = [x for x in weeks if x % 2 == 1]
    elif t == "even":
        weeks = [x for x in weeks if x % 2 == 0]
    if not weeks:
        die(f"{where}.weeks 展开后为空")
    return weeks, (2 if t in ("odd", "even") else 1)


def check_session(s, where):
    wd = s.get("weekday")
    if wd not in (1, 2, 3, 4, 5, 6, 7):
        die(f"{where}.weekday 必须是 1-7，实际 {wd!r}")
    periods = s.get("periods") or []
    if not periods or not all(isinstance(p, int) and p >= 1 for p in periods):
        die(f"{where}.periods 必须是非空整数数组，实际 {periods!r}")
    for key in ("start_time", "end_time"):
        v = s.get(key) or ""
        if not TIME_RE.match(v):
            die(f"{where}.{key} 必须是 HH:MM，实际 {v!r}")
    if s["end_time"] <= s["start_time"]:
        die(f"{where} 结束时间不晚于开始时间（{s['start_time']}→{s['end_time']}）")


def collect(doc):
    meta = doc.get("meta") or {}
    base = meta.get("semester_start_date")
    if not base:
        die("meta.semester_start_date 缺失（必须是第 1 周的星期一）")
    try:
        start = dt.date.fromisoformat(base)
    except ValueError:
        die(f"meta.semester_start_date 不是 YYYY-MM-DD：{base!r}")
    if start.isoweekday() != 1:
        die(
            f"meta.semester_start_date={base} 是星期{WEEKDAY_CN[start.isoweekday() - 1]}，"
            "必须是第 1 周的星期一（错一天，整学期都会偏）"
        )

    # 调休例外：code 和 name 是两种可选的匹配方式，不能拼进同一个键
    shift_by_code, shift_by_name = {}, {}
    for sh in meta.get("day_shifts") or []:
        k = (sh.get("weekday"), sh.get("week"))
        days = int(sh.get("days", 0))
        if sh.get("code"):
            shift_by_code[(str(sh["code"]),) + k] = days
        if sh.get("name"):
            shift_by_name[(str(sh["name"]),) + k] = days

    courses = doc.get("courses") or []
    if not courses:
        die("courses 为空")

    events = []          # 每条 = 一个 VEVENT
    occurrences = []     # 每次实际上课
    for ci, c in enumerate(courses):
        name = (c.get("name") or "").strip()
        if not name:
            die(f"courses[{ci}] 缺 name")
        code = c.get("code")
        sessions = c.get("sessions") or []
        if not sessions:
            die(f"courses[{ci}]（{name}）没有 sessions")
        for si, s in enumerate(sessions):
            where = f"courses[{ci}].sessions[{si}]（{name}）"
            check_session(s, where)
            weeks, step = norm_weeks(s.get("weeks"), where)

            runs = []
            for w in weeks:
                if runs and w == runs[-1][-1] + step:
                    runs[-1].append(w)
                else:
                    runs.append([w])

            loc = s.get("location") or {}
            room = loc.get("room") or loc.get("raw") or "未标注"
            teachers = c.get("teachers") or []
            tdesc = "教师：" + ("、".join(teachers) if teachers else "未标注")

            for run in runs:
                first, last = run[0], run[-1]
                day = start + dt.timedelta(days=(first - 1) * 7 + (s["weekday"] - 1))
                delta = shift_by_code.get((str(code), s["weekday"], first)) if code else None
                if delta is None:
                    delta = shift_by_name.get((name, s["weekday"], first), 0)
                day += dt.timedelta(days=delta)
                p1, p2 = s["periods"][0], s["periods"][-1]
                desc = (
                    f"{tdesc}｜第{p1}-{p2}节｜第{first}-{last}周"
                    + ("" if room != "未标注" else "｜地点未标注")
                )
                key = f"{code or name}|{s['weekday']}|{p1}-{p2}|{first}"
                uid = "ct-" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12] + "@campus-timetable"
                ev = {
                    "uid": uid, "date": day, "start": s["start_time"], "end": s["end_time"],
                    "summary": f"{name}（{code}）" if code else name,
                    "location": room, "desc": desc,
                    "rrule": None if len(run) == 1 else (step, len(run)),
                    "count": len(run), "step": step, "first_week": first,
                }
                events.append(ev)
                for i in range(len(run)):
                    occurrences.append({
                        "start": dt.datetime.combine(day + dt.timedelta(days=7 * i * step),
                                                     dt.time.fromisoformat(s["start_time"])),
                        "end": dt.datetime.combine(day + dt.timedelta(days=7 * i * step),
                                                   dt.time.fromisoformat(s["end_time"])),
                        "name": name, "room": room,
                    })
    return start, events, occurrences


# ----------------------------------------------------------------- 写出 ICS
def fold(line, limit=75):
    out, cur, n = [], "", 0
    for ch in line:
        b = len(ch.encode("utf-8"))
        if n + b > limit - 2:      # 留 2 octets 给续行的前导空格
            out.append(cur)
            cur, n = "", 0
        cur += ch
        n += b
    out.append(cur)
    return "\r\n ".join(out)


def esc(s):
    return (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r", "").replace("\n", "\\n")


def render(events, calendar_name, stamp):
    L = [
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "PRODID:-//campus-timetable-skill//CN", "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        fold("X-WR-CALNAME:" + esc(calendar_name)),
        "X-WR-TIMEZONE:" + TZ,
        "BEGIN:VTIMEZONE", "TZID:" + TZ, "BEGIN:STANDARD", "DTSTART:19700101T000000",
        "TZOFFSETFROM:+0800", "TZOFFSETTO:+0800", "TZNAME:CST",
        "END:STANDARD", "END:VTIMEZONE",
    ]
    for e in events:
        d = e["date"].strftime("%Y%m%d")
        L.append("BEGIN:VEVENT")
        L.append("UID:" + e["uid"])
        L.append("DTSTAMP:" + stamp)
        L.append(f"DTSTART;TZID={TZ}:{d}T{e['start'].replace(':', '')}00")
        L.append(f"DTEND;TZID={TZ}:{d}T{e['end'].replace(':', '')}00")
        if e["rrule"]:
            step, count = e["rrule"]
            L.append(f"RRULE:FREQ=WEEKLY;INTERVAL={step};COUNT={count}")
        L.append(fold("SUMMARY:" + esc(e["summary"])))
        L.append(fold("LOCATION:" + esc(e["location"])))
        L.append(fold("DESCRIPTION:" + esc(e["desc"])))
        L.extend([
            "BEGIN:VALARM", "TRIGGER:-PT10M", "ACTION:DISPLAY",
            fold("DESCRIPTION:" + esc(e["summary"] + " 10 分钟后开始")),
            "END:VALARM",
        ])
        L.append("END:VEVENT")
    L.append("END:VCALENDAR")
    return "\r\n".join(L) + "\r\n"


# ----------------------------------------------------------------- 报告
def report(start, events, occurrences, out_path=None):
    occurrences.sort(key=lambda o: o["start"])
    print(f"第 1 周星期一 : {start}（校验：第 3 周周三 = {start + dt.timedelta(days=16)}）")
    print(f"VEVENT     : {len(events)}")
    print(f"上课次数   : {len(occurrences)}")

    conflicts = []
    for i in range(1, len(occurrences)):
        if occurrences[i]["start"] < occurrences[i - 1]["end"]:
            conflicts.append((occurrences[i - 1], occurrences[i]))
    print(f"时间冲突   : {len(conflicts)}")
    for a, b in conflicts[:5]:
        print(f"  !! {a['start']:%m-%d %H:%M} {a['name']}  ×  {b['start']:%m-%d %H:%M} {b['name']}")

    if occurrences:
        first = occurrences[0]
        print(f"最早一次课 : {first['start']:%Y-%m-%d %H:%M} {first['name']} {first['room']}")
        seen = {}
        for o in occurrences:
            seen.setdefault(o["start"].date(), o)
        head = sorted(seen)[:5]
        print("前 5 个上课日：")
        for d in head:
            day = [o for o in occurrences if o["start"].date() == d]
            print(f"  {d} 周{WEEKDAY_CN[d.isoweekday() - 1]}  " + "；".join(
                f"{o['start']:%H:%M} {o['name']}" for o in day))
    if out_path:
        print(f"已写出     : {out_path}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="courses.json -> .ics")
    ap.add_argument("input", help="courses.json 路径")
    ap.add_argument("-o", "--out", help="输出 .ics 路径（--check 时可省略）")
    ap.add_argument("--check", action="store_true", help="只校验并打印统计，不写文件")
    ap.add_argument("--stamp", default=None, help="覆盖 DTSTAMP（UTC，形如 20260101T000000Z）")
    args = ap.parse_args(argv)

    doc = load(args.input)
    start, events, occurrences = collect(doc)
    stamp = args.stamp or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if not args.check:
        out = args.out or os.path.splitext(args.input)[0] + ".ics"
        name = (doc.get("meta") or {}).get("calendar_name") or "我的课表"
        data = render(events, name, stamp)
        with open(out, "w", encoding="utf-8", newline="") as f:
            f.write(data)
        report(start, events, occurrences, out)
        longest = max(len(l.encode("utf-8")) for l in data.split("\r\n"))
        print(f"最长物理行 : {longest} octets（上限 75）")
    else:
        report(start, events, occurrences)
    return 0


if __name__ == "__main__":
    sys.exit(main())
