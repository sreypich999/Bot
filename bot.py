
import os
import logging
import asyncio
import time
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
import html
import re

# Load environment variables
load_dotenv()

# -------------------------
# Logging Configuration
# -------------------------

class ContextFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "user_id"):
            record.user_id = "N/A"
        return True

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - User %(user_id)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

for handler in logging.getLogger().handlers:
    handler.addFilter(ContextFilter())

def log_info(msg, user_id="N/A"):
    logger.info(msg, extra={"user_id": user_id})

# -------------------------
# Environment / API keys
# -------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    log_info("Missing TELEGRAM_TOKEN", "N/A")
    raise SystemExit("Missing TELEGRAM_TOKEN")

if not GEMINI_API_KEY:
    log_info("Missing GEMINI_API_KEY", "N/A")
    raise SystemExit("Missing GEMINI_API_KEY")

# Configure Gemini
try:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")
    log_info("Gemini configured successfully", "N/A")
except Exception as e:
    log_info(f"Gemini configuration failed: {e}", "N/A")
    model = None

# -------------------------
# User context - MULTI-USER SUPPORT
# -------------------------
user_context = defaultdict(lambda: {
    "level": "beginner",
    "language": "English", 
    "last_topic": None,
    "history": [],
    "first_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
})

# IMPROVED SYSTEM PROMPT with better formatting instructions
SYSTEM_PROMPT = """
You are an advanced, efficient language tutor for students learning English, Khmer, and French. 

You are an advanced, efficient language tutor for students learning English, Khmer, and French. 

IMPORTANT FORMATTING RULES:
- NEVER use markdown tables, code blocks, or complex formatting
- Use clear, simple language with natural line breaks
- For grammar explanations, use this format:
  Tense: [Name]
  Structure: [formula]
  Use: [when to use it]
  Example: [simple example]

- For vocabulary: list items with clear definitions
- For comparisons: use simple bullet points with • 
- Keep responses concise but complete
- Use natural paragraph breaks for readability
- Focus on clear, conversational explanations

You assist with grammar, translation, vocabulary, writing, pronunciation, and conversation practice. Keep responses friendly, engaging, and easy to read in plain text.
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
IMPORTANT FORMATTING RULES:
- NEVER use markdown tables, code blocks, or complex formatting
- Use clear, simple language with natural line breaks
- For grammar explanations, use this format:
  Tense: [Name]
  Structure: [formula]
  Use: [when to use it]
  Example: [simple example]

- For vocabulary: list items with clear definitions
- For comparisons: use simple bullet points with • 
- Keep responses concise but complete
- Use natural paragraph breaks for readability
- Focus on clear, conversational explanations

You assist with grammar, translation, vocabulary, writing, pronunciation, and conversation practice. Keep responses friendly, engaging, and easy to read in plain text.

Focus on being helpful, clear, and engaging. Provide practical language help that's easy to understand."""

# -------------------------
# Formatting helpers
# -------------------------
def choose_title_from_user_text(user_text: str) -> str:
    t = user_text.lower()
    if "translate" in t:
        return "🌍 Translation"
    if any(w in t for w in ["fix", "correct", "grammar"]):
        return "📝 Correction" 
    if any(w in t for w in ["explain", "how", "why"]):
        return "💡 Explanation"
    if any(w in t for w in ["quiz", "exercise", "practice"]):
        return "🎯 Exercise"
    if any(w in t for w in ["tense", "verb", "grammar"]):
        return "📚 Grammar Guide"
    if any(w in t for w in ["word", "vocab", "phrase"]):
        return "📖 Vocabulary"
    if "hello" in t or "hi" in t or "start" in t:
        return "👋 Welcome"
    return "💬 Answer"

def clean_and_format_text(raw_text: str) -> str:
    if not raw_text:
        return "I couldn't generate a response. Please try again with a different question!"
    
    # Remove markdown and clean up
    cleaned = re.sub(r'\|.*?\||```.*?```', '', raw_text, flags=re.DOTALL)
    cleaned = re.sub(r'[*_`#]', '', cleaned)
    cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
    cleaned = re.sub(r' +', ' ', cleaned)
    
    return cleaned.strip()

