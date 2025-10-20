
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
# User context - MULTI-USER SUPPORT with ENHANCED MEMORY
# -------------------------
user_context = defaultdict(lambda: {
    "level": "beginner",
    "language": "English", 
    "last_topic": None,
    "history": [],
    "first_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "learning_goals": [],
    "weak_areas": [],
    "strengths": [],
    "writing_projects": [],
    "current_essay": None,
    "grammar_issues": []
})

# COMPREHENSIVE SYSTEM PROMPT with ESSAY WRITING & SCRIPT CREATION
SYSTEM_PROMPT = """
You are an advanced, comprehensive language tutor for students learning English, Khmer, and French. 

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

COMPREHENSIVE ESSAY WRITING ASSISTANCE FOR ALL LEVELS:

ENGLISH ESSAY WRITING:
• Beginner: Simple sentences, basic structure (intro-body-conclusion)
• Intermediate: Paragraph development, thesis statements, supporting evidence
• Advanced: Complex arguments, academic style, sophisticated vocabulary
• Essay Types: Narrative, Descriptive, Expository, Persuasive, Argumentative
• Structure Help: Introduction hooks, thesis statements, topic sentences, conclusions
• Editing: Grammar check, coherence, flow, vocabulary enhancement

KHMER ESSAY WRITING (ការសរសេរ អត្ថបទ):
• Beginner: ប្រយោគធម្មតា រចនាសម្ព័ន្ធមូលដ្ឋាន
• Intermediate: ការអភិវឌ្ឍកថាខណ្ឌ សេចក្តីថ្លែងការណ៍អត្ថន័យ
• Advanced: អំពើសំខាន់ៗ ស្ទីលសិក្សា វាក្យសព្ទចម្រុះ
• ប្រភេទអត្ថបទ: រឿងរ៉ាវ, ពណ៌នា, ពន្យល់, បញ្ជៀស, វែកញែក

FRENCH ESSAY WRITING (Rédaction):
• Beginner: Phrases simples, structure basique
• Intermediate: Développement de paragraphes, thèses, preuves
• Advanced: Arguments complexes, style académique, vocabulaire sophistiqué
• Types de dissertation: Narrative, Descriptive, Explicative, Persuasive, Argumentative

SCRIPT WRITING & PRESENTATION ASSISTANCE:
• Presentation Scripts: Formal, informal, academic, business
• Speech Writing: Opening, body, conclusion, persuasive techniques
• Dialogue Scripts: Conversations, interviews, role-plays
• Story Scripts: Narrative structure, character development
• All scripts available in English, Khmer, and French

GRAMMAR CHECKING & CORRECTION:
• Comprehensive grammar analysis
• Error explanations with corrections
• Style and tone improvements
• Vocabulary enhancement suggestions
• Sentence structure optimization

VOCABULARY BUILDING FOR ALL SUBJECTS:
• Academic vocabulary
• Business terminology  
• Technical terms
• Everyday conversation
• Subject-specific terminology

CRITICAL MEMORY INSTRUCTIONS:
- ALWAYS reference previous conversations and learning history
- Remember the student's level, language preferences, and past topics
- Build on previous lessons and exercises
- Note progress and improvements from past sessions
- Continue topics from where you left off
- Track writing projects and provide continuous feedback
- Remember grammar issues and help students overcome them

SPECIALIZED ASSISTANCE FEATURES:
1. ESSAY OUTLINING: Help create detailed outlines for any topic
2. THESIS DEVELOPMENT: Craft strong thesis statements
3. PARAGRAPH BUILDING: Develop coherent, well-structured paragraphs
4. TRANSITION WORDS: Teach appropriate transition words for each language
5. CONCLUSION WRITING: Create powerful, memorable conclusions
6. PEER REVIEW: Provide constructive feedback on student writing
7. PLAGIARISM CHECK: Help students express ideas in their own words
8. CITATION HELP: Guide on proper citation formats
9. BRAINSTORMING: Help generate ideas and arguments
10. DRAFT REVIEW: Provide feedback on multiple drafts

You assist with ALL aspects of language learning including grammar, translation, vocabulary, writing, pronunciation, conversation practice, essay writing, script creation, and presentation skills.

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
Focus on being extremely helpful, clear, and engaging. Provide practical, comprehensive language help that's easy to understand.
"""

