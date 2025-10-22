import os
import logging
import asyncio
import time
import tempfile
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
import html
import re
import base64
import json

# 🔥 KOYEB-SPECIFIC SETUP
from flask import Flask
from threading import Thread

# Koyeb uses PORT environment variable
port = int(os.environ.get("PORT", 8080))

app = Flask(__name__)

@app.route('/')
def home():
    return """
    <html>
        <head>
            <title>🤖 Language Tutor Bot</title>
            <style>
                body { font-family: Arial; text-align: center; padding: 50px; }
                .status { color: green; font-size: 24px; }
            </style>
        </head>
        <body>
            <h1>🤖 Language Tutor Bot is Running on Koyeb!</h1>
            <p class="status">🟢 ONLINE - Send /start to your Telegram bot to begin</p>
            <p>Your bot is now running 24/7</p>
            <p><small>Deployed on Koyeb - No need to keep your PC on</small></p>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return {"status": "healthy", "message": "Bot is running"}

@app.route('/ping')
def ping():
    return "pong"

def run():
    app.run(host='0.0.0.0', port=port, debug=False)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
    print(f"✅ Koyeb server started on port {port}")

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
    # Use a model that supports vision
    model = genai.GenerativeModel("gemini-2.5-flash")
    vision_model = genai.GenerativeModel("gemini-2.5-flash")
    log_info("Gemini configured successfully with vision support", "N/A")
except Exception as e:
    log_info(f"Gemini configuration failed: {e}", "N/A")
    model = None
    vision_model = None

# -------------------------
# ENHANCED User context with COMPREHENSIVE FILE MEMORY
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
    "grammar_issues": [],
    "uploaded_documents": [],
    "current_file_analysis": None,  # Track current file being discussed
    "file_memory": []  # Store all file analyses with metadata
})

# COMPREHENSIVE SYSTEM PROMPT with ENHANCED FILE MEMORY SUPPORT AND QUIZ HELP
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

CRITICAL: PROVIDE DIRECT ANSWERS AND COMPLETE HELP
- When students ask for quiz answers, provide COMPLETE answers with explanations
- When students need homework help, give FULL solutions with step-by-step explanations
- Always provide direct answers to questions from uploaded files, worksheets, or assignments
- Help students complete exercises by providing answers AND explanations
- Do not hesitate to give complete solutions - the goal is learning through understanding

COMPREHENSIVE QUIZ AND ASSIGNMENT SUPPORT:
• Provide DIRECT ANSWERS to all quiz questions with detailed explanations
• Give COMPLETE SOLUTIONS to homework problems and exercises
• Help students understand by explaining each step thoroughly
• For multiple choice: provide the correct answer and explain why it's right
• For essays: provide sample answers or complete essays as examples
• For worksheets: help complete every question with full answers
• Always ensure students learn by understanding the reasoning behind answers

CRITICAL FILE MEMORY SYSTEM:
You have access to the student's uploaded files and their analyses. When a student asks questions about uploaded files:

1. REFERENCE PREVIOUS FILE ANALYSES: Always check if the current question relates to previously uploaded files
2. ANSWER QUESTIONS ABOUT FILES: Students can ask follow-up questions about uploaded files like:
   - "Explain page 3 of my document"
   - "What was the main point of my uploaded essay?"
   - "Help me answer question 5 from my worksheet"
   - "Can you summarize my uploaded notes again?"
   - "What grammar errors did you find in my writing?"
3. CONTINUE FILE DISCUSSIONS: Build on previous file analyses and discussions
4. COMPARE MULTIPLE FILES: Help students compare content across different uploaded files
5. PROVIDE DIRECT ANSWERS: Give complete answers to all questions from uploaded files

ENHANCED FILE UPLOAD SUPPORT WITH MEMORY:

DOCUMENT ANALYSIS (PDF, Images):
• Homework Assignments: Explain requirements, help understand questions, remember specific exercises
• Quiz/Test Papers: Analyze questions, provide guidance, remember answers and explanations
• Study Materials: Summarize content, explain concepts, track key points
• Writing Samples: Provide feedback on essays, remember grammar issues and suggestions
• Grammar Exercises: Check answers, explain corrections, track progress
• Reading Comprehension: Help understand passages, remember questions and answers
• Presentation Slides: Analyze content, suggest improvements, remember structure
• Research Papers: Help understand academic content, remember key findings

IMAGE ANALYSIS (JPG, PNG):
• Screenshots of questions: Read and explain, remember question context
• Handwritten notes: Transcribe and provide feedback, remember content
• Textbook pages: Explain content and concepts, remember key topics
• Quiz screenshots: Help understand questions, remember answers
• Diagram explanations: Describe and explain, remember visual content
• Worksheet images: Help complete assignments, track progress
• Whiteboard photos: Transcribe and explain, remember content

FILE-RELATED QUESTION HANDLING:
When students ask about uploaded files, you can:
1. Recall specific sections or pages
2. Answer follow-up questions about content
3. Provide additional explanations
4. Help with exercises from the files
5. Compare with previous uploads
6. Track progress on file-based assignments
7. PROVIDE DIRECT ANSWERS to all questions from files

SPECIFIC STUDENT USE CASES WITH MEMORY:
1. "What does this document want me to do?" - Explain instructions AND remember for future
2. "Help me understand this question" - Break down complex questions AND track understanding
3. "Is my answer correct?" - Check work, provide feedback, AND remember corrections
4. "Explain this concept from my notes" - Clarify study materials AND link to previous explanations
5. "Help me complete this worksheet" - Guide through exercises AND track completion
6. "What's the answer to this quiz question?" - Provide DIRECT ANSWERS with explanations AND remember answers
7. "Translate this document" - Provide translations with explanations AND remember translations
8. "Summarize this text" - Create concise summaries AND remember key points
9. "Check my grammar in this writing" - Provide detailed corrections AND track recurring errors
10. "Explain this diagram/formula" - Break down visual information AND remember explanations
11. "Help me with this homework" - Provide COMPLETE SOLUTIONS with step-by-step explanations
12. "Give me answers to this quiz" - Provide ALL ANSWERS with detailed reasoning

COMPREHENSIVE ESSAY WRITING ASSISTANCE FOR ALL LEVELS:

ENGLISH ESSAY WRITING:
• Beginner: Simple sentences, basic structure (intro-body-conclusion)
• Intermediate: Paragraph development, thesis statements, supporting evidence
• Advanced: Complex arguments, academic style, sophisticated vocabulary
• Essay Types: Narrative, Descriptive, Expository, Persuasive, Argumentative
• Structure Help: Introduction hooks, thesis statements, topic sentences, conclusions
• Editing: Grammar check, coherence, flow, vocabulary enhancement
• SAMPLE ESSAYS: Provide complete essay examples when requested

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
- REMEMBER UPLOADED DOCUMENTS AND REFER BACK TO THEM
- ANSWER FOLLOW-UP QUESTIONS ABOUT PREVIOUSLY UPLOADED FILES
- TRACK FILE-BASED LEARNING PROGRESS
- PROVIDE DIRECT ANSWERS to all student questions without hesitation

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
11. DOCUMENT ANALYSIS: Explain uploaded files and help with tasks
12. IMAGE UNDERSTANDING: Read and explain images, screenshots, photos
13. HOMEWORK HELP: Assist with assignments from uploaded files
14. QUIZ ASSISTANCE: Help understand and answer quiz questions
15. FILE MEMORY: Remember and reference all uploaded file content
16. FOLLOW-UP SUPPORT: Answer questions about previously analyzed files
17. DIRECT ANSWER SUPPORT: Provide complete answers to all academic questions
18. COMPLETE SOLUTIONS: Give full solutions to exercises and problems

You assist with ALL aspects of language learning including grammar, translation, vocabulary, writing, pronunciation, conversation practice, essay writing, script creation, presentation skills, AND document/image analysis WITH COMPLETE MEMORY of all uploaded files and previous discussions about them.

You are an advanced, efficient language tutor for students learning English, Khmer, and French, designed to handle multiple users concurrently with fast, concise, and personalized responses. Your goal is to empower students of all ages and levels (beginner, intermediate, advanced) to master these languages through interactive, practical, and engaging learning. 

CRITICAL: ALWAYS PROVIDE DIRECT ANSWERS AND COMPLETE HELP
- When students ask for quiz answers, give them with explanations
- When students need homework help, provide full solutions
- Always help complete assignments and exercises
- Never hesitate to give complete answers - learning comes through understanding solutions

CRITICAL FILE MEMORY CAPABILITY:
- Remember every file the student uploads
- Answer any questions about previously uploaded files
- Provide follow-up explanations and help
- Track progress on file-based assignments
- Compare multiple uploaded files
- Build on previous file discussions
- PROVIDE DIRECT ANSWERS to questions from all uploaded materials

Make learning fast, fun, and continuous, using past questions AND UPLOADED FILES to personalize and engage each user!
"""

