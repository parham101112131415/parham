# 🔥 Parham — Hermes-style Telegram AI Agent

بات تلگرامی ایجنت‌محور با **ساختار Hermes** و **تم Parham** (قرمز-مشکی متحرک + حباب)، مخصوص اجرا روی **Railway**. هیچ دیتایی رو گوشی نمی‌مونه — همه‌چی فقط تو ولوم Railway.

## معماری

```
تلگرام → bot/handlers → memory (SQLite تو /data) → ai/bridge
→ opencode serve داخلی (مدل‌های رایگان Zen مثل muse-spark)
→ جواب تیکه‌تیکه ۲۰۰ کاراکتری + دکمه‌های 👍👎🔄💬
```

* مغز: `opencode serve` داخلی + سشن جدا `tg-<user_id>` برای هر کاربر (مثل Hermes gateway)
* حالت fallback: `AI_BACKEND=openai` با کلید OpenAI
* ورکرها (از jobs-manifest هرمس): دلار ساعتی، دلار نیمه‌شب، مموری‌بکاپ، pairing-watch
* داشبورد Parham Panel روی `$PORT` (دامنه خود Railway): اور‌ویو، سشن‌ها، یوزرها، مموری، بکاپ/ریستور، لاگ، چت

## دیپلوی روی Railway (راحت)

1. ریپو رو به Railway وصل کن (Deploy from GitHub → `parham101112131415/parham`)
2. یه **Volume** اضافه کن و به `/data` مونت کن
3. این Variables رو بذار:

| Variable | مقدار |
|---|---|
| `BOT_TOKEN` | توکن بات تلگرام |
| `OWNER_ID` | آیدی عددی تلگرام خودت |
| `AI_BACKEND` | `bridge` |
| `OPENCODE_AUTH_JSON` | محتوای فایل `~/.local/share/opencode/auth.json` گوشیت (تک‌خطی) — برای مدل‌های رایگان |
| `DASHBOARD_USER` / `DASHBOARD_PASS` | یوزر/پسورد داشبورد |
| `TZ` | `Asia/Tehran` |
| `PORT` | خود Railway می‌ذاره |

4. دو بکاپ هرمس (`migrate-full.tar.xz` + `hermes-memory-*.tgz`) رو یا تو پوشه `seed/` بذار قبل از دیپلوی، یا بعدش از داشبورد (Backup → restore) یا تلگرام (`/restore` در reply به فایل) آپلود کن. اولی بیس می‌شه، دومی روش می‌خوابه (جدیده برنده‌ست).
5. دیپلوی کن. داشبورد روی دامنه‌ای که Railway میده بالا میاد (`xxxx.up.railway.app`).

## اجرای لوکال (Termux)

```bash
pip install -r requirements.txt
cp .env.example .env   # پرش کن
opencode serve --hostname 127.0.0.1 --port 4096 &
python -m bot.main
```

## دستورات بات

/start · /help · /settings · /clear · /memory · /forget · /mode · /reconfig · /lang · /backup (مالک) · /restore (مالک، در reply به فایل)

ویس → Whisper، عکس → تحلیل (نیاز به `OPENAI_API_KEY` داره، وگرنه متنی جواب میده).
