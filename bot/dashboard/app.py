"""Parham dashboard: Hermes-structure admin panel with the Parham red-black theme.

Routes: / (overview) /sessions /users /memory /backup /restore /logs /chat /health
Auth: basic (DASHBOARD_USER/PASS). Served on $PORT (Railway public domain).
"""
from __future__ import annotations

import base64
import html
import logging
import os

from aiohttp import web
from sqlalchemy import func, select

from bot.config import CONFIG
from bot.db.models import Fact, Feedback, Message, User, session_factory
from bot.handlers.messages import answer_for
from bot.services.backup import create_backup
from bot.services.memory import get_facts

log = logging.getLogger("parham.dashboard")

THEME_CSS = """
:root{--red:#ef4444;--black:#0a0a0b;--panel:#141416;--text:#f5f5f5}
*{box-sizing:border-box}body{margin:0;font-family:Vazirmatn,Tahoma,sans-serif;color:var(--text);
background:linear-gradient(120deg,#0a0a0b,#1a0505,#0a0a0b,#2a0a0a);background-size:300% 300%;animation:bgmove 12s ease infinite}
@keyframes bgmove{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.bubbles{position:fixed;inset:0;overflow:hidden;pointer-events:none;z-index:0}
.bubbles span{position:absolute;bottom:-40px;border-radius:50%;background:rgba(239,68,68,.25);animation:rise linear infinite}
@keyframes rise{to{transform:translateY(-110vh)}}
header{position:relative;z-index:1;padding:18px 24px;font-size:22px;font-weight:800;color:var(--red);
text-shadow:0 0 18px rgba(239,68,68,.8);border-bottom:1px solid rgba(239,68,68,.35)}
nav{position:relative;z-index:1;padding:10px 24px;display:flex;gap:10px;flex-wrap:wrap}
nav a{color:var(--text);text-decoration:none;background:var(--panel);border:1px solid rgba(239,68,68,.4);
padding:8px 14px;border-radius:10px}nav a:hover{border-color:var(--red);box-shadow:0 0 12px rgba(239,68,68,.5)}
main{position:relative;z-index:1;padding:16px 24px}
.card{background:rgba(20,20,22,.92);border:1px solid rgba(239,68,68,.35);border-radius:14px;padding:16px;margin:12px 0;
box-shadow:0 0 24px rgba(239,68,68,.12)}
.card h3{margin:0 0 8px;color:var(--red)}
table{width:100%;border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #2a2a2d;text-align:right;font-size:14px}
.badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:12px;border:1px solid var(--red);color:var(--red)}
.badge.ok{border-color:#22c55e;color:#22c55e}
input,button,textarea{background:#0f0f11;color:var(--text);border:1px solid rgba(239,68,68,.4);border-radius:10px;padding:10px;margin:4px 0}
button{cursor:pointer;background:var(--red);color:#fff;font-weight:700}button:hover{box-shadow:0 0 14px rgba(239,68,68,.7)}
"""

BUBBLES = """<div class="bubbles">""" + "".join(
    f'<span style="left:{(i * 37) % 100}%;width:{6 + (i % 5) * 4}px;height:{6 + (i % 5) * 4}px;animation-duration:{7 + (i % 6)}s"></span>'
    for i in range(18)
) + "</div>"


def page(title: str, body: str) -> str:
    """Wrap body HTML in the Parham themed shell."""
    nav = (
        "<nav><a href='/'>اور‌ویو</a><a href='/sessions'>سشن‌ها</a><a href='/users'>یوزرها</a>"
        "<a href='/memory'>مموری</a><a href='/backup'>بکاپ</a><a href='/logs'>لاگ</a>"
        "<a href='/chat'>چت</a><a href='/health'>health</a></nav>"
    )
    return (
        f"<!DOCTYPE html><html dir='rtl' lang='fa'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>Parham Panel — {html.escape(title)}</title><style>{THEME_CSS}</style></head>"
        f"<body>{BUBBLES}<header>🔥 Parham Panel</header>{nav}<main>{body}</main></body></html>"
    )


