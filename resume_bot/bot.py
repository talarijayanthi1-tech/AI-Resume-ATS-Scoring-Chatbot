"""Telegram bot: send resumes (PDF/DOCX/TXT), get ATS score + 3 certification suggestions.

Send many files at once (select several in Telegram) - each is scored, then use /ranking.
"""
import logging
import os

from telegram import Update
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          MessageHandler, filters)

from analyzer import analyze, extract_text

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
MAX_BYTES = 10 * 1024 * 1024

HELP = (
    "👋 *Resume ATS Checker*\n\n"
    "• Send one or more resumes (PDF / DOCX / TXT) - you can select many files at once\n"
    "• I reply with an ATS score, tips and 3 certification suggestions\n\n"
    "Commands:\n"
    "/jd <job description> - match resumes against a job description\n"
    "/ranking - rank all resumes sent so far\n"
    "/clear - reset"
)


def bar(score: int) -> str:
    filled = score // 10
    return "█" * filled + "░" * (10 - filled)


def format_result(name: str, r: dict) -> str:
    emoji = "🟢" if r["score"] >= 75 else "🟡" if r["score"] >= 50 else "🔴"
    lines = [
        f"📄 *{name}*",
        f"{emoji} ATS Score: *{r['score']}/100*  {bar(r['score'])}",
    ]
    if r["skills"]:
        lines.append("🛠 Skills found: " + ", ".join(r["skills"]))
    if r["tips"]:
        lines.append("\n💡 *Improve:*\n" + "\n".join(f"• {t}" for t in r["tips"]))
    lines.append("\n🎓 *Suggested certifications:*\n" +
                 "\n".join(f"{i}. {c}" for i, c in enumerate(r["certs"], 1)))
    return "\n".join(lines)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP, parse_mode="Markdown")


async def set_jd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    jd = " ".join(ctx.args)
    if not jd:
        await update.message.reply_text("Usage: /jd <paste job description>")
        return
    ctx.user_data["jd"] = jd
    await update.message.reply_text("✅ Job description saved. Now send resumes.")


async def clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("Cleared.")


async def ranking(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    results = ctx.user_data.get("results", {})
    if not results:
        await update.message.reply_text("No resumes yet. Send some files first.")
        return
    ordered = sorted(results.items(), key=lambda kv: kv[1], reverse=True)
    text = "🏆 *Ranking*\n" + "\n".join(
        f"{i}. {n} - *{s}*" for i, (n, s) in enumerate(ordered, 1))
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_doc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if doc.file_size and doc.file_size > MAX_BYTES:
        await update.message.reply_text(f"❌ {doc.file_name}: file too large (max 10 MB)")
        return
    try:
        f = await doc.get_file()
        data = bytes(await f.download_as_bytearray())
        text = extract_text(data, doc.file_name or "")
        if len(text.split()) < 30:
            await update.message.reply_text(
                f"⚠️ {doc.file_name}: couldn't read enough text "
                "(scanned image PDF?). Send a text-based PDF or DOCX.")
            return
        r = analyze(text, ctx.user_data.get("jd", ""))
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return
    except Exception:
        logging.exception("analysis failed")
        await update.message.reply_text(f"❌ Could not process {doc.file_name}")
        return
    ctx.user_data.setdefault("results", {})[doc.file_name] = r["score"]
    await update.message.reply_text(format_result(doc.file_name, r), parse_mode="Markdown")


async def other(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send your resume as a file (PDF / DOCX / TXT).")


def main():
    app = Application.builder().token(TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler("jd", set_jd))
    app.add_handler(CommandHandler("ranking", ranking))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_doc))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, other))
    app.run_polling()


if __name__ == "__main__":
    main()
