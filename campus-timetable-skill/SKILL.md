---
name: campus-timetable
description: 把中国高校教务系统导出的课表截图（合并单元格、单双周、连堂、12 节晚课）解析成结构化 JSON，并生成可直接导入手机系统日历的 .ics 文件。当用户上传课表图片，或说"把课表导入日历""整理我的课表""生成日历文件"时使用。
metadata:
  version: "0.1.0"
---

# 校园课表 → 手机日历

## 这个技能做什么

**输入**：一张课表截图（任意教务系统：强智、正方、URP、青果、金智，或同学转发的图片）。
**输出**：一份结构化 `courses.json` + 一份可导入 iOS / Android 系统日历的 `courses.ics`。

不做什么：不登录教务系统、不爬取、不保存用户图片超过单次调用、不接触成绩与评教数据。

## 何时触发

- 用户上传或粘贴了一张课程表图片
- 用户问"能不能把课表导进日历 / 手机日历 / 生成 ics"
- 用户抱怨"单双周记不住""调课总忘""课表截图太乱"

不触发：只有课程名称文字没有图片；只是问某门课的时间。

## 工作流：三步，每一步都不能跳

### 第 1 步 识别（图 → JSON）

用 `references/parse-prompt.md` 里的提示词，交给**支持视觉**的多模态模型。
命令行方式：

```bash
export FINCH_AI_API_KEY=...          # 必填
export FINCH_AI_BASE_URL=...         # 可选，OpenAI 兼容端点
export FINCH_AI_MODEL=...            # 必填，必须是视觉模型
python scripts/parse.py --image kebiao.png --out courses.json
```

模型返回的 JSON 可能带代码块围栏或客套话，`parse.py` 会剥掉并做结构校验。

### 第 2 步 校验（**必做，不是可选项**）

拿到 JSON 后立刻跑这三条，任何一条不过就不要继续：

1. **数量**：截图里有几门课，`courses` 里是不是同样数量
2. **节次**：随机挑 3 条 session，对比原图上单元格里的文字"第X节-第Y节"
3. **单双周**：找一门单周、一门双周课，看 `weeks.type` 是不是 `odd` / `even`

### 第 3 步 生成（JSON → ICS）

```bash
python scripts/to_ics.py courses.json -o courses.ics          # 生成
python scripts/to_ics.py courses.json --check                 # 只校验不写文件
```

**永远不要让语言模型手写 ICS**，原因见 `references/ics-rules.md`。

## 三条铁律

1. **节次以单元格里的【文字】为准，不信格子的【视觉位置】。**
   教务系统会把"同一时段、不同周次"的课上下错开显示。文字写"第1节-第2节"、块画在第 3-4 行，真实时间是第 1-2 节。

2. **断周不能压成一条 RRULE。**
   `4-5周,7-12周,17-19周` 是 11 周，不是 13 周。一条 RRULE 只能表达等差的周，必须按连续段拆成多条 VEVENT。

3. **识别不到就写 null，不写"待定"。**
   "待定"是虚构值，会污染数据且无法与"识别失败"区分。同时给每个 session 一个 `confidence`（0-1）。

## 文件索引

| 文件 | 作用 |
| --- | --- |
| `references/parse-prompt.md` | 第 1 步用的完整提示词（含单双周、节次换算规则） |
| `references/schema.md` | `courses.json` 的字段定义与取值范围 |
| `references/ics-rules.md` | 生成 ICS 的硬规则、踩过的坑、验证方法 |
| `scripts/parse.py` | 调视觉模型，图 → JSON |
| `scripts/to_ics.py` | JSON → ICS（确定性代码，不使用模型） |
| `examples/26软件5.json` / `.ics` | 真实跑通的一整套样例（11 门课 / 19 条 session / 150 次上课） |

## 已知限制

- **需要视觉模型**。没有视觉能力的模型会直接说"看不到图片"，这不是提示词的问题。
- **学期起始日不在截图里**。必须由用户提供，或取校历第 1 周的周一；缺失时按最近一个周一兜底并在 `meta.assumptions` 里写明。
- **校历调休不会自动处理**。截图只是"周模板"，国庆/期中调课要靠 `meta.day_shifts` 手工补（格式见 `references/schema.md`）。
- **单次输出长度有限**。课表很大时，模型的 JSON 可能被截断，所以识别和生成必须分成两次调用。

## 变更记录

- 0.1.0 首个版本：截图 → JSON → ICS，覆盖单双周、断周、连堂、12 节晚课。