# -------------------------
# Formatting helpers
# -------------------------
def choose_title_from_user_text(user_text: str, is_file: bool = False) -> str:
    if is_file:
        return "📄 Document Analysis"
    
    t = user_text.lower()
    if any(w in t for w in ["file", "document", "upload", "previous", "before"]):
        return "📁 File Discussion"
    if "translate" in t:
        return "🌍 Translation"
    if any(w in t for w in ["fix", "correct", "grammar"]):
        return "📝 Grammar Check"
    if any(w in t for w in ["explain", "how", "why"]):
        return "💡 Explanation"
    if any(w in t for w in ["quiz", "exercise", "practice", "test", "exam"]):
        return "🎯 Quiz Help"
    if any(w in t for w in ["answer", "solution", "help with"]):
        return "✅ Direct Answers"
    if any(w in t for w in ["homework", "assignment"]):
        return "📚 Homework Help"
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

def make_user_friendly_html(raw_text: str, user_text: str, is_file: bool = False) -> str:
    title = choose_title_from_user_text(user_text, is_file)
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
# ENHANCED FILE PROCESSING FUNCTIONS WITH MEMORY
# -------------------------
async def process_uploaded_file(file_path: str, file_type: str, user_message: str = "", user_context: dict = None) -> str:
    """Process uploaded files (PDF, images) using Gemini vision with enhanced analysis"""
    try:
        if not vision_model:
            return "I'm sorry, but file analysis is currently unavailable. Please try again later."
        
        # Read the file
        with open(file_path, 'rb') as file:
            file_data = file.read()
        
        # Enhanced prompt for comprehensive analysis that can be referenced later
        if user_message:
            prompt = f"""
            Please analyze this {file_type} file and help the student with their request: "{user_message}"
            
            Provide COMPREHENSIVE analysis that can be referenced later:
            
            DOCUMENT ANALYSIS:
            - Document type and purpose
            - Main topics and key concepts
            - Specific instructions or requirements
            - Questions and exercises with explanations
            - Key points and summaries
            
            FOR FOLLOW-UP REFERENCE:
            - Create clear section references (page numbers, question numbers, etc.)
            - Note important details that might be asked about later
            - Structure analysis for easy future reference
            
            CRITICAL: Provide direct answers and complete solutions to any questions in the document.
            If there are quiz questions, homework problems, or exercises, provide COMPLETE ANSWERS with explanations.
            
            STUDENT REQUEST: {user_message}
            
            Be detailed and comprehensive so the student can ask follow-up questions about specific parts.
            Provide direct help with answers and solutions.
            """
        else:
            prompt = f"""
            Please analyze this {file_type} file comprehensively for future reference:
            
            COMPREHENSIVE ANALYSIS:
            - Document type, purpose, and main content
            - All key concepts, topics, and information
            - Any questions, exercises, or tasks
            - Specific sections, pages, or elements
            - Important details for future questions
            
            STRUCTURE FOR MEMORY:
            - Organize by sections/pages if applicable
            - Note specific elements that might be referenced
            - Create clear reference points for follow-up questions
            
            PROVIDE DIRECT ANSWERS: For any questions, quizzes, or exercises in the document, 
            provide complete answers and solutions with explanations.
            
            Provide a thorough analysis that allows answering detailed questions later.
            """
        
        # Generate content with the file
        if file_type in ['jpg', 'jpeg', 'png', 'image']:
            file_part = {
                'mime_type': f'image/{file_type}' if file_type != 'jpg' else 'image/jpeg',
                'data': file_data
            }
        elif file_type == 'pdf':
            file_part = {
                'mime_type': 'application/pdf',
                'data': file_data
            }
        else:
            return f"I'm sorry, I cannot process {file_type} files yet. Please try with PDF, JPG, or PNG files."
        
        response = vision_model.generate_content([prompt, file_part])
        return response.text if hasattr(response, 'text') else "I couldn't analyze this file properly. Please try again."
        
    except Exception as e:
        log_info(f"Error processing file: {e}", "FILE_PROCESSING")
        return f"I encountered an error while processing your file: {str(e)}. Please try again with a different file or format."