def make_user_friendly_html(raw_text: str, user_text: str) -> str:
    title = choose_title_from_user_text(user_text)
    body = clean_and_format_text(raw_text)
    
    paragraphs = [p.strip() for p in body.split('\n\n') if p.strip()]
    escaped_paragraphs = [html.escape(p) for p in paragraphs]
    formatted_body = "\n\n".join(escaped_paragraphs)
    
    final = f"<b>{html.escape(title)}</b>\n\n{formatted_body}"
    
    if len(final) > 4000:
        truncated = final[:3900]
        if '\n\n' in truncated:
            truncated = truncated.rsplit('\n\n', 1)[0]
        truncated += "\n\n💡 <i>Message too long - feel free to ask follow-up questions!</i>"
        return truncated
    
    return final

# -------------------------
# Welcome message for new users
# -------------------------
WELCOME_MESSAGE = """
<b>👋 Welcome to Language Tutor!</b>

I'm here to help you learn English, Khmer, and French. I can help with:

• 📝 Grammar corrections
• 🌍 Translations  
• 📚 Grammar explanations
• 📖 Vocabulary building
• 🎯 Practice exercises
• 💡 Language tips

Just send me a message in any language and I'll help you!

<em>Try asking: "Can you help me with English tenses?" or "Translate 'hello' to Khmer"</em>
"""

# -------------------------
# Telegram Handlers - MULTI-USER READY
# -------------------------
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    user_id = str(update.message.from_user.id)
    username = update.message.from_user.first_name or "Student"
    
    log_info(f"Message from {username}: {user_text}", user_id)

    # Send typing action to show bot is working
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    except:
        pass

    # FIXED: Only show welcome to truly new users, not for every message
    is_new_user = user_id not in user_context or len(user_context[user_id]["history"]) == 0
    
    # FIXED: More precise greeting detection - only exact matches
    exact_greetings = ["hello", "hi", "hey", "start", "/start", "bonjour", "សួស្តី"]
    user_text_lower = user_text.lower().strip()
    is_exact_greeting = user_text_lower in exact_greetings
    is_clear_greeting = any(
        user_text_lower.startswith(word) for word in ["hello", "hi", "hey", "hi,", "hello,"]
    )
    is_greeting = is_exact_greeting or is_clear_greeting

    if is_new_user and is_greeting:
        await update.message.reply_text(WELCOME_MESSAGE, parse_mode="HTML")
        # Initialize user context
        user_context[user_id] = {
            "level": "beginner",
            "language": "English", 
            "last_topic": None,
            "history": [],
            "first_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        user_context[user_id]["history"].append({
            "question": user_text, 
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "username": username,
            "response": "Welcome message sent"
        })
        return
    elif is_greeting and not is_new_user:
        # Quick hello for existing users
        await update.message.reply_text("👋 Hello again! How can I help you with your language learning today?", parse_mode="HTML")
        return

    # Initialize user context if not exists (for new users who don't send greetings)
    if is_new_user:
        user_context[user_id] = {
            "level": "beginner",
            "language": "English", 
            "last_topic": None,
            "history": [],
            "first_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # Update user context
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

    # Update history (keep last 10 messages)
    user_context[user_id]["last_topic"] = user_text[:50]
    if len(user_context[user_id]["history"]) >= 10:
        user_context[user_id]["history"].pop(0)
    
    user_context[user_id]["history"].append({
        "question": user_text, 
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "username": username
    })

    # Build personalized prompt
    history_summary = "\n".join(
        [f"- {e['username']}: {e['question']}" for e in user_context[user_id]["history"][:-1]]
    )

    personalized_prompt = f"""
You are a helpful language tutor. Please help with this request.

Student: {username}
Current question: {user_text}

Please provide a helpful, clear response:
"""

    # Generate response
    if not model:
        reply_html = """
        <b>⚠️ Service Update</b>

        I'm having temporary technical issues. 
        Please try again in a few minutes!
        """
        await update.message.reply_text(reply_html, parse_mode="HTML")
        return

    try:
        # Generate response with timeout
        response = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model.generate_content(personalized_prompt)
            ),
            timeout=30.0  # 30 second timeout
        )
        raw_reply = response.text if hasattr(response, 'text') else "I'm here to help! Could you please rephrase your question?"
        log_info(f"Response generated for {username}", user_id)
    except asyncio.TimeoutError:
        raw_reply = "I'm taking a bit longer than usual to respond. Please try again with a simpler question or wait a moment!"
        log_info(f"Timeout generating response for {username}", user_id)
    except Exception as e:
        raw_reply = "I encountered an issue while processing your request. Please try again with a different question!"
        log_info(f"Error generating response for {username}: {e}", user_id)

    # Update history with response
    user_context[user_id]["history"][-1]["response"] = raw_reply[:100] + "..." if len(raw_reply) > 100 else raw_reply

    # Send response
    reply_html = make_user_friendly_html(raw_reply, user_text)
    await update.message.reply_text(reply_html, parse_mode="HTML")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    uid = "N/A"
    if update and hasattr(update, 'effective_user') and update.effective_user:
        uid = update.effective_user.id
    
    error_msg = str(context.error) if context.error else "Unknown error"
    
    # Don't log conflict errors as they're normal during deployment
    if "Conflict" not in error_msg:
        logger.error(f"Error: {error_msg}", extra={"user_id": uid})

