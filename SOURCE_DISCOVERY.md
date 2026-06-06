# Source discovery

Validated public interfaces added to `config.toml`:

- SemiAnalysis Weekly Podcast: `https://anchor.fm/s/10fbee758/podcast/rss`
- I/O Fund RSS: `https://io-fund.com/rss.xml`
- I/O Fund YouTube: `https://www.youtube.com/feeds/videos.xml?channel_id=UC0OhiHAJHiLVg_wjP3A9O_A`
- BG2 Podcast RSS: `https://anchor.fm/s/f06c2370/podcast/rss`
- BG2 YouTube: `https://www.youtube.com/feeds/videos.xml?channel_id=UC-yRDvpR99LUc5l7i7jLzew`
- The Six Five Podcast RSS: `https://sixfive.libsyn.com/rss`
- Six Five YouTube: `https://www.youtube.com/feeds/videos.xml?channel_id=UC7-rtz96bYgd2m4AhKtZFQw`
- Moor Insights YouTube: `https://www.youtube.com/feeds/videos.xml?channel_id=UC8fY_kIR5AqTmafpAzOjQ2g`
- Chip Stock Investor Podcast: `https://anchor.fm/s/e2cacf78/podcast/rss`
- Chip Stock Investor YouTube: `https://www.youtube.com/feeds/videos.xml?channel_id=UC3aD-gfmHV_MhMmcwyIu1wA`
- Ticker Symbol: YOU Podcast: `https://rss.buzzsprout.com/1805490.rss`

Notes:

- X/Twitter, LinkedIn, Seeking Alpha, Substack Notes, and similar social feeds generally require official API access, login, or paid/private feeds. The monitor intentionally does not bypass those controls.
- Page-change sources are still useful for daily monitoring, but they do not provide reliable item-level publish dates, so `recent_digest.py` excludes them from dated multi-day reports.
