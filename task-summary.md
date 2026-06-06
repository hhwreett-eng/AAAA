---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 935f5b459d1914fa5913f4495f92a59e_b6ccf99f60da11f1832e5254006c9bbf
    ReservedCode1: wr11VTaXbmNu0vS7UMa4cFoCHhTCBg5+GmhwwdSiSbn27v0IUJ69RwfbKIF7QUY3c4b4XwQxY8zClHQGwD4nTcffRxScA78XdHDB1zTooJ4iaD2B6/riwtzmuZyJxDfaNLxcRReB+LiujADiDxx6txGtH5ExFVae85rtP3uCwFeNQCGoGZ9l7YYzIeU=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 935f5b459d1914fa5913f4495f92a59e_b6ccf99f60da11f1832e5254006c9bbf
    ReservedCode2: wr11VTaXbmNu0vS7UMa4cFoCHhTCBg5+GmhwwdSiSbn27v0IUJ69RwfbKIF7QUY3c4b4XwQxY8zClHQGwD4nTcffRxScA78XdHDB1zTooJ4iaD2B6/riwtzmuZyJxDfaNLxcRReB+LiujADiDxx6txGtH5ExFVae85rtP3uCwFeNQCGoGZ9l7YYzIeU=
---





# 科技股博主监控 - 定时任务配置

## 任务内容
运行 run.ps1 抓取美国科技股博主公开内容，生成 Word (.docx) 日报

## 定时规则
每天 5 次：08:00、11:00、14:00、17:00、20:00（UTC+8，每3小时）

| 时间 | 任务名称 |
|------|---------|
| 08:00 | 每日科技股博主监控 |
| 11:00 | 每日科技股博主监控（11点） |
| 14:00 | 每日科技股博主监控（14点） |
| 17:00 | 每日科技股博主监控（17点） |
| 20:00 | 每日科技股博主监控（20点） |

## 监控博主列表

| 博主 | 来源类型 | 条数 |
|------|---------|------|
| SemiAnalysis / Dylan Patel | feed ×3 | RSS/YouTube/Podcast |
| Beth Kindig / I/O Fund | feed ×4 | RSS/YouTube/Page |
| Doug O'Laughlin / Fabricated Knowledge | feed ×1 | RSS |
| muji / HHHYPERGROWTH | feed ×1 + page ×1 | RSS/Page |
| Ben Thompson / Stratechery | feed ×1 + page ×1 | RSS/Page |
| Jamin Ball / Clouded Judgement | feed ×1 | RSS |
| App Economy Insights | feed ×1 | RSS |
| Software Stack Investing | feed ×1 | RSS |
| BG2 / Brad Gerstner + Bill Gurley | feed ×2 + page ×1 | RSS/YouTube/Page |
| The Six Five / Patrick Moorhead + Daniel Newman | feed ×3 + page ×1 | RSS/YouTube/Page |
| Chip Stock Investor | feed ×3 | RSS/YouTube/Podcast |
| Ticker Symbol: YOU | feed ×2 | YouTube/Podcast |
| Jose Najarro Stocks | feed ×1 | YouTube |
| Serenity / aleabitoreddit | page ×1 | GitHub Archive |
| Elon Musk / @elonmusk | x_api + fallback | X API → Nitter RSS 自动切换 |

## 报告路径
`C:\Users\0\Documents\AAA\reports\科技博主-YYYY-MM-DD.docx`

## 备注
- cron 表达式不支持星期过滤，周末也会触发，去重机制下无新内容不重复报
- Serenity 通过 GitHub tweet archive 间接监控，非实时（延迟约数小时），建议获取 X API Bearer Token 后升级为 x_api 类型
- Elon Musk 主用 X API，遇 429/402/502/503 限流时自动回退到 Nitter RSS
- 报告格式已改为 .docx，历史 .md 仍可被「昨日回顾」读取
*（内容由AI生成，仅供参考）*
*（内容由AI生成，仅供参考）*
*（内容由AI生成，仅供参考）*