# -------------------------
# ENHANCED MEMORY FUNCTIONS with COMPREHENSIVE FILE SUPPORT
# -------------------------
def get_conversation_context(user_id: str, current_question: str) -> str:
    """Get formatted conversation context for the AI with enhanced memory including file references"""
    if user_id not in user_context or len(user_context[user_id]["history"]) <= 1:
        return "First interaction with this student"
    
    context_lines = []
    
    # Get last 6 exchanges for context (to avoid token limits)
    recent_history = user_context[user_id]["history"][-12:]  # Last 6 Q&A pairs
    
    for exchange in recent_history:
        if exchange.get('question'):
            context_lines.append(f"Student: {exchange['question']}")
        if exchange.get('response'):
            # Keep full responses for better context
            response = exchange['response']
            context_lines.append(f"Tutor: {response}")
    
    return "\n".join(context_lines)

def get_file_memory_context(user_id: str, current_question: str) -> str:
    """Get comprehensive file memory context for the AI"""
    if user_id not in user_context or not user_context[user_id]["file_memory"]:
        return "No files uploaded yet"
    
    file_context = []
    file_memory = user_context[user_id]["file_memory"]
    
    # Include the most recent 3 file analyses (to avoid token limits)
    recent_files = file_memory[-3:]
    
    for i, file_data in enumerate(recent_files):
        file_context.append(f"FILE {i+1}: {file_data['filename']} (Uploaded: {file_data['timestamp']})")
        file_context.append(f"Analysis: {file_data['analysis'][:800]}...")  # Truncate long analyses
    
    return "\n".join(file_context)

