# campus-timetable-skill

> 给 AI Agent 用的一个技能：**一张课表截图 → 手机系统日历**。
> 面向中国高校教务系统（强智 / 正方 / URP / 青果 / 金智等）导出的课表图片。

## 30 秒看懂

```
课表截图 ──[视觉模型]──> courses.json ──[确定性脚本]──> courses.ics ──> 手机日历
            第 1 步            校验            第 3 步
```

- 第 1 步由**多模态大模型**做，它擅长看图
- 第 3 步由**代码**做，因为 iCalendar 要求逐字节合规，模型做不好
- 中间的 `courses.json` 是唯一的交接面，人可以看懂、可以改

## 为什么值得做

中国高校课表的真实痛点不是"看不见课表"，而是：

| 痛点 | 现在怎么做 | 这个技能怎么做 |
| --- | --- | --- |
| 截图满天飞，格式各校不同 | 手动抄 | 一次识别成结构数据 |
| 单双周记不住 | 靠脑子 | `weeks.type: odd/even` 精确落到日历 |
| 调课、国庆调休 | 每次都要问人 | `day_shifts` 一条规则搞定 |
| 教室找不到 | 翻群聊 | 直接进日程的 LOCATION |
| 课前忘 | 无 | 每个事件自带提前 10 分钟提醒 |

## 实测数据

用一份真实的 2026 级课表跑通（26软件5 班）：

| 指标 | 数值 |
| --- | --- |
| 课程 / session | 11 门 / 19 条 |
| 生成的 VEVENT | 31 条（RRULE 压缩，未展开） |
| 展开后上课次数 | 150 次 |
| 学期课时 | 388 节 |
| 时间冲突 | 0 |
| 最长物理行 | 73 octets（上限 75） |
| 开学第一课 | 2026-09-16 08:30 思想道德与法治 I402 |

## 快速开始

```bash
# 0. 依赖：Python 3.9+，标准库即可（无需 pip install）

# 1. 识别（需要视觉模型）
export FINCH_AI_API_KEY=sk-...
export FINCH_AI_MODEL=<一个支持视觉的模型>
python scripts/parse.py --image kebiao.png --out courses.json

# 2. 只校验，先看统计对不对
python scripts/to_ics.py courses.json --check

# 3. 生成
python scripts/to_ics.py courses.json -o courses.ics
```

没有 API Key 也可以先跑通第 3 步：`examples/26软件5.json` 是一份已经校对过的真实数据。

## 目录结构

```
campus-timetable-skill/
├── SKILL.md                     技能入口：何时触发、三步工作流、三条铁律
├── README.md                    这份文件（给人看的）
├── LICENSE                      MIT
├── references/
│   ├── parse-prompt.md          第 1 步的完整提示词
│   ├── schema.md                courses.json 字段定义
│   └── ics-rules.md             生成 ICS 的硬规则与踩坑记录
├── scripts/
│   ├── parse.py                 图 → JSON（调视觉模型）
│   ├── to_ics.py                JSON → ICS（纯确定性）
│   └── demo_offline.py          离线演示：不调模型，用内置样例跑通管道
├── tests/
│   ├── test_to_ics.py           10 条：日历生成的正确性
│   └── test_parse.py            13 条：JSON 提取与结构校验
└── examples/
    ├── 26软件5.json             真实课表，已人工校对
    └── 26软件5.ics              由上面的 JSON 生成
```

## 没有 API Key 也能跑

```bash
python scripts/demo_offline.py --out demo.json   # 不调模型，用内置样例
python scripts/to_ics.py demo.json -o demo.ics   # 接着生成日历
```

它会打印横幅说明"未调用任何模型"，并在输出的 JSON 里写上
`meta.offline_demo = true`，避免这份文件被当成模型输出交付出去。

**它证明的是管道通，不是识别准。** 真实识别仍需要 `parse.py` + 一个视觉模型。

## 自测

```bash
python -m unittest discover -s tests -v
```

**23 条断言全部通过**，都基于这份真实课表的**正确答案**，不是占位符。

`tests/test_to_ics.py`（10 条，日历生成）：

| 测试 | 断言 |
| --- | --- |
| `test_week1_monday` | 第 1 周 = 2026-08-31（周一），且第 3 周周三 = 09-16 |
| `test_event_and_occurrence_counts` | 31 条 VEVENT、150 次上课 |
| `test_no_conflicts` | 任意两个事件不重叠 |
| `test_single_week_is_compressed` | 单周课只有一条 `INTERVAL=2;COUNT=9` |
| `test_first_class` | 开学第一课 = 09-16 08:30 思想道德与法治 I402 |
| `test_holiday_shift` | 10/10 有程序设计、10/9 没有 |
| `test_odd_week_course` | 09-16 有、09-23 无、09-30 有 |
| `test_line_folding` | 最长行 ≤ 75 octets、无空行、CRLF |
| `test_required_properties` | UID / DTSTAMP / DTSTART / DTEND / VALARM 齐全 |
| `test_bad_start_date_rejected` | 基准日不是周一时报错退出 |

`tests/test_parse.py`（13 条，JSON 提取与校验）：

| 覆盖 | 断言 |
| --- | --- |
| 模型输出清洗 | 纯 JSON / ```json 围栏 / 前后夹客套话都能取出 |
| 坏输出 | 没有 JSON、JSON 语法错误 → 报错退出，不会静默写空文件 |
| 结构校验 | 缺 `assumptions`、日期格式错、`courses` 为空、缺 `name`、缺 `sessions` → 全部报错退出 |
| 合法 null | `teachers` / `code` / `room` 为 null 时正常通过 |

**没有覆盖的：模型本身的识别效果。** 那一步必须真调一次模型才算验证，测试替不了。


## 已知限制

1. **需要视觉模型**。模型没有视觉能力时会直接说"看不到图片"，这不是提示词问题。
2. **学期起始日不在截图里**。必须外部提供（校历第 1 周周一），脚本会校验它是不是星期一。
3. **补课日不会自动来**。截图是"周模板"，像"9/20 补 10/5 的课"这种只能靠校历补进 `day_shifts` 或在 assumptions 里声明。
4. **识别准确率不是 100%**。实测条目级 18/19（94.7%），错的那条是"教务系统把块挪了位置、模型信了位置没信文字"。所以第 2 步校验不能省。

## 踩过的坑（全在 `references/ics-rules.md`）

- 让模型直接写 ICS：43 行输出、2/20 条事件、HTML 注释、`COUNT=13` 而实际 11 周
- 断周压成一条 RRULE：多排 5 次、漏排 3 次，还会跟别的课撞车
- 学期基准日错一周：整学期晚 7 天
- 单周展开成 9 条单独事件：能用，但用户看到 9 个重复条目（本版已改为 `INTERVAL=2` 压成 1 条）
