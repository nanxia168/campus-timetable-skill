# courses.json 结构定义

一次调用产出一个对象。字段缺失**必须**写 `null`，不得省略键，不得写"待定"。

## 顶层

```json
{
  "meta": { ... },
  "courses": [ ... ]
}
```

## meta

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `calendar_name` | string | 否 | 日历名，如 `2026秋 26软件5 课表` |
| `semester_start_date` | string `YYYY-MM-DD` | **是** | **第 1 周的星期一**。不是开学日，不是截图日期 |
| `semester_start_date_source` | `"user"` \| `"calendar"` \| `"assumed"` | 否 | `calendar` = 由校历推出；`assumed` = 兜底 |
| `school` / `term` | string \| null | 否 | 有就填，没有就 null |
| `assumptions` | string[] | **是** | 所有推断项，每条一句话。空数组表示没有任何推断 |
| `low_confidence_fields` | string[] | 否 | 如 `"courses[2].teachers"` |
| `day_shifts` | object[] | 否 | 校历调休例外，见下 |

### day_shifts（调休）

```json
{"code": "3573", "weekday": 5, "week": 6, "days": 1}
```

含义：课号 `3573` 的课，第 6 周星期五那一次，实际发生在**往后 1 天**（周六）。
`code` 也可以换成 `name`（课程名精确匹配）。匹配不上就跳过并告警。

## courses[]

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `name` | string | 完整课程名，**不含**教师姓名 |
| `code` | string \| null | 课程号，截图里课程名后面那串数字，如 `3591` |
| `teachers` | string[] \| null | 可能多人 |
| `credit` | number \| null | 学分，没有就 null，不要猜 |
| `category` | string \| null | `必修` / `选修` / `实验` / `体育` / `线上`；截图没标就 null |
| `sessions` | object[] | 一门课有几个上课时段就几条，**不要重复输出课程名** |

## sessions[]

| 字段 | 类型 | 取值 | 说明 |
| --- | --- | --- | --- |
| `weekday` | number | 1–7 | 周一 = 1，周日 = 7 |
| `periods` | number[] | 如 `[1,2]`、`[9,10,11,12]` | 连堂写在一起，不要拆 |
| `start_time` / `end_time` | string | `HH:MM` | 首节开始 / 末节结束 |
| `weeks` | object | 见下 | |
| `location` | object | `{raw, campus, building, room}` | 拆不出就全放 `raw`，其余 null |
| `note` | string \| null | | 备注；执行"抄录-核对"规则时放这里 |
| `confidence` | number | 0–1 | 靠推测得到的不得高于 0.6 |

## weeks

```json
{"type": "all" | "odd" | "even" | "ranges", "ranges": [[3, 19]], "explicit": [6]}
```

| type | 含义 | 例子 |
| --- | --- | --- |
| `all` | 每个教学周 | `1-16周` → `{"type":"all","ranges":[[1,16]]}` |
| `odd` | 范围内的单周 | `3-19周(单)` → `{"type":"odd","ranges":[[3,19]]}` |
| `even` | 范围内的双周 | `2-16周(双)` → `{"type":"even","ranges":[[2,16]]}` |
| `ranges` | 任意区间 + 零散周 | `3-5周,7-19周` → `{"ranges":[[3,5],[7,19]]}` |

注意：`ranges` 里不要写 `[3,3]` 这种单周区间，单周写进 `explicit`，两者混用会让下游难以核对。

## 最小完整示例

```json
{
  "meta": {
    "calendar_name": "2026秋 课表",
    "semester_start_date": "2026-08-31",
    "semester_start_date_source": "calendar",
    "assumptions": ["截图未标教师，teachers 置 null"],
    "low_confidence_fields": ["courses[0].sessions[0].location.campus"]
  },
  "courses": [
    {
      "name": "大学语文",
      "code": "2585",
      "teachers": ["马红莉"],
      "credit": null,
      "category": "必修",
      "sessions": [
        {
          "weekday": 3,
          "periods": [3, 4],
          "start_time": "10:05",
          "end_time": "11:25",
          "weeks": {"type": "ranges", "ranges": [[3, 5], [7, 19]], "explicit": []},
          "location": {"raw": "F211", "campus": null, "building": null, "room": "F211"},
          "note": null,
          "confidence": 0.9
        }
      ]
    }
  ]
}
```