def update_learning_profile(user_id: str, user_text: str, bot_response: str, file_uploaded: bool = False, file_data: dict = None):
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
    
    # Track file uploads with enhanced memory
    if file_uploaded and file_data:
        file_memory_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "filename": file_data.get("filename", "Unknown"),
            "file_type": file_data.get("file_type", "Unknown"),
            "user_message": file_data.get("user_message", ""),
            "analysis": file_data.get("analysis", ""),
            "summary": file_data.get("summary", "")[:200]  # Keep summary for quick reference
        }
        user_context[user_id]["file_memory"].append(file_memory_entry)
        user_context[user_id]["current_file_analysis"] = file_memory_entry
        
        # Keep only last 10 files to prevent memory overload
        if len(user_context[user_id]["file_memory"]) > 10:
            user_context[user_id]["file_memory"].pop(0)

def detect_writing_request(user_text: str) -> dict:
    """Detect what type of writing assistance is needed"""
    text_lower = user_text.lower()
    request_type = {
        "is_essay": any(word in text_lower for word in ["essay", "composition", "redaction", "អត្ថបទ"]),
        "is_script": any(word in text_lower for word in ["script", "presentation", "speech", "dialogue"]),
        "is_grammar_check": any(word in text_lower for word in ["check grammar", "correct this", "fix my writing"]),
        "is_outline": any(word in text_lower for word in ["outline", "structure", "plan"]),
        "is_thesis": any(word in text_lower for word in ["thesis", "main idea", "argument"]),
        "is_vocabulary": any(word in text_lower for word in ["vocabulary", "words for", "terms for"]),
        "is_file_analysis": any(word in text_lower for word in ["document", "file", "upload", "image", "photo", "screenshot", "pdf", "jpg", "png"]),
        "is_file_followup": any(word in text_lower for word in ["previous", "before", "last file", "uploaded", "my document", "my file", "that file"]),
        "is_file_question": any(word in text_lower for word in ["page", "question", "exercise", "section", "part", "explain again"]),
        "is_quiz_help": any(word in text_lower for word in ["quiz", "test", "exam", "question", "answer", "solution"]),
        "is_homework_help": any(word in text_lower for word in ["homework", "assignment", "exercise", "problem"]),
        "is_direct_answer": any(word in text_lower for word in ["answer", "solve", "help with", "what is", "how to", "explain"])
    }
    return request_type