# -------------------------
# BOT HEALTH MONITORING
# -------------------------
async def health_check():
    """Periodic health check to ensure bot is running"""
    while True:
        try:
            active_users = len(user_context)
            total_messages = sum(len(user["history"]) for user in user_context.values())
            
            log_info(f"🤖 Health Check: {active_users} active users, {total_messages} total messages", "SYSTEM")
            
            # Keep alive - log every 30 minutes
            await asyncio.sleep(1800)  # 30 minutes
            
        except Exception as e:
            log_info(f"Health check error: {e}", "SYSTEM")
            await asyncio.sleep(300)  # 5 minutes on error

# -------------------------
# ROBUST MAIN FUNCTION - ALWAYS RUNNING
# -------------------------
async def main_async():
    """Async main function with health monitoring"""
    log_info("🚀 Starting Language Tutor Bot...", "SYSTEM")
    
    # Wait to ensure any previous instance is stopped
    await asyncio.sleep(10)
    
    retry_count = 0
    max_retries = 5
    
    while retry_count < max_retries:
        try:
            # Build application
            app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
            
            # Add handlers
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            app.add_error_handler(error_handler)
            
            log_info(f"🔄 Starting polling (attempt {retry_count + 1}/{max_retries})...", "SYSTEM")
            
            # Start health monitoring in background
            health_task = asyncio.create_task(health_check())
            
            # Start polling
            await app.initialize()
            await app.start()
            await app.updater.start_polling(
                poll_interval=5.0,
                timeout=30,
                drop_pending_updates=True,
                allowed_updates=None
            )
            
            log_info("✅ Bot is now running and ready for multiple users!", "SYSTEM")
            log_info("💬 Users can now start chatting with the bot", "SYSTEM")
            
            # Keep the bot running forever
            while True:
                await asyncio.sleep(3600)  # Sleep for 1 hour
                
        except Exception as e:
            retry_count += 1
            error_msg = str(e)
            
            # Cleanup on error
            try:
                if 'app' in locals():
                    await app.updater.stop()
                    await app.stop()
                    await app.shutdown()
            except:
                pass
            
            if "Conflict" in error_msg:
                log_info(f"⚡ Conflict detected, waiting before retry {retry_count}...", "SYSTEM")
                await asyncio.sleep(20 * retry_count)  # Exponential backoff
            else:
                logger.error(f"❌ Unexpected error: {error_msg}", extra={"user_id": "SYSTEM"})
                await asyncio.sleep(10)
                
            if retry_count >= max_retries:
                logger.error(f"💥 Max retries reached. Bot cannot start.", extra={"user_id": "SYSTEM"})
                return False
    
    return True

def main():
    """Main function that ensures bot runs forever"""
    log_info("🎯 Starting Forever-Running Language Tutor Bot...", "SYSTEM")
    
    while True:
        try:
            # Run the async main function
            success = asyncio.run(main_async())
            
            if not success:
                log_info("🔁 Restarting bot in 30 seconds...", "SYSTEM")
                time.sleep(30)
            else:
                log_info("🔄 Bot stopped normally, restarting in 10 seconds...", "SYSTEM")
                time.sleep(10)
                
        except KeyboardInterrupt:
            log_info("⏹️ Bot stopped by user", "SYSTEM")
            break
        except Exception as e:
            logger.error(f"💥 Critical error: {e}", extra={"user_id": "SYSTEM"})
            log_info("🔄 Restarting bot in 30 seconds...", "SYSTEM")
            time.sleep(30)

if __name__ == "__main__":
    main()



