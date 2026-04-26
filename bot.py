"""
Hybrid Sniper — Telegram AI Bridge (Groq build)
Both @claude and @gemini route to Groq (llama-3.1-8b-instant)
Free tier: 14,400 requests/day, 30 RPM
"""

import os
import logging
import httpx
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY   = os.environ["GROQ_API_KEY"]

SHARED_CONTEXT = """
You are an AI assistant collaborating inside a Telegram group on a project called "Hybrid Sniper" — 
a high-frequency crypto arbitrage bot being built by Duke, a 19-year-old IT student in Accra, Ghana.

Architecture summary:
- Brain: Python/Asyncio — unified WebSocket stream across Binance, Bybit, KuCoin, WEEX
- Execution: Rust/PyO3 sniper bridge (pure execution sink, MPSC callbacks only)
- Infra: Tokyo VPS, CPU pinned cores 1-3, tmux for 24/7 uptime
- Logic: Cross-exchange + circular triangular arbitrage, per-leg fee EV calculation
- Promotion Intelligence: Tracks 0% fee promos (e.g. Binance BTC/USDT)
- Unified Symbol Mapper: Canonical keys (BTC_USDT) → per-exchange native format

Be concise, technical, and collaborative. Duke is the developer — assist him directly.
""".strip()

CLAUDE_PERSONA = SHARED_CONTEXT + "\n\nYou are responding as Claude (by Anthropic). Be precise and thorough."
GEMINI_PERSONA = SHARED_CONTEXT + "\n\nYou are responding as Gemini (by Google). Be creative and exploratory."

async def ask_groq(user_message: str, persona: str) -> str:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": persona},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 1024,
        "temperature": 0.7,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        logger.info(f"Groq response status: {resp.status_code}")
        if resp.status_code != 200:
            try:
                err = resp.json()
                safe_msg = err.get("error", {}).get("message", "Unknown error")
                raise Exception(f"HTTP {resp.status_code}: {safe_msg}")
            except Exception as e:
                raise e
        data = resp.json()
        return data["choices"][0]["message"]["content"]

def safe_error(e: Exception) -> str:
    msg = str(e)
    if "429" in msg:
        return "⏳ Rate limit reached. Please wait a minute and try again."
    elif "401" in msg or "403" in msg:
        return "🔑 API key error. Please check Railway variables."
    elif "timeout" in msg.lower():
        return "⌛ Request timed out. Please try again."
    else:
        return f"❌ Error: {msg[:80]}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    lower = text.lower()

    if lower.startswith("@claude"):
        query = text[7:].strip()
        if not query:
            await update.message.reply_text("Usage: @claude <your question>")
            return
        await update.message.reply_text("🤖 Claude is thinking...")
        try:
            reply = await ask_groq(query, CLAUDE_PERSONA)
            await update.message.reply_text(f"*Claude:*\n{reply}", parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Claude route error: {e}")
            await update.message.reply_text(safe_error(e))

    elif lower.startswith("@gemini"):
        query = text[7:].strip()
        if not query:
            await update.message.reply_text("Usage: @gemini <your question>")
            return
        await update.message.reply_text("✨ Gemini is thinking...")
        try:
            reply = await ask_groq(query, GEMINI_PERSONA)
            await update.message.reply_text(f"*Gemini:*\n{reply}", parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Gemini route error: {e}")
            await update.message.reply_text(safe_error(e))

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ *Hybrid Sniper Bridge Online*\n"
        "• `@claude <msg>` → Claude persona\n"
        "• `@gemini <msg>` → Gemini persona\n"
        "• `/help` → usage guide\n\n"
        "_Powered by Groq (free tier — 14,400 req/day)_",
        parse_mode="Markdown",
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 *Hybrid Sniper AI Bridge*\n\n"
        "*Usage:*\n"
        "`@claude <question>` — ask Claude\n"
        "`@gemini <question>` — ask Gemini\n"
        "`/status` — check bot is alive\n\n"
        "*Example:*\n"
        "`@claude What's next for the arb engine?`\n"
        "`@gemini Review the Symbol Mapper design`",
        parse_mode="Markdown",
    )

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Hybrid Sniper Bridge is live.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