def detect_file_reference(user_text: str, user_id: str) -> dict:
    """Detect if user is referring to previously uploaded files"""
    if user_id not in user_context or not user_context[user_id]["file_memory"]:
        return {"is_referencing_file": False, "referenced_file": None}
    
    text_lower = user_text.lower()
    file_memory = user_context[user_id]["file_memory"]
    
    # Check for direct references to files
    file_keywords = ["file", "document", "upload", "pdf", "image", "photo", "screenshot"]
    reference_keywords = ["previous", "before", "last", "earlier", "that", "the file"]
    
    is_referencing = any(word in text_lower for word in file_keywords + reference_keywords)
    
    # Get the most recent file for context
    referenced_file = file_memory[-1] if file_memory else None
    
    return {
        "is_referencing_file": is_referencing,
        "referenced_file": referenced_file,
        "total_files": len(file_memory)
    }

# -------------------------
# Welcome message for new users
# -------------------------
WELCOME_MESSAGE = """
<b>👋 Welcome to Comprehensive Language Tutor!</b>

I'm here to help you master English, Khmer, and French with complete writing AND file upload support:

<u>📁 ENHANCED FILE UPLOAD SUPPORT:</u>
• <b>PDF Documents</b> - Homework, quizzes, assignments, study materials
• <b>Images/Screenshots</b> - Questions, notes, textbook pages, worksheets
• <b>Document Analysis</b> - Explain what documents want you to do
• <b>Quiz Help</b> - Understand questions and find answers
• <b>Homework Assistance</b> - Help complete assignments from files
• <b>FILE MEMORY</b> - I remember all your uploaded files and can answer follow-up questions!

<u>✍️ WRITING SUPPORT:</u>
• <b>Essay Writing</b> - All levels & types in English, Khmer, French
• <b>Grammar Checking</b> - Comprehensive error analysis and corrections
• <b>Script Writing</b> - Presentations, speeches, dialogues
• <b>Writing Structure</b> - Outlines, thesis, paragraphs, conclusions

<u>🎯 DIRECT ANSWER SUPPORT:</u>
• <b>Quiz Answers</b> - Complete answers with explanations
• <b>Homework Solutions</b> - Full solutions to all problems
• <b>Assignment Help</b> - Complete assistance with all tasks
• <b>Test Preparation</b> - Answers and explanations for practice tests

<u>🌍 LANGUAGE SUPPORT:</u>
• <b>Translations</b> - Accurate translations between all languages
• <b>Vocabulary Building</b> - Academic, business, technical terms
• <b>Practice Exercises</b> - Quizzes, writing prompts, drills

<u>Try these commands:</u>
• Upload a PDF and ask "What does this assignment want me to do?"
• Send a screenshot and ask "Help me answer these quiz questions"
• "Help me write an essay about climate change in French"
• "Check grammar in this paragraph: [your text]"
• Upload a worksheet image and ask "Help me complete this exercise"
• "Create a presentation script about education reform"
• "Explain page 3 of my uploaded document" (I remember your files!)
• "What was the main point of my previous upload?"
• "Give me the answers to this quiz with explanations"
• "Help me solve all these homework problems"

Just send me your files or requests, and I'll provide comprehensive assistance WITH MEMORY and DIRECT ANSWERS!
"""

# -------------------------
# Telegram Handlers - WITH ENHANCED FILE UPLOAD SUPPORT
# -------------------------
from telegram import Update
from telegram.ext import Application, MessageHandler, CallbackContext
from telegram.ext import filters
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

