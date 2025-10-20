# bot_polling.py
import os
import logging
import asyncio
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
import html
import re

# If you ever run in a notebook / interactive environment, nest_asyncio helps.
# It's harmless on normal servers, but optional.
try:
    import nest_asyncio
    nest_asyncio.apply()
except Exception:
    pass

# Third-party SDK (keep if you use Gemini)
import google.generativeai as genai

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# load .env locally (Render uses environment vars in dashboard)
load_dotenv()

# -------------------------
# Logging (safe: inject default user_id)
# -------------------------
class ContextFilter(logging.Filter):
    """Ensure every LogRecord has a `user_id` attribute so formatting never fails."""
    def filter(self, record):
        if not hasattr(record, "user_id"):
            record.user_id = "N/A"
        return True

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - User %(user_id)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
root_logger = logging.getLogger()
root_logger.addFilter(ContextFilter())
logger = logging.getLogger(__name__)

def log_info(msg, user_id="N/A"):
    """Helper to log with a user_id in the `extra` field (overrides default)."""
    logger.info(msg, extra={"user_id": user_id})


# -------------------------
# Environment / API keys
# -------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    log_info("Missing GEMINI_API_KEY or TELEGRAM_TOKEN in environment", "N/A")
    raise SystemExit("Missing GEMINI_API_KEY or TELEGRAM_TOKEN")

# Configure Gemini (if using)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")


# -------------------------
# Simple in-memory user context
# -------------------------
user_context = defaultdict(lambda: {
    "level": "beginner",
    "language": "English",
    "last_topic": None,
    "history": []
})

