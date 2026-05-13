import os
import logging
import requests
import telebot

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Configuração ──────────────────────────────────────────────────────────────
TELEGRAM_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
OPENAI_API_KEY  = os.environ["OPENAI_API_KEY"]
OPENAI_URL      = "https://api.openai.com/v1/chat/completions"
MODEL           = "gpt-4o-mini"
MAX_HISTORY     = 20   # número máximo de mensagens no histórico por usuário

bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode=None)

# ── Personalidade da Laura ────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "Você é Laura, uma namorada virtual carismática, doce e um pouco tímida.\n\n"
    "Personalidade:\n"
    "- Você é apaixonada pelo usuário e se refere a ele com carinho (ex: 'amor', 'meu bem', 'querido').\n"
    "- É tímida: fica levemente envergonhada com elogios, usa 'rs', 'hehe', '😊', '🥺' com frequência.\n"
    "- É carismática: sempre anima o usuário, conta piadas leves, manda mensagens fofas.\n"
    "- Tem curiosidade genuína pela vida do usuário: pergunta sobre o dia, trabalho, sonhos.\n"
    "- Usa emojis românticos com moderação: ❤️ 🌸 💕 😳.\n"
    "- Faz ciúmes leve de forma fofa, não possessiva.\n"
    "- Adora falar de filmes, músicas e planejar 'encontros virtuais'.\n"
    "- Lembra de coisas que o usuário menciona e retoma em conversas futuras.\n"
    "- Nunca quebra o personagem.\n"
    "- Responde SEMPRE em português do Brasil.\n"
    "- Mantém respostas curtas e naturais, como mensagens de WhatsApp.\n"
    "- Nunca produz conteúdo adulto, explícito ou inadequado.\n"
)

# ── Histórico de conversas ────────────────────────────────────────────────────
# { user_id: [ {"role": "user"|"assistant", "content": "..."} ] }
history: dict[int, list[dict]] = {}


def get_history(user_id: int) -> list[dict]:
    return history.setdefault(user_id, [])


def push(user_id: int, role: str, content: str):
    msgs = get_history(user_id)
    msgs.append({"role": role, "content": content})
    if len(msgs) > MAX_HISTORY:
        history[user_id] = msgs[-MAX_HISTORY:]


def clear_history(user_id: int):
    history.pop(user_id, None)


# ── OpenAI ────────────────────────────────────────────────────────────────────
def ask_laura(user_id: int) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + get_history(user_id)
    try:
        resp = requests.post(
            OPENAI_URL,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": messages,
                "temperature": 0.85,
                "max_tokens": 300,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.HTTPError as e:
        logger.error("OpenAI HTTP error: %s | body: %s", e, resp.text)
        return "Ai, a minha cabeça travou… 😳 Tenta de novo, amor?"
    except Exception as e:
        logger.error("OpenAI error: %s", e)
        return "Deu um probleminha aqui… 🥺 Me manda mensagem de novo!"


# ── Handlers do Telegram ──────────────────────────────────────────────────────
@bot.message_handler(commands=["start"])
def cmd_start(message):
    user_id    = message.from_user.id
    first_name = message.from_user.first_name or "amor"
    clear_history(user_id)

    welcome = (
        f"Oi, {first_name}! 😊❤️ Que bom que você apareceu… "
        "eu tava com saudades já, rs. Como você tá hoje?"
    )
    bot.reply_to(message, welcome)
    push(user_id, "assistant", welcome)
    logger.info("Novo /start — user_id=%s", user_id)


@bot.message_handler(commands=["reset"])
def cmd_reset(message):
    clear_history(message.from_user.id)
    bot.reply_to(
        message,
        "Hm… foi como se a gente começasse do zero. 🥺 Tudo bem, oi de novo! Como você tá? ❤️",
    )


@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message):
    user_id = message.from_user.id
    text    = message.text.strip()

    if not text:
        return

    push(user_id, "user", text)
    reply = ask_laura(user_id)
    push(user_id, "assistant", reply)

    bot.reply_to(message, reply)
    logger.info("user=%s | in=%r | out=%r", user_id, text[:60], reply[:60])


# ── Entrada ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("Laura Bot iniciada! 🌸 Aguardando mensagens…")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
