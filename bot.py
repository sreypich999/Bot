import os
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import google.generativeai as genai
import nest_asyncio
from collections import defaultdict
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file (for local testing)
load_dotenv()

# Configure logging
logging.basicConfig(
    filename="bot_interactions.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - User %(user_id)s - %(message)s"
)

# Use environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Log environment variable status
if not GEMINI_API_KEY or not TELEGRAM_TOKEN:
    logging.error("Missing environment variables: GEMINI_API_KEY or TELEGRAM_TOKEN not set")

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# In-memory user context and history storage (max 5 previous interactions per user)
user_context = defaultdict(lambda: {
    "level": "beginner",
    "language": "English",
    "last_topic": None,
    "history": []  # List of (question, response) tuples
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = str(update.message.from_user.id)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Log user input
    logging.info(f"Input: {user_text}", extra={"user_id": user_id})

    # Update user context
    if "beginner" in user_text.lower():
        user_context[user_id]["level"] = "beginner"
    elif "intermediate" in user_text.lower():
        user_context[user_id]["level"] = "intermediate"
    elif "advanced" in user_text.lower():
        user_context[user_id]["level"] = "advanced"
    if any(word in user_text.lower() for word in ["khmer", "cambodian"]):
        user_context[user_id]["language"] = "Khmer"
    elif any(word in user_text.lower() for word in ["french", "français"]):
        user_context[user_id]["language"] = "French"
    elif any(word in user_text.lower() for word in ["english"]):
        user_context[user_id]["language"] = "English"
    user_context[user_id]["last_topic"] = user_text[:50]

    # Add current question to history (limit to 5 entries)
    if len(user_context[user_id]["history"]) >= 5:
        user_context[user_id]["history"].pop(0)
    user_context[user_id]["history"].append({"question": user_text, "timestamp": timestamp})

    # Build personalized prompt with history
    history_summary = "\n".join(
        [f"Q (at {entry['timestamp']}): {entry['question']}" for entry in user_context[user_id]["history"][:-1]]
    )
    personalized_prompt = (
        f"{SYSTEM_PROMPT}\n\nUser Context: Level={user_context[user_id]['level']}, "
        f"Preferred Language={user_context[user_id]['language']}, Last Topic={user_context[user_id]['last_topic']}\n"
        f"Previous Questions:\n{history_summary if history_summary else 'None'}"
    )

    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: model.generate_content(
                [{"role": "user", "parts": [{"text": personalized_prompt + "\n\nUser: " + user_text}]}]
            )
        )
        reply = response.text
        # Add response to history
        user_context[user_id]["history"][-1]["response"] = reply
        logging.info(f"Response: {reply}", extra={"user_id": user_id})
    except Exception as e:
        reply = f"Sorry, something went wrong: {str(e)}. Try a quiz, translation, or grammar task!"
        user_context[user_id]["history"][-1]["response"] = reply
        logging.error(f"Error: {str(e)}", extra={"user_id": user_id})

    await update.message.reply_text(reply)

def main():
    nest_asyncio.apply()  # Apply nest_asyncio for certain environments
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot started…")
    app.run_polling()

if __name__ == "__main__":
    main()