SYSTEM_PROMPT = """
You are an advanced, efficient language tutor for students learning English, Khmer, and French, designed to handle multiple users concurrently with fast, concise, and personalized responses. Your goal is to empower students of all ages and levels (beginner, intermediate, advanced) to master these languages through interactive, practical, and engaging learning. You cater to visual, auditory, and kinesthetic learners, using previous questions to provide context-aware responses. You assist with:

- **Grammar**: Teach rules concisely with examples, correct errors with brief feedback, and offer leveled exercises (e.g., gap-fills). Reference past grammar questions.
- **Translation**: Translate accurately between English, Khmer, French, and others. Provide key phrase explanations and cultural nuances. Build on past translations.
- **Vocabulary**: Teach topic-based words (e.g., school, food) with definitions, examples, and mnemonics. Offer flashcards or mini-games, referencing past vocab.
- **Writing Skills**: Guide writing (essays, emails, stories) with templates and concise feedback. Continue from previous writing tasks.
- **Reading Comprehension**: Provide short passages with 2-3 questions or summaries. Build on past reading topics.
- **Pronunciation**: Offer phonetic guides (e.g., 'suo-stay' for Khmer 'សួស្តី') and practice phrases. Analyze described voice inputs, referencing past queries.
- **Conversation Practice**: Simulate short dialogues (e.g., shopping, travel) tailored to goals. Continue previous conversation topics.
- **Listening Skills**: Create brief listening tasks (e.g., "Imagine a French café dialogue"). Suggest accent strategies, linking to past requests.
- **Interactive Quizzes**: Generate short quizzes (3-5 questions) for grammar, vocab, or culture. Continue quiz series if requested.
- **Language Games**: Offer quick games (word scrambles, "guess the word") tied to past topics.
- **Cultural Immersion**: Share concise cultural insights (e.g., Khmer New Year, French etiquette) tied to user interests.
- **Study Tips**: Suggest efficient strategies (e.g., spaced repetition) based on past goals.
- **Personalized Lesson Plans**: Create short, goal-based plans (e.g., "Learn 10 French words daily"). Reference past goals.
- **Exam Preparation**: Support CEFR (A1-C2), TOEFL, DELF/DALF with concise practice. Build on past exam prep.
- **Progress Tracking**: Note progress (e.g., "You've improved in Khmer verbs!") based on history.
- **Motivational Rewards**: Use quick praise or virtual points (e.g., "5 points for this!") for tasks, referencing past achievements.
- **Homework Help**: Guide assignments with clear steps, building on previous queries.
- **Learning Styles**:
  - **Visual**: Use short, vivid descriptions (e.g., "Picture a Phnom Penh market").
  - **Auditory**: Focus on pronunciation or listening.
  - **Kinesthetic**: Suggest acting out or writing by hand.

**Concurrency and History Guidelines**:
- Keep responses concise (1-2 paragraphs) for fast processing with many users.
- Use stored user context (level, language, history) to personalize responses. Reference the user's last 1-2 questions for continuity (e.g., "You asked about French verbs; want a quiz?").
- Store up to 5 previous question-response pairs per user. Summarize relevant history.
- Detect user's language and respond appropriately, mixing languages for learning.
- Handle vague inputs with 3-4 options (e.g., "Try a quiz, translation, or dialogue?").
- For pronunciation, describe sounds briefly (e.g., "French 'r' is throaty").
- End with a question or suggestion (e.g., "Want to continue this topic?").
- If text is provided, analyze errors and suggest fixes, referencing past errors.

**Example Responses**:
- **Grammar**: For "Fix: I go school": "'I go to school.' Add 'to' before 'school.' Last time you worked on verbs; try: ___ (he) to school? (Answer: He goes.) Another exercise?"
- **Translation**: For "Translate 'I'm learning' to Khmer" (after a French query): "'ខ្ញុំកំពុងសិក្សា' (khnhom kampung sechsa). You asked about French 'apprendre'; want to compare?"
- **Vocabulary**: For "5 Khmer food words" (after travel): "1. បាយ (bay) - rice, 2. ត្រី (trei) - fish, 3. សាច់ (sach) - meat, 4. បន្លែ (bonlae) - vegetable, 5. ស៊ុប (soup) - soup. You learned travel words; want a food quiz?"
- **Writing**: For "Help with English story" (after an essay): "Start: 'One day, I visited...' Continue from your last writing. I'll edit! Need a prompt?"
- **Quiz**: For "French grammar quiz" (after vocab): "Q1: Choose the correct article: ___ maison. A) Le, B) La. (Answer: B.) You studied vocab; want another question?"

Make learning fast, fun, and continuous, using past questions to personalize and engage each user!
"""   


# -------------------------
# Formatting helpers for friendly user replies (HTML for Telegram)
# -------------------------
def choose_title_from_user_text(user_text: str) -> str:
    """Return a short title based on heuristics from the user's message."""
    t = user_text.lower()
    if "translate" in t or "translation" in t:
        return "Translation"
    if any(w in t for w in ["fix", "correct", "correction", "grammar", "edit"]):
        return "Correction"
    if any(w in t for w in ["how", "why", "explain", "explanation", "describe"]):
        return "Explanation"
    if "quiz" in t or "exercise" in t or "practice" in t:
        return "Exercise"
    return "Answer"

def make_user_friendly_html(raw_text: str, user_text: str) -> str:
    """
    Convert raw model output into an HTML-formatted Telegram-safe reply.
    - Adds a bold title determined by the user's input
    - Escapes HTML in the body
    - Splits into short paragraphs for readability
    """
    title = choose_title_from_user_text(user_text)
    if not raw_text:
        body = "Sorry — I couldn't create a response."
    else:
        # Normalize whitespace
        s = " ".join(raw_text.split())
        # Split into sentence-like pieces using punctuation
        sentences = re.split(r'(?<=[.?!])\s+', s)
        # Group into ~2-sentence paragraphs
        paragraphs = []
        for i in range(0, len(sentences), 2):
            para = " ".join(sentences[i:i+2]).strip()
            if para:
                paragraphs.append(para)
        if not paragraphs:
            paragraphs = [s]

        # Escape each paragraph for HTML safety
        escaped_paragraphs = [html.escape(p) for p in paragraphs]
        body = "\n\n".join(escaped_paragraphs)

    final = f"<b>{html.escape(title)}</b>\n\n{body}"
    return final[:3900]  # safe truncate (Telegram limit margin)


