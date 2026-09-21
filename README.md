# Parham — REAL Hermes Agent on Railway

نه کپی، نه بازنویسی — خودِ `hermes-agent` اصلی که موتورش **opencode واقعی**ـه (muse-spark ۱.۳، یعنی من). Hermes صددرصد دست‌نخورده؛ فقط provider اون یه درایور نامرئی محلیه که به opencode وصل می‌شه.

## چی ران می‌شه

| سرویس | دستور | توضیح |
|---|---|---|
| تلگرام | `hermes gateway run` | بات واقعی Hermes (منوی دستورات خودکار Hermes) |
| داشبورد | `hermes dashboard` روی `$PORT` | داشبورد اصلی، بدون هیچ تغییری |
| مغز | opencode واقعی (`OPENCODE_MODEL`) | درایور نامرئی `proxy/` — Hermes دست‌نخورده |
| `OPENCODE_MODEL` | `opencode/muse-spark-1.3-contributor-free` | مدل داخل opencode |
| `OPENCODE_AUTH_JSON` | (اختیاری) محتوای تک‌خطی `auth.json` | احراز opencode |

حافظه، اسکیل‌ها، کرون‌ها (دلار ساعتی/نیمه‌شب، مموری‌بکاپ، pairing) از دو بکاپ خودت سید می‌شن و بعدش فقط روی ولوم Railway ذخیره می‌شن. هیچی روی گوشی نیست.

## دیپلوی

1. Deploy from GitHub → `parham101112131415/parham`
2. Volume به `/data`
3. Variables:

| Variable | مقدار |
|---|---|
| `TELEGRAM_BOT_TOKEN` | توکن باتت |
| `TELEGRAM_ALLOWED_USERS` | `8055210419` |
| `TELEGRAM_HOME_CHANNEL` | `8055210419` |
| `DASHBOARD_USER` | `admin` (یا دلخواه) |
| `DASHBOARD_PASS` | پسورد قوی |
| `DATA_DIR` | `/data` |
| `TZ` | `Asia/Tehran` |

`PORT` رو Railway می‌ذاره. داشبورد روی دامنه Railway با یوزر/پسورد خودت.
