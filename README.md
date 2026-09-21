# 🔥 Parham — Hermes-style Telegram AI Agent + REAL Hermes dashboard

بات تلگرامی ایجنت‌محور با **ساختار Hermes** و **تم Parham** (قرمز-مشکی متحرک + حباب)، مخصوص اجرا روی **Railway**. هیچ دیتایی رو گوشی نمی‌مونه — همه‌چی فقط تو ولوم Railway.

## معماری

```
تلگرام → bot/handlers → memory (SQLite تو /data) → ai/bridge
→ opencode serve داخلی (مدل‌های رایگان Zen مثل muse-spark)
→ جواب تیکه‌تیکه ۲۰۰ کاراکتری + دکمه‌های 👍👎🔄💬

$PORT → داشبورد اصلی Hermes (hermes dashboard واقعی، نه کپی)
        + تم Parham (قرمز-مشکی متحرک + حباب) + تایتل Parham Panel
```

* مغز تلگرام: `opencode serve` داخلی + سشن جدا `tg-<user_id>` برای هر کاربر (مثل Hermes gateway)
* داشبورد: **خود `hermes dashboard`** (پین‌شده به SHA تست‌شده) — تب‌های Sessions/Profiles/Cron/Skills/MCP/Tools/Chat واقعی. تنها تفاوت با Hermes خام: تم `parham` (از اسلات رسمی `dashboard-themes/*.yaml`) و تایتل.
* ورکرها (از jobs-manifest هرمس): دلار ساعتی، دلار نیمه‌شب، مموری‌بکاپ، pairing-watch
* آنبوردینگ AI-driven: اسم، اسم بات (انتخاب کاربر)، شهر، علایق، شخصیت — بدون مرحله خشک

## دیپلوی روی Railway (راحت)

1. ریپو رو به Railway وصل کن (Deploy from GitHub → `parham101112131415/parham`)
2. یه **Volume** اضافه کن و به `/data` مونت کن
3. این Variables رو بذار:

| Variable | مقدار |
|---|---|
| `BOT_TOKEN` | توکن بات تلگرام |
| `OWNER_ID` | آیدی عددی تلگرام خودت (`8055210419`) |
| `AI_BACKEND` | `bridge` |
| `OPENCODE_MODEL` | `opencode/muse-spark-1.3` (یا هر مدل رایگان Zen) |
| `OPENCODE_AUTH_JSON` | محتوای تک‌خطی `~/.local/share/opencode/auth.json` گوشیت |
| `DASHBOARD_USER` / `DASHBOARD_PASS` | یوزر/پسورد داشبورد Hermes |
| `DATA_DIR` | `/data` |
| `TZ` | `Asia/Tehran` |

`PORT` رو خود Railway می‌ذاره.

4. دو بکاپ هرمس (`migrate-full.tar.xz` + `hermes-memory-*.tgz`) رو یا تو پوشه `seed/` بذار قبل از دیپلوی، یا بعدش از تلگرام (`/restore` در reply به فایل) آپلود کن. اولی بیس می‌شه، دومی روش می‌خوابه (جدیده برنده‌ست).
5. دیپلوی کن. داشبورد اصلی Hermes با تم Parham میاد روی دامنه‌ای که Railway میده (`xxxx.up.railway.app`) — لاگین با یوزر/پسورد خودت.

## اجرای لوکال (Termux)

```bash
pip install -r requirements.txt
cp .env.example .env   # پرش کن
opencode serve --hostname 127.0.0.1 --port 4096 &
python -m bot.main
```

## دستورات بات (منوی خودکار کنار چت، مثل Hermes)

start · help · settings · clear · memory · forget · mode · reconfig · lang · backup · restore · status (سه‌تای آخر فقط مالک)

ویس → Whisper، عکس → تحلیل (نیاز به `OPENAI_API_KEY` داره، وگرنه متنی جواب میده).