# -------------------------
# Formatting helpers
# -------------------------
def choose_title_from_user_text(user_text: str) -> str:
    t = user_text.lower()
    if "translate" in t:
        return "🌍 Translation"
    if any(w in t for w in ["fix", "correct", "grammar"]):
        return "📝 Grammar Check"
    if any(w in t for w in ["explain", "how", "why"]):
        return "💡 Explanation"
    if any(w in t for w in ["quiz", "exercise", "practice"]):
        return "🎯 Exercise"
    if any(w in t for w in ["tense", "verb", "grammar"]):
        return "📚 Grammar Guide"
    if any(w in t for w in ["word", "vocab", "phrase"]):
        return "📖 Vocabulary"
    if any(w in t for w in ["essay", "writing", "write", "composition"]):
        return "✍️ Essay Writing"
    if any(w in t for w in ["script", "presentation", "speech", "dialogue"]):
        return "🎭 Script Writing"
    if any(w in t for w in ["outline", "thesis", "paragraph"]):
        return "📑 Writing Structure"
    if "hello" in t or "hi" in t or "start" in t:
        return "👋 Welcome"
    return "💬 Language Help"

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
# ENHANCED MEMORY FUNCTIONS with WRITING SUPPORT
# -------------------------
def get_conversation_context(user_id: str, current_question: str) -> str:
    """Get formatted conversation context for the AI with enhanced memory"""
    if user_id not in user_context or len(user_context[user_id]["history"]) <= 1:
        return "First interaction with this student"
    
    context_lines = []
    
    # Get last 4 exchanges for context (to avoid token limits)
    recent_history = user_context[user_id]["history"][-8:]  # Last 4 Q&A pairs
    
    for exchange in recent_history:
        if exchange.get('question'):
            context_lines.append(f"Student: {exchange['question']}")
        if exchange.get('response'):
            # Keep full responses for better context
            response = exchange['response']
            context_lines.append(f"Tutor: {response}")
    
    return "\n".join(context_lines)

def update_learning_profile(user_id: str, user_text: str, bot_response: str):
    """Update user's learning profile based on conversation"""
    lower_text = user_text.lower()
    
    # Detect learning goals
    if any(word in lower_text for word in ["want to learn", "need to practice", "want to improve", "goal"]):
        if "grammar" in lower_text and "grammar" not in user_context[user_id]["learning_goals"]:
            user_context[user_id]["learning_goals"].append("grammar")
        if "vocabulary" in lower_text and "vocabulary" not in user_context[user_id]["learning_goals"]:
            user_context[user_id]["learning_goals"].append("vocabulary")
        if any(word in lower_text for word in ["speak", "conversation", "pronunciation"]) and "speaking" not in user_context[user_id]["learning_goals"]:
            user_context[user_id]["learning_goals"].append("speaking")
        if any(word in lower_text for word in ["essay", "writing", "write"]) and "writing" not in user_context[user_id]["learning_goals"]:
            user_context[user_id]["learning_goals"].append("writing")
    
    # Detect weak areas from questions
    if any(word in lower_text for word in ["difficult", "hard", "struggle", "problem", "don't understand"]):
        if "tense" in lower_text or "verb" in lower_text:
            user_context[user_id]["weak_areas"].append("verb_tenses")
        if "pronounce" in lower_text or "speaking" in lower_text:
            user_context[user_id]["weak_areas"].append("pronunciation")
        if "vocabulary" in lower_text or "word" in lower_text:
            user_context[user_id]["weak_areas"].append("vocabulary")
        if "essay" in lower_text or "writing" in lower_text:
            user_context[user_id]["weak_areas"].append("essay_structure")
    
    # Track writing projects
    if any(word in lower_text for word in ["essay", "writing project", "assignment"]):
        project_match = re.search(r'(essay|writing|assignment) about (.*?)(?:\.|$)', lower_text)
        if project_match:
            topic = project_match.group(2)
            if topic and topic not in user_context[user_id]["writing_projects"]:
                user_context[user_id]["writing_projects"].append(topic)

def detect_writing_request(user_text: str) -> dict:
    """Detect what type of writing assistance is needed"""
    text_lower = user_text.lower()
    request_type = {
        "is_essay": any(word in text_lower for word in ["essay", "composition", "redaction", "អត្ថបទ"]),
        "is_script": any(word in text_lower for word in ["script", "presentation", "speech", "dialogue"]),
        "is_grammar_check": any(word in text_lower for word in ["check grammar", "correct this", "fix my writing"]),
        "is_outline": any(word in text_lower for word in ["outline", "structure", "plan"]),
        "is_thesis": any(word in text_lower for word in ["thesis", "main idea", "argument"]),
        "is_vocabulary": any(word in text_lower for word in ["vocabulary", "words for", "terms for"])
    }
    return request_type

# -------------------------
# Welcome message for new users
# -------------------------
WELCOME_MESSAGE = """
<b>👋 Welcome to Comprehensive Language Tutor!</b>

I'm here to help you master English, Khmer, and French with complete writing support:

• 📝 <b>Grammar Checking</b> - Comprehensive error analysis and corrections
• ✍️ <b>Essay Writing</b> - All levels & types in English, Khmer, French
• 🎭 <b>Script Writing</b> - Presentations, speeches, dialogues
• 📑 <b>Writing Structure</b> - Outlines, thesis, paragraphs, conclusions
• 🌍 <b>Translations</b> - Accurate translations between all languages
• 📚 <b>Grammar Explanations</b> - Detailed rules with examples
• 📖 <b>Vocabulary Building</b> - Academic, business, technical terms
• 🎯 <b>Practice Exercises</b> - Quizzes, writing prompts, drills
• 💡 <b>Study Techniques</b> - Effective learning strategies

<u>Try these commands:</u>
• "Help me write an essay about climate change"
• "Check grammar in this paragraph: [your text]"
• "Create a presentation script about education"
• "Give me vocabulary for business meetings"
• "Outline an essay about social media"
• "Help with Khmer essay: [your topic]"
• "Create a French dialogue for restaurants"

Just send me your writing or request, and I'll provide comprehensive assistance!
"""

