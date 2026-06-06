---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 935f5b459d1914fa5913f4495f92a59e_a7caddc260db11f19f62525400d9a7a1
    ReservedCode1: kV5Jj93BuvMyejW44WqWLCAqqgZW8erxNRAI8Q4yMOoPR2p/CFkT5Yi1wkrJQ2XwJ8ui76quS+LXj+uebKkvvo5Qh8qzAOh0umBq7ZJBK0SRr2ISVig3/wmEqZroCOYmtmSaZY6eJbt70VCGq/S1XRAWJVdCV85Ve6xoUGyHmMrH3EyNi1PfqFyU+M0=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 935f5b459d1914fa5913f4495f92a59e_a7caddc260db11f19f62525400d9a7a1
    ReservedCode2: kV5Jj93BuvMyejW44WqWLCAqqgZW8erxNRAI8Q4yMOoPR2p/CFkT5Yi1wkrJQ2XwJ8ui76quS+LXj+uebKkvvo5Qh8qzAOh0umBq7ZJBK0SRr2ISVig3/wmEqZroCOYmtmSaZY6eJbt70VCGq/S1XRAWJVdCV85Ve6xoUGyHmMrH3EyNi1PfqFyU+M0=
---

# Cloud 部署指南

## 一、推送到 GitHub（一次性）

```powershell
cd C:\Users\0\Documents\AAA
git init
git add .
git commit -m "Initial commit: tech stock monitor"
# 在 GitHub 创建仓库后：
git remote add origin https://github.com/你的用户名/仓库名.git
git push -u origin main
```

## 二、申请 Gmail 应用密码（一次性）

1. 登录你的 Gmail → 管理 Google 账号 → 安全性
2. 开启"两步验证"
3. 搜索"应用专用密码" → 生成一个，记住这串 16 位密码

## 三、设置 GitHub Secrets（一次性）

在仓库 Settings → Secrets and variables → Actions → New repository secret：

| Secret 名称 | 值 |
|-------------|-----|
| `SMTP_USERNAME` | 你的 Gmail 地址（如 `yourname@gmail.com`） |
| `SMTP_PASSWORD` | 上一步的 16 位应用专用密码 |

## 四、验证

推送代码后，GitHub Actions 会在每天 08:00/10:00/12:00/14:00/20:00 自动运行。

手动测试：GitHub 仓库 → Actions → 点击 "Tech Stock Daily Monitor" → "Run workflow"。

## 现有文件说明

| 文件 | 用途 |
|------|------|
| `monitor.py` | 主程序，纯 stdlib，无需 pip install |
| `config-cloud.toml` | 云端配置，已开启 Gmail SMTP 邮件发送 |
| `config.toml` | 本地配置（不影响云端） |
| `.github/workflows/monitor.yml` | GitHub Actions 定时任务定义 |
| `state/seen.json` | 去重状态（自动通过 git 持久化） |
| `reports/` | 日报输出目录 |
*（内容由AI生成，仅供参考）*