def _authed(request: web.Request) -> bool:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        return False
    try:
        user, _, password = base64.b64decode(auth[6:]).decode().partition(":")
    except Exception:  # noqa: BLE001
        return False
    return user == CONFIG.dashboard_user and password == CONFIG.dashboard_pass


@web.middleware
async def auth_middleware(request: web.Request, handler) -> web.Response:
    """Require basic auth on every route except /health."""
    if request.path == "/health":
        return await handler(request)
    if not _authed(request):
        return web.Response(status=401, headers={"WWW-Authenticate": 'Basic realm="parham"'})
    return await handler(request)


async def overview(request: web.Request) -> web.Response:
    """Overview: counts + worker status."""
    factory = session_factory()
    async with factory() as session:
        users = await session.scalar(select(func.count(User.id))) or 0
        msgs = await session.scalar(select(func.count(Message.id))) or 0
        facts = await session.scalar(select(func.count(Fact.id))) or 0
        likes = await session.scalar(select(func.count(Feedback.id)).where(Feedback.kind == "like")) or 0
        dislikes = await session.scalar(select(func.count(Feedback.id)).where(Feedback.kind == "dislike")) or 0
    workers = [
        ("دلار ساعتی", "scheduled"),
        ("دلار نیمه‌شب", "scheduled"),
        ("مموری‌بکاپ", "scheduled"),
        ("pairing-watch", "scheduled"),
    ]
    cards = "".join(
        f"<div class='card'><h3>{n}</h3><span class='badge ok'>{s}</span></div>" for n, s in workers
    )
    body = (
        f"<div class='card'><h3>آمار</h3>یوزرها: {users} | پیام‌ها: {msgs} | "
        f"فکت‌ها: {facts} | 👍 {likes} | 👎 {dislikes}</div>"
        f"<h3>ورکرها</h3>{cards}"
    )
    return web.Response(text=page("اور‌ویو", body), content_type="text/html")


async def sessions_view(request: web.Request) -> web.Response:
    """Sessions: recent users (= opencode tg-<id> sessions)."""
    factory = session_factory()
    async with factory() as session:
        rows = (await session.scalars(select(User).order_by(User.id.desc()).limit(50))).all()
    trs = "".join(
        f"<tr><td>{u.telegram_id}</td><td>{html.escape(u.real_name or '—')}</td>"
        f"<td>{html.escape(u.city or '—')}</td><td>{html.escape(u.mode)}</td>"
        f"<td><span class='badge ok'>tg-{u.telegram_id}</span></td></tr>"
        for u in rows
    )
    return web.Response(
        text=page("سشن‌ها", f"<div class='card'><table><tr><th>آیدی</th><th>اسم</th><th>شهر</th><th>مود</th><th>سشن</th></tr>{trs}</table></div>"),
        content_type="text/html",
    )


async def users_view(request: web.Request) -> web.Response:
    """Users: profiles."""
    factory = session_factory()
    async with factory() as session:
        rows = (await session.scalars(select(User).order_by(User.id.desc()).limit(50))).all()
    trs = "".join(
        f"<tr><td>{u.telegram_id}</td><td>{html.escape(u.username or '')}</td>"
        f"<td>{html.escape(u.personality[:60] or '—')}</td><td>{html.escape(u.interests[:60] or '—')}</td></tr>"
        for u in rows
    )
    return web.Response(
        text=page("یوزرها", f"<div class='card'><table><tr><th>آیدی</th><th>یوزرنیم</th><th>شخصیت</th><th>علایق</th></tr>{trs}</table></div>"),
        content_type="text/html",
    )


async def memory_view(request: web.Request) -> web.Response:
    """Memory: facts per user."""
    factory = session_factory()
    async with factory() as session:
        rows = (await session.scalars(select(Fact).order_by(Fact.id.desc()).limit(100))).all()
    trs = "".join(
        f"<tr><td>{f.telegram_id}</td><td>{html.escape(f.key)}</td><td>{html.escape(f.value[:120])}</td></tr>"
        for f in rows
    )
    return web.Response(
        text=page("مموری", f"<div class='card'><table><tr><th>یوزر</th><th>کلید</th><th>مقدار</th></tr>{trs}</table></div>"),
        content_type="text/html",
    )