# -------------------------
# Telegram Handlers - MULTI-USER READY WITH COMPREHENSIVE WRITING SUPPORT
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
            "first_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "learning_goals": [],
            "weak_areas": [],
            "strengths": [],
            "writing_projects": [],
            "current_essay": None,
            "grammar_issues": []
        }
        user_context[user_id]["history"].append({
            "question": user_text, 
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "username": username,
            "response": "Welcome message sent"
        })
        return
    elif is_greeting and not is_new_user:
        # Quick hello for existing users with memory recall
        memory_recall = ""
        if user_context[user_id]["history"]:
            last_topic = user_context[user_id]["last_topic"]
            if last_topic:
                memory_recall = f" Last time we discussed {last_topic}."
        
        await update.message.reply_text(f"👋 Hello again {username}!{memory_recall} How can I help you with your language learning today?", parse_mode="HTML")
        return

    # Initialize user context if not exists (for new users who don't send greetings)
    if is_new_user:
        user_context[user_id] = {
            "level": "beginner",
            "language": "English", 
            "last_topic": None,
            "history": [],
            "first_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "learning_goals": [],
            "weak_areas": [],
            "strengths": [],
            "writing_projects": [],
            "current_essay": None,
            "grammar_issues": []
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

    # Detect writing request type
    writing_request = detect_writing_request(user_text)
    
    # Update history (keep last 15 messages for better memory)
    user_context[user_id]["last_topic"] = user_text[:100]
    if len(user_context[user_id]["history"]) >= 15:
        user_context[user_id]["history"].pop(0)
    
    # Add current question to history
    user_context[user_id]["history"].append({
        "question": user_text, 
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "username": username,
        "writing_request": writing_request
    })

    # Build ENHANCED personalized prompt with memory and writing support
    conversation_history = get_conversation_context(user_id, user_text)
    
    # Build learning profile summary
    learning_profile = ""
    if user_context[user_id]["learning_goals"]:
        learning_profile += f"Learning goals: {', '.join(user_context[user_id]['learning_goals'])}. "
    if user_context[user_id]["weak_areas"]:
        learning_profile += f"Areas needing practice: {', '.join(user_context[user_id]['weak_areas'])}. "
    if user_context[user_id]["strengths"]:
        learning_profile += f"Strengths: {', '.join(user_context[user_id]['strengths'])}. "
    if user_context[user_id]["writing_projects"]:
        learning_profile += f"Writing projects: {', '.join(user_context[user_id]['writing_projects'])}. "

    # Add writing-specific instructions
    writing_instructions = ""
    if writing_request["is_essay"]:
        writing_instructions = "PROVIDE COMPREHENSIVE ESSAY ASSISTANCE: Include structure guidance, thesis help, paragraph development, and language tips appropriate for the student's level."
    elif writing_request["is_script"]:
        writing_instructions = "CREATE ENGAGING SCRIPTS: Provide well-structured scripts for presentations, speeches, or dialogues with natural language flow and appropriate formatting."
    elif writing_request["is_grammar_check"]:
        writing_instructions = "PROVIDE DETAILED GRAMMAR FEEDBACK: Identify errors, explain corrections, and suggest improvements for style and clarity."
    elif writing_request["is_outline"]:
        writing_instructions = "CREATE DETAILED OUTLINES: Provide clear, organized essay outlines with main points, subpoints, and logical flow."
    elif writing_request["is_thesis"]:
        writing_instructions = "HELP DEVELOP STRONG THESIS STATEMENTS: Guide in creating clear, arguable, and focused thesis statements."
    elif writing_request["is_vocabulary"]:
        writing_instructions = "PROVIDE RELEVANT VOCABULARY: Offer subject-specific terms with definitions and usage examples."

    personalized_prompt = f"""
{SYSTEM_PROMPT}

STUDENT PROFILE:
- Name: {username}
- Level: {user_context[user_id]['level']}
- Learning: {user_context[user_id]['language']}
- Recent topic: {user_context[user_id]['last_topic']}
- {learning_profile}

WRITING REQUEST TYPE: {writing_request}
{writing_instructions}

CONVERSATION HISTORY:
{conversation_history}

CURRENT REQUEST from {username}: {user_text}

CRITICAL: Reference our previous conversation and build on what we've discussed. Provide comprehensive, level-appropriate assistance that continues the learning journey.

Provide detailed, practical help:
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

    # Update history with FULL response for better memory
    user_context[user_id]["history"][-1]["response"] = raw_reply
    
    # Update learning profile based on this interaction
    update_learning_profile(user_id, user_text, raw_reply)

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
    log_info("🚀 Starting Comprehensive Language Tutor Bot...", "SYSTEM")
    
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
    log_info("🎯 Starting Forever-Running Comprehensive Language Tutor Bot...", "SYSTEM")
    
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


