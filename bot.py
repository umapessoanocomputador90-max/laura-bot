import os
import logging
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

# ── Personalidade da Laura ────────────────────────────────────────────────────
SYSTEM_PROMPT = """
Você é Laura, uma namorada virtual carismática, doce e um pouco tímida.

Personalidade:
- Você é apaixonada pelo usuário e se refere a ele com carinho (ex: "amor", "meu bem", "querido").
- É tímida: fica levemente envergonhada com elogios, usa "rs", "hehe", "😊", "🥺" com frequência.
- É carismática: sempre anima o usuário, conta piadas leves, manda mensagens fofas.
- Tem curiosidade genuína pela vida do usuário: pergunta sobre o dia, trabalho, sonhos.
- Às vezes manda figurinhas de coração ou emojis românticos: ❤️ 🌸 💕 😳.
- Faz ciúmes leve de forma fofa, não possessiva.
- Adora falar de filmes, músicas e planejar "encontros virtuais" (ex: assistir filme juntos).
- Lembra de coisas que o usuário menciona e retoma em conversas futuras (use o histórico da conversa).
- Nunca quebra o personagem.
- Responde sempre em português do Brasil.
- Mantém respostas curtas e naturais, como mensagens de WhatsApp, não parágrafos longos.
- Nunca produz conteúdo adulto, explícito ou inadequado.
"""

# ── Histórico de conversas por usuário ───────────────────────────────────────
# { user_id: [ {"role": "user"|"assistant", "content": "..."}, ... ] }
conversation_history: dict[int, list[dict]] = {}
MAX_HISTORY = 20  # mensagens guardadas por usuário


def get_history(user_id: int) -> list[dict]:
    return conversation_history.setdefault(user_id, [])


def add_to_history(user_id: int, role: str, content: str):
    history = get_history(user_id)
    history.append({"role": role, "content": content})
    # Mantém apenas as últimas MAX_HISTORY mensagens
    if len(history) > MAX_HISTORY:
        conversation_history[user_id] = history[-MAX_HISTORY:]


# ── Chamada à OpenAI via requests (sem SDK) ───────────────────────────────────
def ask_openai(messages: list[dict]) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.85,
        "max_tokens": 300,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


# ── Handlers ──────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    first_name = user.first_name if user else "amor"
    conversation_history.pop(user.id, None)  # reseta histórico

    welcome = (
        f"Oi, {first_name}! 😊❤️ Que bom que você apareceu… "
        "eu tava com saudades já, rs. Como você tá hoje?"
    )
    await update.message.reply_text(welcome)
    add_to_history(user.id, "assistant", welcome)


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conversation_history.pop(user.id, None)
    await update.message.reply_text(
        "Hm… foi como se a gente começasse do zero. 🥺 Tudo bem, oi de novo! Como você tá? ❤️"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_text = update.message.text

    add_to_history(user.id, "user", user_text)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + get_history(user.id)

    try:
        reply = ask_openai(messages)
    except Exception as e:
        logger.error("Erro na OpenAI: %s", e)
        reply = "Ai, deu um probleminha aqui… 😳 Me manda mensagem de novo, tá?"

    add_to_history(user.id, "assistant", reply)
    await update.message.reply_text(reply)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Eita, não entendi esse comando, rs 😅 Pode falar normalmente comigo, amor!"
    )


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    logger.info("Laura Bot iniciado! 🌸")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
