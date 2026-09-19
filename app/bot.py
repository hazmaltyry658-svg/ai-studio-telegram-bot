import asyncio
import os
import time
from pathlib import Path

from telegram import Update, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from .config import OUTPUT_DIR, MAX_VIDEO_SECONDS, MAX_AUDIO_MINUTES
from .db import init_db, add_job, update_job, history
from .keyboards import main_menu, aspect_menu, duration_menu
from .providers import generate_video, generate_song, mux, compress_video

SESSIONS = {}
ACTIVE = set()

def session(uid):
    return SESSIONS.setdefault(uid, {"mode": None, "step": None, "data": {}})

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = session(update.effective_user.id)
    s.update({"mode": None, "step": None, "data": {}})
    await update.message.reply_text(
        "🎬 أهلاً بك في AI Studio\n\n"
        "أرسل لي وصفًا لصناعة فيديو، أو كلمات أغنية لصناعة أغنية كاملة.\n\n"
        "اختر من القائمة:",
        reply_markup=main_menu()
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "الأوامر:\n"
        "/start — القائمة الرئيسية\n"
        "/video — إنشاء فيديو\n"
        "/song — إنشاء أغنية\n"
        "/history — سجل أعمالك\n"
        "/cancel — إلغاء المهمة الحالية"
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    SESSIONS.pop(uid, None)
    ACTIVE.discard(uid)
    await update.message.reply_text("❌ تم إلغاء العملية.", reply_markup=main_menu())

async def history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = history(update.effective_user.id)
    if not rows:
        await update.message.reply_text("📚 لا يوجد سجل حتى الآن.")
        return
    text = "📚 آخر الأعمال:\n\n"
    for jid, kind, status, created, path in rows:
        icon = "🎬" if kind == "video" else "🎵"
        text += f"{icon} #{jid} — {status} — {created}\n"
    await update.message.reply_text(text)

async def choose_mode(update, mode):
    uid = update.effective_user.id
    if uid in ACTIVE:
        await update.message.reply_text("⏳ عندك عملية قيد التنفيذ. استخدم /cancel أولاً.")
        return
    s = session(uid)
    s["mode"] = mode
    if mode == "video":
        s["step"] = "prompt"
        await update.message.reply_text("🎬 اكتب وصف الفيديو بالتفصيل.")
    else:
        s["step"] = "lyrics"
        await update.message.reply_text("🎵 أرسل كلمات الأغنية كاملة، وكل مقطع في سطر.")

async def video_cmd(update, context):
    await choose_mode(update, "video")

async def song_cmd(update, context):
    await choose_mode(update, "song")

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    s = session(uid)
    data = q.data

    if data == "video":
        if uid in ACTIVE:
            await q.message.reply_text("⏳ لديك عملية قيد التنفيذ.")
            return
        s.update({"mode": "video", "step": "prompt", "data": {}})
        await q.message.reply_text("🎬 اكتب وصف الفيديو بالتفصيل.")
    elif data == "song":
        if uid in ACTIVE:
            await q.message.reply_text("⏳ لديك عملية قيد التنفيذ.")
            return
        s.update({"mode": "song", "step": "lyrics", "data": {}})
        await q.message.reply_text("🎵 أرسل كلمات الأغنية كاملة.")
    elif data.startswith("aspect:"):
        s["data"]["aspect"] = data.split(":", 1)[1]
        s["step"] = "duration"
        await q.message.reply_text("اختر مدة الفيديو:", reply_markup=duration_menu("video"))
    elif data.startswith("duration:"):
        sec = int(data.split(":", 1)[1])
        s["data"]["seconds"] = sec
        if s["mode"] == "video":
            await launch_video(q.message, uid)
        else:
            await launch_song(q.message, uid)
    elif data == "history":
        rows = history(uid)
        text = "📚 لا يوجد سجل." if not rows else "\n".join(
            f"#{r[0]} — {r[1]} — {r[2]} — {r[3]}" for r in rows
        )
        await q.message.reply_text(text)
    elif data == "cancel":
        SESSIONS.pop(uid, None)
        ACTIVE.discard(uid)
        await q.message.reply_text("❌ تم الإلغاء.", reply_markup=main_menu())

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    s = session(uid)
    text = (update.message.text or "").strip()
    if not text:
        return

    if s["step"] == "prompt" and s["mode"] == "video":
        s["data"]["prompt"] = text
        s["step"] = "aspect"
        await update.message.reply_text("اختر مقاس الفيديو:", reply_markup=aspect_menu())
        return

    if s["step"] == "lyrics" and s["mode"] == "song":
        s["data"]["lyrics"] = text
        s["step"] = "style"
        await update.message.reply_text(
            "🎼 اكتب نوع/مزاج الأغنية، مثل: طرب عربي حزين، بوب، راب، رومانسي."
        )
        return

    if s["step"] == "style" and s["mode"] == "song":
        s["data"]["style"] = text
        s["step"] = "reference"
        await update.message.reply_text(
            "🎤 اكتب مرجعًا موسيقيًا عامًا إن أردت، مثل: صوت رجالي دافئ وطرب يمني. "
            "لا ننسخ صوت فنان حقيقي."
        )
        return

    if s["step"] == "reference" and s["mode"] == "song":
        s["data"]["reference"] = text
        s["step"] = "duration"
        await update.message.reply_text(
            "اختر مدة الأغنية:", reply_markup=duration_menu("song")
        )
        return

    await update.message.reply_text("استخدم /start لفتح القائمة.")

async def launch_video(message, uid):
    s = session(uid)
    ACTIVE.add(uid)
    prompt = s["data"]["prompt"]
    aspect = s["data"]["aspect"]
    seconds = min(int(s["data"]["seconds"]), MAX_VIDEO_SECONDS)
    jid = add_job(uid, "video", prompt, "running")
    await message.reply_text("🎬 بدأت صناعة الفيديو... قد يستغرق عدة دقائق.")
    try:
        out = str(Path(OUTPUT_DIR) / f"video_{uid}_{jid}.mp4")
        await generate_video(prompt + f" | cinematic | aspect ratio {aspect} | duration about {seconds}s",
                             aspect, seconds, out)
        final = out
        if Path(final).stat().st_size > 48 * 1024 * 1024:
            compressed = str(Path(OUTPUT_DIR) / f"video_{uid}_{jid}_compressed.mp4")
            await compress_video(final, compressed)
            final = compressed
        update_job(jid, "done", final)
        await message.reply_video(
            video=InputFile(final),
            caption="✅ تم إنشاء الفيديو.\nيمكنك حفظه ونشره."
        )
    except Exception as e:
        update_job(jid, "failed")
        await message.reply_text(f"❌ فشل إنشاء الفيديو:\n{str(e)[:1000]}")
    finally:
        ACTIVE.discard(uid)
        SESSIONS.pop(uid, None)

async def launch_song(message, uid):
    s = session(uid)
    ACTIVE.add(uid)
    d = s["data"]
    seconds = min(int(d["seconds"]), MAX_AUDIO_MINUTES * 60)
    jid = add_job(uid, "song", d["lyrics"], "running")
    await message.reply_text("🎵 بدأت صناعة الأغنية واللحن والغناء... قد يستغرق عدة دقائق.")
    try:
        out = str(Path(OUTPUT_DIR) / f"song_{uid}_{jid}.mp3")
        await generate_song(
            d["lyrics"], d.get("style", ""), d.get("reference", ""),
            seconds, out
        )
        update_job(jid, "done", out)
        await message.reply_audio(
            audio=InputFile(out),
            title=f"AI Studio #{jid}",
            caption="✅ تم إنشاء الأغنية."
        )
    except Exception as e:
        update_job(jid, "failed")
        await message.reply_text(f"❌ فشل إنشاء الأغنية:\n{str(e)[:1000]}")
    finally:
        ACTIVE.discard(uid)
        SESSIONS.pop(uid, None)

async def error_handler(update, context):
    print("ERROR:", context.error)

def main():
    init_db()
    app = Application.builder().token(
        __import__("app.config", fromlist=["TELEGRAM_BOT_TOKEN"]).TELEGRAM_BOT_TOKEN
    ).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("video", video_cmd))
    app.add_handler(CommandHandler("song", song_cmd))
    app.add_handler(CommandHandler("history", history_cmd))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(error_handler)

    print("AI Studio Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