async def backup_view(request: web.Request) -> web.Response:
    """Backup: download full backup / upload restore file."""
    if request.method == "POST":
        data = await request.post()
        upload = data.get("file")
        if upload is None:
            return web.Response(text=page("بکاپ", "<div class='card'>فایلی نفرستادی.</div>"), content_type="text/html")
        tmp = os.path.join(CONFIG.data_dir, "_restore_upload.tar")
        with open(tmp, "wb") as fh:
            fh.write(upload.file.read())
        import tarfile

        try:
            with tarfile.open(tmp, "r:*") as tar:
                tar.extractall(CONFIG.data_dir, filter="data")
            msg = "ریستور شد ✅ کانتینر رو ری‌استارت کن."
        except Exception:  # noqa: BLE001
            log.exception("dashboard restore failed")
            msg = "ریستور fail شد."
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
        return web.Response(text=page("بکاپ", f"<div class='card'>{msg}</div>"), content_type="text/html")

    body = (
        "<div class='card'><h3>دانلود بکاپ کامل</h3>"
        "<a href='/backup/download'><button>دانلود</button></a></div>"
        "<div class='card'><h3>ریستور از فایل</h3>"
        "<form method='post' enctype='multipart/form-data'>"
        "<input type='file' name='file'><br><button type='submit'>ریستور</button></form></div>"
    )
    return web.Response(text=page("بکاپ", body), content_type="text/html")


async def backup_download(request: web.Request) -> web.Response:
    """Download a fresh full backup."""
    path = await asyncio_get_backup()
    return web.FileResponse(path)


async def asyncio_get_backup() -> str:
    """Create backup without blocking the loop."""
    import asyncio

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, create_backup, CONFIG.data_dir)


async def logs_view(request: web.Request) -> web.Response:
    """Logs: last lines of bot log if present."""
    log_path = os.path.join(CONFIG.data_dir, "bot.log")
    text = ""
    if os.path.exists(log_path):
        with open(log_path, errors="ignore") as fh:
            lines = fh.readlines()[-200:]
        text = html.escape("".join(lines))
    return web.Response(
        text=page("لاگ", f"<div class='card'><pre dir='ltr' style='text-align:left'>{text or 'لاگی نیست'}</pre></div>"),
        content_type="text/html",
    )


async def chat_view(request: web.Request) -> web.Response:
    """Chat: talk to the agent as owner directly from the dashboard."""
    if request.method == "POST":
        data = await request.post()
        text = (data.get("text") or "").strip()
        if not text:
            return web.Response(text=page("چت", "<div class='card'>چیزی ننوشتی.</div>"), content_type="text/html")
        reply = await answer_for(CONFIG.owner_id, text)
        return web.Response(
            text=page("چت", f"<div class='card'><h3>تو</h3>{html.escape(text)}</div><div class='card'><h3>پارهم</h3>{html.escape(reply)}</div><a href='/chat'>برگرد</a>"),
            content_type="text/html",
        )
    body = (
        "<div class='card'><h3>چت مستقیم</h3><form method='post'>"
        "<textarea name='text' rows='4' style='width:100%'></textarea><br>"
        "<button type='submit'>بفرست</button></form></div>"
    )
    return web.Response(text=page("چت", body), content_type="text/html")


async def health(request: web.Request) -> web.Response:
    """Healthcheck for Railway (no auth)."""
    return web.Response(text="ok")


def build_app() -> web.Application:
    """Build the dashboard application."""
    app = web.Application(middlewares=[auth_middleware])
    app.router.add_get("/", overview)
    app.router.add_get("/sessions", sessions_view)
    app.router.add_get("/users", users_view)
    app.router.add_get("/memory", memory_view)
    app.router.add_get("/backup", backup_view)
    app.router.add_post("/backup", backup_view)
    app.router.add_get("/backup/download", backup_download)
    app.router.add_get("/logs", logs_view)
    app.router.add_get("/chat", chat_view)
    app.router.add_post("/chat", chat_view)
    app.router.add_get("/health", health)
    return app
