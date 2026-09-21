# 🔥 Parham — REAL Hermes Agent on Railway

نه کپی، نه بازنویسی — خودِ `hermes-agent` اصلی (پین‌شده به نسخه تست‌شده) که مستقیم روی **opencode** (خانواده muse-spark، یعنی من) جواب می‌ده. بدون کلید جدا، بدون مدل دلخواه.

## چی ران می‌شه

| سرویس | دستور | توضیح |
|---|---|---|
| تلگرام | `hermes gateway run` | بات واقعی Hermes (منوی دستورات خودکار Hermes) |
| داشبورد | `hermes dashboard` روی `$PORT` | داشبورد اصلی + تم Parham (قرمز-مشکی متحرک + حباب) |
| مغز | `opencode-free/muse-spark-1.2-contributor-free` | keyless — هیچ کلیدی لازم نیست |

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