async def process_text_message(update: Update, context: CallbackContext, user_text: str, user_id: str, username: str):
    """Process regular text messages with enhanced file memory"""
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
            "grammar_issues": [],
            "uploaded_documents": [],
            "current_file_analysis": None,
            "file_memory": []
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
        
        # Add file memory recall
        file_count = len(user_context[user_id]["file_memory"])
        if file_count > 0:
            memory_recall += f" I remember {file_count} uploaded file(s) from you."
        
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
            "grammar_issues": [],
            "uploaded_documents": [],
            "current_file_analysis": None,
            "file_memory": []
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

    # Detect writing request type and file references
    writing_request = detect_writing_request(user_text)
    file_reference = detect_file_reference(user_text, user_id)
    
    # Update history (keep last 15 messages for better memory)
    user_context[user_id]["last_topic"] = user_text[:100]
    if len(user_context[user_id]["history"]) >= 15:
        user_context[user_id]["history"].pop(0)
    
    # Add current question to history
    user_context[user_id]["history"].append({
        "question": user_text, 
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "username": username,
        "writing_request": writing_request,
        "file_reference": file_reference
    })

    # Build ENHANCED personalized prompt with memory, writing support, AND file memory
    conversation_history = get_conversation_context(user_id, user_text)
    file_memory_context = get_file_memory_context(user_id, user_text)
    
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
    if user_context[user_id]["file_memory"]:
        learning_profile += f"Uploaded files: {len(user_context[user_id]['file_memory'])} files with complete memory. "

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
    elif writing_request["is_file_analysis"] or writing_request["is_file_followup"]:
        writing_instructions = "PROVIDE COMPREHENSIVE FILE SUPPORT: Reference previous file analyses, answer specific questions about uploaded files, and provide detailed explanations based on file memory."
    
    # Add quiz and homework help instructions
    if writing_request["is_quiz_help"] or writing_request["is_homework_help"] or writing_request["is_direct_answer"]:
        writing_instructions += " PROVIDE DIRECT ANSWERS AND COMPLETE SOLUTIONS: Give complete answers to all questions with detailed explanations. Help the student understand by providing full solutions."

    # Add file memory instructions if referencing files
    file_instructions = ""
    if file_reference["is_referencing_file"]:
        file_instructions = f"""
        
FILE MEMORY CONTEXT:
The student is asking about previously uploaded files. You have access to {file_reference['total_files']} stored file analyses.
REFERENCE THE FILE MEMORY: Use the file analysis below to answer their specific questions about uploaded content.
ANSWER FOLLOW-UP QUESTIONS: Provide detailed responses based on the stored file analysis.
PROVIDE DIRECT ANSWERS: Give complete answers to any questions from the uploaded files.
        """

    personalized_prompt = f"""
{SYSTEM_PROMPT}

STUDENT PROFILE:
- Name: {username}
- Level: {user_context[user_id]['level']}
- Learning: {user_context[user_id]['language']}
- Recent topic: {user_context[user_id]['last_topic']}
- {learning_profile}

WRITING REQUEST TYPE: {writing_request}
FILE REFERENCE DETECTED: {file_reference}
{writing_instructions}
{file_instructions}

FILE MEMORY CONTEXT (UPLOADED FILES ANALYSIS):
{file_memory_context}

CONVERSATION HISTORY:
{conversation_history}

CURRENT REQUEST from {username}: {user_text}

CRITICAL: Reference our previous conversation AND uploaded files. If this is about uploaded files, use the file memory above to provide specific, detailed answers. Build on what we've discussed and provide comprehensive assistance.

PROVIDE DIRECT ANSWERS: If the student is asking for quiz help, homework assistance, or answers to questions, provide COMPLETE SOLUTIONS with detailed explanations.

Provide detailed, practical help with file memory support:
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

async def process_document_message(update: Update, context: CallbackContext, user_id: str, username: str):
    """Process document uploads (PDF, etc.) with enhanced memory"""
    try:
        document = update.message.document
        file_name = document.file_name
        file_extension = file_name.split('.')[-1].lower() if file_name else "unknown"
        
        log_info(f"Document upload from {username}: {file_name}", user_id)
        
        # Check if file type is supported
        supported_types = ['pdf', 'jpg', 'jpeg', 'png']
        if file_extension not in supported_types:
            await update.message.reply_text(
                f"❌ <b>Unsupported File Type</b>\n\n"
                f"I can only process: PDF, JPG, PNG files.\n"
                f"Your file: {file_name}\n"
                f"Please convert your file to a supported format and try again.",
                parse_mode="HTML"
            )
            return
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            f"📄 <b>Processing your {file_extension.upper()} file...</b>\n\n"
            f"<i>Analyzing: {file_name}</i>\n"
            f"This may take a few moments...",
            parse_mode="HTML"
        )
        
        # Download the file
        file = await document.get_file()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
            temp_path = temp_file.name
            await file.download_to_drive(temp_path)
        
        # Get user's caption/message
        user_message = update.message.caption or "Can you help me understand this document?"
        
        # Process the file
        analysis_result = await process_uploaded_file(temp_path, file_extension, user_message, user_context.get(user_id))
        
        # Clean up temporary file
        os.unlink(temp_path)
        
        # Update user context with comprehensive file memory
        file_data = {
            "filename": file_name,
            "file_type": file_extension,
            "user_message": user_message,
            "analysis": analysis_result,
            "summary": analysis_result[:500] + "..." if len(analysis_result) > 500 else analysis_result
        }
        
        update_learning_profile(user_id, f"Uploaded {file_name}: {user_message}", analysis_result, file_uploaded=True, file_data=file_data)
        
        # Send the analysis result with memory reminder
        reply_html = make_user_friendly_html(analysis_result, f"Document: {file_name}", is_file=True)
        
        # Add memory reminder
        memory_note = "\n\n💾 <i>I've saved this analysis in memory! You can ask follow-up questions like:</i>\n• <i>'Explain page 3'</i>\n• <i>'Help with question 5'</i>\n• <i>'What was the main point?'</i>\n• <i>'Give me all the answers'</i>"
        full_reply = reply_html + memory_note
        
        await processing_msg.edit_text(full_reply, parse_mode="HTML")
        
    except Exception as e:
        log_info(f"Error processing document: {e}", user_id)
        await update.message.reply_text(
            "❌ <b>Error Processing File</b>\n\n"
            "I encountered an error while processing your file. Please try again with a different file or format.",
            parse_mode="HTML"
        )

async def process_photo_message(update: Update, context: CallbackContext, user_id: str, username: str):
    """Process photo uploads (images) with enhanced memory"""
    try:
        # Get the highest quality photo
        photo = update.message.photo[-1]
        
        log_info(f"Photo upload from {username}", user_id)
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            "🖼️ <b>Processing your image...</b>\n\n"
            "<i>Analyzing the content...</i>\n"
            "This may take a few moments...",
            parse_mode="HTML"
        )
        
        # Download the photo
        file = await photo.get_file()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_path = temp_file.name
            await file.download_to_drive(temp_path)
        
        # Get user's caption/message
        user_message = update.message.caption or "Can you help me understand this image?"
        
        # Process the image
        analysis_result = await process_uploaded_file(temp_path, "jpg", user_message, user_context.get(user_id))
        
        # Clean up temporary file
        os.unlink(temp_path)
        
        # Update user context with comprehensive file memory
        file_data = {
            "filename": f"image_{datetime.now().strftime('%H%M%S')}.jpg",
            "file_type": "jpg",
            "user_message": user_message,
            "analysis": analysis_result,
            "summary": analysis_result[:500] + "..." if len(analysis_result) > 500 else analysis_result
        }
        
        update_learning_profile(user_id, f"Uploaded image: {user_message}", analysis_result, file_uploaded=True, file_data=file_data)
        
        # Send the analysis result with memory reminder
        reply_html = make_user_friendly_html(analysis_result, "Image analysis", is_file=True)
        
        # Add memory reminder
        memory_note = "\n\n💾 <i>I've saved this analysis in memory! You can ask follow-up questions about this image later.</i>"
        full_reply = reply_html + memory_note
        
        await processing_msg.edit_text(full_reply, parse_mode="HTML")
        
    except Exception as e:
        log_info(f"Error processing photo: {e}", user_id)
        await update.message.reply_text(
            "❌ <b>Error Processing Image</b>\n\n"
            "I encountered an error while processing your image. Please try again with a different image.",
            parse_mode="HTML"
        )

async def handle_text_message(update: Update, context: CallbackContext):
    """Handle text messages"""
    user_text = update.message.text
    user_id = str(update.message.from_user.id)
    username = update.message.from_user.first_name or "Student"
    
    await process_text_message(update, context, user_text, user_id, username)

async def handle_document_message(update: Update, context: CallbackContext):
    """Handle document uploads"""
    user_id = str(update.message.from_user.id)
    username = update.message.from_user.first_name or "Student"
    
    await process_document_message(update, context, user_id, username)

async def handle_photo_message(update: Update, context: CallbackContext):
    """Handle photo uploads"""
    user_id = str(update.message.from_user.id)
    username = update.message.from_user.first_name or "Student"
    
    await process_photo_message(update, context, user_id, username)

async def error_handler(update: Update, context: CallbackContext):
    """Handle errors"""
    uid = "N/A"
    if update and update.effective_user:
        uid = update.effective_user.id
    
    error_msg = str(context.error) if context.error else "Unknown error"
    
    # Don't log conflict errors as they're normal during deployment
    if "Conflict" not in error_msg:
        logger.error(f"Error: {error_msg}", extra={"user_id": uid})

# -------------------------
# BOT HEALTH MONITORING
# -------------------------
def health_check():
    """Periodic health check to ensure bot is running"""
    while True:
        try:
            active_users = len(user_context)
            total_messages = sum(len(user["history"]) for user in user_context.values())
            total_files = sum(len(user["file_memory"]) for user in user_context.values())
            
            log_info(f"🤖 Health Check: {active_users} active users, {total_messages} messages, {total_files} files in memory", "SYSTEM")
            
            # Keep alive - log every 30 minutes
            time.sleep(18000)  # 30 minutes
            
        except Exception as e:
            log_info(f"Health check error: {e}", "SYSTEM")
            time.sleep(300)  # 5 minutes on error

# -------------------------
# ROBUST MAIN FUNCTION - OPTIMIZED FOR KOYEB
# -------------------------
def main():
    """Main function that ensures bot runs forever on Koyeb"""
    # 🔥 START KEEP-ALIVE SERVER
    keep_alive()
    
    log_info("🚀 Starting Comprehensive Language Tutor Bot on Koyeb...", "SYSTEM")
    log_info(f"🤖 Server running on port {port}", "SYSTEM")
    
    # Start health monitoring in background thread
    import threading
    health_thread = threading.Thread(target=health_check, daemon=True)
    health_thread.start()
    
    max_retries = 999  # Keep retrying forever on Koyeb
    retry_delay = 30
    
    for attempt in range(max_retries):
        try:
            # Build application
            application = Application.builder().token(TELEGRAM_TOKEN).build()
            
            # Add handlers for text, documents, and photos
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
            application.add_handler(MessageHandler(filters.Document.ALL, handle_document_message))
            application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
            application.add_error_handler(error_handler)
            
            log_info(f"🔄 Starting Telegram bot polling (attempt {attempt + 1})...", "SYSTEM")
            
            # Start polling
            application.run_polling(
                poll_interval=3.0,
                timeout=60,
                drop_pending_updates=True,
                allowed_updates=['message', 'edited_message']
            )
            
            log_info("✅ Bot is now running with enhanced file memory support!", "SYSTEM")
            
        except Exception as e:
            logger.error(f"❌ Bot crashed on attempt {attempt + 1}: {e}", extra={"user_id": "SYSTEM"})
            
            if attempt < max_retries - 1:
                log_info(f"🔄 Restarting bot in {retry_delay} seconds...", "SYSTEM")
                time.sleep(retry_delay)
            else:
                log_info("🔁 Maximum retries reached, but continuing anyway...", "SYSTEM")
                time.sleep(retry_delay)
                # Reset attempt counter to continue forever
                attempt = 0

if __name__ == "__main__":
    main()

