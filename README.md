# 美国科技股博主公开内容监控器

这个小项目每天从公开来源抓取内容，去重后生成 Markdown 日报。它适合监控英伟达、AI 基础设施、CSP 云厂商、半导体、SaaS/云软件等方向的博主和研究员。

它只使用公开 RSS/Atom、YouTube RSS、普通公开网页变更和可选官方 API。不绕登录、不抓付费正文、不规避平台反爬。

## 快速运行

```powershell
.\run.ps1
```

如果 Windows 提示禁止运行脚本，用：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run.ps1
```

日报会写到：

```text
reports\daily-YYYY-MM-DD.md
```

第一次运行如果不想把当前历史内容全算作“新内容”，先初始化去重状态：

```powershell
.\run.ps1 -InitSeen
```

或：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 -InitSeen
```

之后每天运行普通命令即可。

## 安装每天定时任务

默认每天 08:30 运行：

```powershell
.\install_daily_task.ps1
```

如果执行策略拦截：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install_daily_task.ps1
```

改时间：

```powershell
.\install_daily_task.ps1 -Time "21:00"
```

日志会写到：

```text
logs\daily-task.log
```

## 生成最近 N 天汇总

日常日报会去重；如果你想重新汇总最近 5 天、7 天或 30 天的公开内容，用：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run_recent.ps1 -Days 5
```

输出会写到：

```text
reports\recent-5d-YYYY-MM-DD.md
```

这个汇总会列出本次检查到的公开接口、主题信号、关键词命中和逐条内容。

## 配置监控对象

编辑 `config.toml`。每个博主一个 `[[creators]]`，每个来源一个 `[[creators.sources]]`。

RSS/Atom/YouTube RSS：

```toml
[[creators]]
name = "Example Creator"
tags = ["nvidia", "cloud"]

[[creators.sources]]
name = "Example Newsletter"
type = "feed"
url = "https://example.com/feed"
tags = ["newsletter"]
```

普通公开网页变更：

```toml
[[creators.sources]]
name = "Example Media Page"
type = "page"
url = "https://example.com/media"
tags = ["website"]
```

X/Twitter 官方 API：

```toml
[[creators.sources]]
name = "Example X Account"
type = "x_api"
handle = "example"
bearer_token_env = "X_BEARER_TOKEN"
max_results = 20
```

然后在系统环境变量里设置 `X_BEARER_TOKEN`。

## 邮件推送

`config.toml` 里把 `[delivery.email] enabled` 改成 `true`，填 SMTP 服务器、发件人、收件人，并设置环境变量：

```powershell
$env:SMTP_USERNAME = "your-user"
$env:SMTP_PASSWORD = "your-password"
```

建议先手动运行一次确认能生成日报，再打开邮件推送。

## 目前内置名单

- SemiAnalysis / Dylan Patel
- Beth Kindig / I/O Fund
- Doug O'Laughlin / Fabricated Knowledge
- muji / HHHYPERGROWTH
- Ben Thompson / Stratechery
- Jamin Ball / Clouded Judgement
- App Economy Insights
- Software Stack Investing
- BG2 / Brad Gerstner + Bill Gurley
- The Six Five / Patrick Moorhead + Daniel Newman
- Chip Stock Investor
- Ticker Symbol: YOU
- Jose Najarro Stocks

有些平台没有稳定 RSS，配置里用 `page` 监控公开页面是否变更；如果你能拿到该平台官方 API 或 RSS 地址，改成 `feed` 或 `x_api` 会更准。

已验证补充的公开接口记录在 `SOURCE_DISCOVERY.md`。