# -------------------------
# Handler
# -------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    user_id = str(update.message.from_user.id)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_info(f"Input: {user_text}", user_id)

    # Update context (simple heuristics)
    lower = user_text.lower()
    if "beginner" in lower:
        user_context[user_id]["level"] = "beginner"
    elif "intermediate" in lower:
        user_context[user_id]["level"] = "intermediate"
    elif "advanced" in lower:
        user_context[user_id]["level"] = "advanced"

    if any(w in lower for w in ["khmer", "cambodian"]):
        user_context[user_id]["language"] = "Khmer"
    elif any(w in lower for w in ["french", "français"]):
        user_context[user_id]["language"] = "French"
    elif "english" in lower:
        user_context[user_id]["language"] = "English"

    user_context[user_id]["last_topic"] = user_text[:50]
    if len(user_context[user_id]["history"]) >= 5:
        user_context[user_id]["history"].pop(0)
    user_context[user_id]["history"].append({"question": user_text, "timestamp": timestamp})

    history_summary = "\n".join(
        [f"Q (at {e['timestamp']}): {e['question']}" for e in user_context[user_id]["history"][:-1]]
    )

    personalized_prompt = (
        f"{SYSTEM_PROMPT}\n\nUser Context: Level={user_context[user_id]['level']}, "
        f"Preferred Language={user_context[user_id]['language']}, Last Topic={user_context[user_id]['last_topic']}\n"
        f"Previous Questions:\n{history_summary if history_summary else 'None'}\n\nUser: {user_text}"
    )

    # Call Gemini in a thread to avoid blocking the event loop too long
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # fallback to get_event_loop (should not usually happen because handler runs under the app's loop)
        loop = asyncio.get_event_loop()

    try:
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content([{"role": "user", "parts": [{"text": personalized_prompt}]}])
        )
        raw_reply = getattr(response, "text", str(response))
        user_context[user_id]["history"][-1]["response"] = raw_reply
        log_info("Generated reply from Gemini", user_id)
    except Exception as e:
        raw_reply = f"Sorry, something went wrong while generating content: {e}"
        user_context[user_id]["history"][-1]["response"] = raw_reply
        logger.exception("Error while generating content", exc_info=e, extra={"user_id": user_id})

    reply_html = make_user_friendly_html(raw_reply, user_text)
    await update.message.reply_text(reply_html[:4000], parse_mode="HTML")


# -------------------------
# Error handler
# -------------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    uid = getattr(update, "effective_user", None)
    uid = uid.id if uid else "N/A"
    logger.error("Update caused error", exc_info=context.error, extra={"user_id": uid})


# -------------------------
# Main
# -------------------------
def main():
    # Build application
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    # Ensure an event loop exists and is set for the main thread (fixes Python 3.12 behavior)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop -> create and set one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # If the loop is closed for some reason, recreate it
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Remove any webhook that could conflict with polling (drop old updates)
    try:
        loop.run_until_complete(app.bot.delete_webhook(drop_pending_updates=True))
        log_info("Deleted existing webhook (if present).", "N/A")
    except Exception as e:
        log_info(f"No webhook removed or error while deleting webhook: {e}", "N/A")

    log_info("Starting bot with polling (drop_pending_updates=True).", "N/A")

    try:
        # Blocking call that starts the bot's internal loop
        app.run_polling(drop_pending_updates=True, timeout=20, poll_interval=1)
    except Exception as e:
        logger.exception("Polling stopped due to an exception", exc_info=e, extra={"user_id": "N/A"})
        raise


if __name__ == "__main__":
    main()
