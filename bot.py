import os
import logging
import asyncio
import time
import tempfile
from datetime import datetime, timedelta
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
    # Use Gemini 2.5 Flash model for both text and vision
    model = genai.GenerativeModel("gemini-2.5-flash")
    vision_model = genai.GenerativeModel("gemini-2.5-flash")
    log_info("Gemini 1.5 Flash configured successfully with vision support", "N/A")
except Exception as e:
    log_info(f"Gemini configuration failed: {e}", "N/A")
    model = None
    vision_model = None

# -------------------------
# ENHANCED User context with COMPREHENSIVE FILE MEMORY AND QUIZ TRACKING
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
    "file_memory": [],  # Store all file analyses with metadata
    "quiz_scores": [],  # Track quiz performance
    "current_quiz": None,  # Track active quiz
    "total_quizzes_taken": 0,
    "average_score": 0.0,
    "study_streak": 0,
    "last_study_date": None,
    "flashcards": [],  # Vocabulary flashcards with spaced repetition
    "current_flashcard_session": None,  # Track active flashcard review session
    "daily_goals": {
        "quizzes_per_day": 1,
        "flashcards_per_day": 10,
        "study_minutes_per_day": 30
    },
    "today_progress": {
        "date": None,
        "quizzes_completed": 0,
        "flashcards_reviewed": 0,
        "study_minutes": 0
    },
    "study_groups": [],  # Groups the user belongs to
    "owned_groups": []   # Groups the user created
})

# Global study groups storage
study_groups = {}

# COMPREHENSIVE SYSTEM PROMPT with ENHANCED FILE MEMORY SUPPORT, QUIZ HELP, AND INTERACTIVE FEATURES
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

INTERACTIVE QUIZ GENERATION:
• Create custom quizzes based on topics, difficulty levels, and student needs
• Generate multiple choice, true/false, fill-in-the-blank, and short answer questions
• Provide immediate feedback and explanations for all answers
• Track quiz scores and learning progress
• Adapt quiz difficulty based on student performance
• Support quizzes in English, Khmer, and French

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
        elif file_type in ['docx', 'doc']:
            # For Word documents, we'd need python-docx library
            # For now, provide basic support note
            return f"I've received your Word document '{file_path.split('/')[-1]}'. For full document analysis, additional text extraction libraries would be needed. I can still help you with general questions about the document type and provide study guidance!"
        elif file_type in ['pptx', 'ppt']:
            # For PowerPoint, we'd need python-pptx library
            # For now, provide basic support note
            return f"I've received your PowerPoint presentation '{file_path.split('/')[-1]}'. For full slide analysis, additional presentation processing libraries would be needed. I can help you prepare presentations and provide speaking tips!"
        else:
            return f"I'm sorry, I cannot process {file_type} files yet. Please try with PDF, JPG, PNG, DOCX, or PPTX files."
        
        response = vision_model.generate_content([prompt, file_part])
        return response.text if hasattr(response, 'text') else "I couldn't analyze this file properly. Please try again."
        
    except Exception as e:
        log_info(f"Error processing file: {e}", "FILE_PROCESSING")
        return f"I encountered an error while processing your file: {str(e)}. Please try again with a different file or format."

# -------------------------
# INTERACTIVE QUIZ SYSTEM
# -------------------------
def generate_quiz(topic: str, level: str, language: str, num_questions: int = 5) -> dict:
    """Generate an interactive quiz based on topic, level, and language"""
    quiz_prompt = f"""
    Create an interactive quiz for {language} language learning.

    TOPIC: {topic}
    LEVEL: {level}
    NUMBER OF QUESTIONS: {num_questions}

    Create a quiz with {num_questions} questions. Mix different question types:
    - Multiple choice (3-4 options)
    - True/False
    - Fill-in-the-blank
    - Short answer

    Format each question as:
    Question Type: [type]
    Question: [question text]
    Options: [A] option1 [B] option2 [C] option3 [D] option4 (for multiple choice)
    Correct Answer: [answer]
    Explanation: [brief explanation]

    Make questions appropriate for {level} level students.
    Focus on {topic} related content.
    Provide clear, educational explanations.
    """

    try:
        if not model:
            return None

        response = model.generate_content(quiz_prompt)
        quiz_content = response.text if hasattr(response, 'text') else ""

        # Parse the quiz content into structured format
        questions = []
        lines = quiz_content.split('\n')
        current_question = {}

        for line in lines:
            line = line.strip()
            if line.startswith('Question Type:'):
                if current_question:
                    questions.append(current_question)
                current_question = {'type': line.replace('Question Type:', '').strip()}
            elif line.startswith('Question:'):
                current_question['question'] = line.replace('Question:', '').strip()
            elif line.startswith('Options:'):
                current_question['options'] = line.replace('Options:', '').strip()
            elif line.startswith('Correct Answer:'):
                current_question['answer'] = line.replace('Correct Answer:', '').strip()
            elif line.startswith('Explanation:'):
                current_question['explanation'] = line.replace('Explanation:', '').strip()

        if current_question:
            questions.append(current_question)

        return {
            'topic': topic,
            'level': level,
            'language': language,
            'questions': questions[:num_questions],  # Limit to requested number
            'total_questions': len(questions[:num_questions]),
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    except Exception as e:
        log_info(f"Error generating quiz: {e}", "QUIZ_SYSTEM")
        return None

def format_quiz_for_display(quiz: dict) -> str:
    """Format quiz for display to user"""
    if not quiz or not quiz.get('questions'):
        return "I couldn't generate a quiz right now. Please try again later."

    formatted = f"<b>🎯 {quiz['topic'].title()} Quiz</b>\n"
    formatted += f"<i>Level: {quiz['level'].title()} | Language: {quiz['language']}</i>\n\n"

    for i, question in enumerate(quiz['questions'], 1):
        formatted += f"<b>Question {i}:</b> {question['question']}\n"

        if question.get('options'):
            formatted += f"{question['options']}\n"

        formatted += "\n"

    formatted += "Reply with your answers (e.g., '1. A, 2. True, 3. [your answer]')\n"
    formatted += "I'll check them and provide feedback!"

    return formatted

def check_quiz_answers(quiz: dict, user_answers: list) -> dict:
    """Check user's quiz answers and return results"""
    if not quiz or not quiz.get('questions'):
        return {"error": "No quiz data available"}

    results = {
        'total_questions': len(quiz['questions']),
        'correct_answers': 0,
        'score_percentage': 0,
        'feedback': []
    }

    for i, question in enumerate(quiz['questions']):
        user_answer = user_answers[i] if i < len(user_answers) else ""
        correct = question.get('answer', '').lower().strip()
        user_ans = user_answer.lower().strip()

        is_correct = user_ans == correct

        if is_correct:
            results['correct_answers'] += 1

        feedback = {
            'question_num': i + 1,
            'question': question['question'],
            'user_answer': user_answer,
            'correct_answer': question.get('answer', ''),
            'is_correct': is_correct,
            'explanation': question.get('explanation', '')
        }

        results['feedback'].append(feedback)

    results['score_percentage'] = round((results['correct_answers'] / results['total_questions']) * 100, 1)

    return results

def format_quiz_results(results: dict) -> str:
    """Format quiz results for display"""
    formatted = f"<b>📊 Quiz Results</b>\n\n"
    formatted += f"<b>Score: {results['correct_answers']}/{results['total_questions']} ({results['score_percentage']}%)</b>\n\n"

    for feedback in results['feedback']:
        status = "✅" if feedback['is_correct'] else "❌"
        formatted += f"<b>Q{feedback['question_num']}:</b> {status}\n"
        formatted += f"Your answer: {feedback['user_answer']}\n"
        formatted += f"Correct: {feedback['correct_answer']}\n"

        if feedback.get('explanation'):
            formatted += f"💡 {feedback['explanation']}\n"

        formatted += "\n"

    # Add encouragement based on score
    if results['score_percentage'] >= 90:
        formatted += "🎉 Excellent work! You're mastering this topic!"
    elif results['score_percentage'] >= 70:
        formatted += "👍 Good job! Keep practicing to improve further."
    elif results['score_percentage'] >= 50:
        formatted += "📚 Not bad! Review the explanations and try again."
    else:
        formatted += "💪 Don't worry! Learning takes time. Let's review and try again."

    return formatted

def get_progress_statistics(user_id: str) -> str:
    """Generate comprehensive progress statistics for a user"""
    if user_id not in user_context:
        return "No progress data available yet. Start learning to see your statistics!"

    user_data = user_context[user_id]

    # Calculate days since first seen
    try:
        first_seen = datetime.strptime(user_data["first_seen"], "%Y-%m-%d %H:%M:%S")
        days_learning = (datetime.now() - first_seen).days + 1
    except:
        days_learning = 1

    # Quiz statistics
    quiz_scores = user_data.get("quiz_scores", [])
    total_quizzes = len(quiz_scores)
    avg_score = user_data.get("average_score", 0.0)

    # Recent quiz performance
    recent_scores = quiz_scores[-5:] if quiz_scores else []
    recent_avg = sum(score["score"] for score in recent_scores) / len(recent_scores) if recent_scores else 0

    # Learning profile
    level = user_data.get("level", "beginner").title()
    language = user_data.get("language", "English")
    goals = user_data.get("learning_goals", [])
    strengths = user_data.get("strengths", [])
    weak_areas = user_data.get("weak_areas", [])

    # File uploads
    total_files = len(user_data.get("file_memory", []))

    # Study streak (simplified - based on quiz activity)
    study_streak = user_data.get("study_streak", 0)

    # Format the statistics
    stats = f"<b>📈 Your Learning Progress Dashboard</b>\n\n"

    # Basic info
    stats += f"<b>👤 Profile:</b>\n"
    stats += f"• Level: {level}\n"
    stats += f"• Language: {language}\n"
    stats += f"• Learning for: {days_learning} days\n\n"

    # Quiz performance
    stats += f"<b>🎯 Quiz Performance:</b>\n"
    stats += f"• Total quizzes taken: {total_quizzes}\n"
    if total_quizzes > 0:
        stats += f"• Average score: {avg_score:.1f}%\n"
        stats += f"• Recent average (last 5): {recent_avg:.1f}%\n"

        # Performance trend
        if len(recent_scores) >= 2:
            trend = "📈 Improving" if recent_avg > avg_score else "📉 Needs focus"
            stats += f"• Trend: {trend}\n"
    stats += "\n"

    # Learning goals and areas
    if goals:
        stats += f"<b>🎯 Learning Goals:</b>\n"
        for goal in goals:
            stats += f"• {goal.title()}\n"
        stats += "\n"

    if strengths:
        stats += f"<b>💪 Strengths:</b>\n"
        for strength in strengths:
            stats += f"• {strength.title()}\n"
        stats += "\n"

    if weak_areas:
        stats += f"<b>📚 Areas to Focus On:</b>\n"
        for area in weak_areas:
            stats += f"• {area.title()}\n"
        stats += "\n"

    # Daily goals and progress
    daily_goals = user_data.get("daily_goals", {})
    today_progress = user_data.get("today_progress", {})

    stats += f"<b>🎯 Today's Goals & Progress:</b>\n"
    stats += f"• Quizzes: {today_progress.get('quizzes_completed', 0)}/{daily_goals.get('quizzes_per_day', 1)}\n"
    stats += f"• Flashcards: {today_progress.get('flashcards_reviewed', 0)}/{daily_goals.get('flashcards_per_day', 10)}\n"
    stats += f"• Study time: {today_progress.get('study_minutes', 0)}/{daily_goals.get('study_minutes_per_day', 30)} min\n\n"

    # Activity summary
    stats += f"<b>📊 Activity Summary:</b>\n"
    stats += f"• Files analyzed: {total_files}\n"
    stats += f"• Study streak: {study_streak} days\n"
    stats += f"• Total interactions: {len(user_data.get('history', []))}\n\n"

    # Encouragement
    if avg_score >= 80:
        stats += "🌟 <b>Excellent progress!</b> You're doing great!"
    elif avg_score >= 60:
        stats += "👍 <b>Good work!</b> Keep up the consistent practice!"
    elif total_quizzes > 0:
        stats += "💪 <b>Keep going!</b> Every quiz helps you improve!"
    else:
        stats += "🚀 <b>Ready to start?</b> Try taking a quiz to begin tracking your progress!"

    return stats

# -------------------------
# FLASHCARD SYSTEM FOR VOCABULARY BUILDING
# -------------------------
def create_flashcard(word: str, definition: str, language: str, level: str, examples: list = None) -> dict:
    """Create a new flashcard with spaced repetition data"""
    return {
        "word": word,
        "definition": definition,
        "language": language,
        "level": level,
        "examples": examples or [],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_reviewed": None,
        "next_review": datetime.now().strftime("%Y-%m-%d"),
        "ease_factor": 2.5,  # Spaced repetition ease factor
        "interval": 1,  # Days until next review
        "review_count": 0,
        "correct_streak": 0
    }

def generate_flashcards(topic: str, language: str, level: str, count: int = 10) -> list:
    """Generate flashcards for a specific topic using AI"""
    prompt = f"""
    Create {count} vocabulary flashcards for {language} language learning.

    TOPIC: {topic}
    LEVEL: {level}
    NUMBER OF CARDS: {count}

    For each flashcard, provide:
    Word: [vocabulary word]
    Definition: [clear definition in simple English]
    Examples: [2-3 example sentences using the word]

    Make sure the vocabulary is appropriate for {level} level students.
    Focus on useful {topic} related words.
    Provide practical, commonly used vocabulary.
    """

    try:
        if not model:
            return []

        response = model.generate_content(prompt)
        content = response.text if hasattr(response, 'text') else ""

        # Parse flashcards from response
        flashcards = []
        lines = content.split('\n')
        current_card = {}

        for line in lines:
            line = line.strip()
            if line.startswith('Word:'):
                if current_card and 'word' in current_card:
                    flashcards.append(create_flashcard(
                        current_card['word'],
                        current_card.get('definition', ''),
                        language,
                        level,
                        current_card.get('examples', [])
                    ))
                current_card = {'word': line.replace('Word:', '').strip()}
            elif line.startswith('Definition:'):
                current_card['definition'] = line.replace('Definition:', '').strip()
            elif line.startswith('Examples:') or line.startswith('Example:'):
                examples_text = line.replace('Examples:', '').replace('Example:', '').strip()
                # Split examples if multiple
                current_card['examples'] = [ex.strip() for ex in examples_text.split(';') if ex.strip()]

        # Add the last card
        if current_card and 'word' in current_card:
            flashcards.append(create_flashcard(
                current_card['word'],
                current_card.get('definition', ''),
                language,
                level,
                current_card.get('examples', [])
            ))

        return flashcards[:count]

    except Exception as e:
        log_info(f"Error generating flashcards: {e}", "FLASHCARD_SYSTEM")
        return []

def get_due_flashcards(user_id: str) -> list:
    """Get flashcards that are due for review"""
    if user_id not in user_context:
        return []

    flashcards = user_context[user_id]["flashcards"]
    today = datetime.now().strftime("%Y-%m-%d")

    due_cards = []
    for card in flashcards:
        next_review = card.get("next_review", today)
        if next_review <= today:
            due_cards.append(card)

    return due_cards

def update_flashcard_progress(card: dict, quality: int) -> dict:
    """Update flashcard using spaced repetition algorithm (simplified)"""
    # Quality: 0-5 (0=complete blackout, 5=perfect response)
    if quality < 3:
        # Incorrect - reset interval
        card["interval"] = 1
        card["correct_streak"] = 0
    else:
        # Correct - increase interval
        if card["correct_streak"] == 0:
            card["interval"] = 1
        elif card["correct_streak"] == 1:
            card["interval"] = 6
        else:
            card["interval"] = int(card["interval"] * card["ease_factor"])

        card["correct_streak"] += 1

    # Update ease factor
    card["ease_factor"] = max(1.3, card["ease_factor"] + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))

    # Set next review date
    next_review_date = datetime.now() + timedelta(days=card["interval"])
    card["next_review"] = next_review_date.strftime("%Y-%m-%d")
    card["last_reviewed"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    card["review_count"] += 1

    return card

def format_flashcard(card: dict) -> str:
    """Format a flashcard for display"""
    formatted = f"<b>📚 {card['word']}</b>\n\n"
    formatted += f"<i>Language: {card['language']} | Level: {card['level']}</i>\n\n"

    if card.get('examples'):
        formatted += "<b>Examples:</b>\n"
        for i, example in enumerate(card['examples'], 1):
            formatted += f"{i}. {example}\n"
        formatted += "\n"

    formatted += "Reply with:\n"
    formatted += "• 'show' - Reveal the definition\n"
    formatted += "• 'easy' - I knew this well\n"
    formatted += "• 'good' - I remembered with some thought\n"
    formatted += "• 'hard' - I struggled to remember\n"
    formatted += "• 'again' - Complete blackout"

    return formatted

def format_flashcard_answer(card: dict) -> str:
    """Format flashcard with answer revealed"""
    formatted = f"<b>📚 {card['word']}</b>\n\n"
    formatted += f"<b>Definition:</b> {card['definition']}\n\n"

    if card.get('examples'):
        formatted += "<b>Examples:</b>\n"
        for i, example in enumerate(card['examples'], 1):
            formatted += f"{i}. {example}\n"
        formatted += "\n"

    formatted += "How well did you know this?\n"
    formatted += "• '5' - Perfect, instant recall\n"
    formatted += "• '4' - Correct, but took time\n"
    formatted += "• '3' - Correct, with difficulty\n"
    formatted += "• '2' - Incorrect, but remembered when shown\n"
    formatted += "• '1' - Complete blackout"

    return formatted

# -------------------------
# STUDY GROUP SYSTEM
# -------------------------
def create_study_group(group_name: str, creator_id: str, description: str = "") -> dict:
    """Create a new study group"""
    group_id = f"group_{len(study_groups) + 1}"
    group = {
        "id": group_id,
        "name": group_name,
        "creator": creator_id,
        "description": description,
        "members": [creator_id],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_quizzes": 0,
        "total_flashcards": 0,
        "group_challenges": []
    }
    study_groups[group_id] = group
    return group

def join_study_group(user_id: str, group_id: str) -> bool:
    """Join a study group"""
    if group_id not in study_groups:
        return False

    if user_id not in study_groups[group_id]["members"]:
        study_groups[group_id]["members"].append(user_id)

    if group_id not in user_context[user_id]["study_groups"]:
        user_context[user_id]["study_groups"].append(group_id)

    return True

def get_group_leaderboard(group_id: str) -> list:
    """Get leaderboard for a study group"""
    if group_id not in study_groups:
        return []

    members = study_groups[group_id]["members"]
    leaderboard = []

    for member_id in members:
        if member_id in user_context:
            user_data = user_context[member_id]
            leaderboard.append({
                "user_id": member_id,
                "name": f"Student {member_id[-4:]}",  # Simple anonymized name
                "quizzes_completed": user_data.get("total_quizzes_taken", 0),
                "average_score": user_data.get("average_score", 0.0),
                "study_streak": user_data.get("study_streak", 0),
                "flashcards_count": len(user_data.get("flashcards", []))
            })

    # Sort by average score, then by quizzes completed
    leaderboard.sort(key=lambda x: (x["average_score"], x["quizzes_completed"]), reverse=True)
    return leaderboard

def format_group_info(group: dict) -> str:
    """Format study group information"""
    members_count = len(group["members"])
    created_date = datetime.strptime(group["created_at"], "%Y-%m-%d %H:%M:%S").strftime("%B %d, %Y")

    info = f"<b>📚 {group['name']}</b>\n\n"
    if group.get("description"):
        info += f"<i>{group['description']}</i>\n\n"

    info += f"👥 <b>Members:</b> {members_count}\n"
    info += f"📅 <b>Created:</b> {created_date}\n"
    info += f"🎯 <b>Group Quizzes:</b> {group['total_quizzes']}\n"
    info += f"🃏 <b>Group Flashcards:</b> {group['total_flashcards']}\n\n"

    # Show top 3 members
    leaderboard = get_group_leaderboard(group["id"])[:3]
    if leaderboard:
        info += "<b>🏆 Top Members:</b>\n"
        for i, member in enumerate(leaderboard, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
            info += f"{medal} {member['name']}: {member['average_score']:.1f}% avg\n"
        info += "\n"

    return info

# -------------------------
# PERSONALIZED LEARNING PATHS
# -------------------------
def generate_learning_path(user_id: str) -> str:
    """Generate a personalized learning path based on user progress and goals"""
    if user_id not in user_context:
        return "Please start learning first so I can create a personalized path for you!"

    user_data = user_context[user_id]

    # Analyze user profile
    level = user_data.get("level", "beginner")
    language = user_data.get("language", "English")
    goals = user_data.get("learning_goals", [])
    weak_areas = user_data.get("weak_areas", [])
    strengths = user_data.get("strengths", [])

    # Quiz performance analysis
    quiz_scores = user_data.get("quiz_scores", [])
    avg_score = user_data.get("average_score", 0.0)
    total_quizzes = len(quiz_scores)

    # Flashcard progress
    flashcards = user_data.get("flashcards", [])
    total_flashcards = len(flashcards)

    # Study patterns
    study_streak = user_data.get("study_streak", 0)

    # Generate personalized recommendations
    path = f"<b>🎯 Your Personalized Learning Path</b>\n\n"
    path += f"<b>👤 Profile:</b> {level.title()} {language} learner\n\n"

    # Current assessment
    path += "<b>📊 Current Assessment:</b>\n"
    if total_quizzes > 0:
        path += f"• Quiz average: {avg_score:.1f}%\n"
    else:
        path += "• No quiz data yet - start with quizzes!\n"

    path += f"• Vocabulary cards: {total_flashcards}\n"
    path += f"• Study streak: {study_streak} days\n\n"

    # Weekly learning plan
    path += "<b>📅 Weekly Learning Plan:</b>\n\n"

    # Day 1-2: Focus on weaknesses
    if weak_areas:
        path += "<b>📚 Days 1-2: Address Weak Areas</b>\n"
        for area in weak_areas[:2]:
            path += f"• Practice {area} with targeted exercises\n"
        path += "• Take 2 quizzes on weak topics\n"
        path += "• Review 10 flashcards daily\n\n"
    else:
        path += "<b>📚 Days 1-2: Build Foundations</b>\n"
        path += "• Take introductory quizzes\n"
        path += "• Learn basic vocabulary (20 cards)\n"
        path += "• Practice basic grammar\n\n"

    # Day 3-4: Build on strengths
    if strengths:
        path += "<b>💪 Days 3-4: Leverage Strengths</b>\n"
        for strength in strengths[:2]:
            path += f"• Advanced practice in {strength}\n"
        path += "• Create content using your strengths\n"
        path += "• Help others with your strong areas\n\n"
    else:
        path += "<b>💪 Days 3-4: Skill Building</b>\n"
        path += "• Practice writing and speaking\n"
        path += "• Learn intermediate vocabulary\n"
        path += "• Work on comprehensive exercises\n\n"

    # Day 5-7: Mixed practice and review
    path += "<b>🔄 Days 5-7: Mixed Practice & Review</b>\n"
    path += "• Review all weak areas\n"
    path += "• Take comprehensive quizzes\n"
    path += "• Practice with uploaded materials\n"
    path += "• Join or create study groups\n\n"

    # Long-term goals
    if goals:
        path += "<b>🎯 Long-term Goals Focus:</b>\n"
        for goal in goals:
            path += f"• {goal.title()}: Weekly dedicated practice\n"
        path += "\n"

    # Progress milestones
    path += "<b>🏆 Progress Milestones:</b>\n"
    path += "• <b>Week 1:</b> Complete 5 quizzes, 50 flashcards\n"
    path += "• <b>Week 2:</b> Improve average score by 10%\n"
    path += "• <b>Week 4:</b> Master 2 weak areas\n"
    path += "• <b>Month 1:</b> Reach 100 flashcards, 20 quizzes\n\n"

    # Study tips
    path += "<b>💡 Study Tips:</b>\n"
    path += "• Study daily to maintain your streak\n"
    path += "• Focus on understanding, not just memorization\n"
    path += "• Use spaced repetition for vocabulary\n"
    path += "• Practice with real-world applications\n"
    path += "• Join study groups for motivation\n\n"

    # Next steps
    path += "<b>🚀 Next Steps:</b>\n"
    if total_quizzes == 0:
        path += "• Start with 'Create a quiz about [topic]'\n"
    if total_flashcards < 20:
        path += "• Build vocabulary: 'Create flashcards for [topic]'\n"
    if not goals:
        path += "• Set goals by asking about specific skills\n"
    path += "• Check progress with 'Show my progress'\n"
    path += "• Join others with 'Create group [name]'"

    return path

# -------------------------
# MULTIMEDIA CONTENT SUPPORT
# -------------------------
def get_multimedia_resources(topic: str, language: str, content_type: str = "all") -> str:
    """Provide multimedia learning resources and links"""
    resources = f"<b>🎬 Multimedia Resources for {topic.title()}</b>\n\n"

    # YouTube educational channels and playlists
    if content_type in ["all", "video"]:
        resources += "<b>📺 Educational Videos:</b>\n"
        if language.lower() == "english":
            if "grammar" in topic.lower():
                resources += "• <a href='https://www.youtube.com/results?search_query=english+grammar+explained'>English Grammar Explained</a>\n"
                resources += "• <a href='https://www.youtube.com/user/EnglishLessonswithAdam'>English with Adam</a>\n"
            elif "vocabulary" in topic.lower():
                resources += "• <a href='https://www.youtube.com/results?search_query=english+vocabulary+building'>Vocabulary Building Videos</a>\n"
                resources += "• <a href='https://www.youtube.com/user/TED-Ed'>TED-Ed Vocabulary</a>\n"
            elif "pronunciation" in topic.lower():
                resources += "• <a href='https://www.youtube.com/results?search_query=english+pronunciation+practice'>Pronunciation Practice</a>\n"
                resources += "• <a href='https://www.youtube.com/user/Rachel'sEnglish'>Rachel's English</a>\n"
            else:
                resources += "• <a href='https://www.youtube.com/results?search_query=learn+english+conversation'>English Conversation Practice</a>\n"
                resources += "• <a href='https://www.youtube.com/user/EnglishAnyone'>English Anyone</a>\n"
        elif language.lower() == "french":
            resources += "• <a href='https://www.youtube.com/results?search_query=apprendre+le+français'>Learn French Videos</a>\n"
            resources += "• <a href='https://www.youtube.com/user/FrenchPod101'>FrenchPod101</a>\n"
        elif language.lower() == "khmer":
            resources += "• <a href='https://www.youtube.com/results?search_query=learn+khmer+language'>Khmer Language Learning</a>\n"
            resources += "• <a href='https://www.youtube.com/results?search_query=khmer+alphabet'>Khmer Alphabet Videos</a>\n"
        resources += "\n"

    # Audio resources
    if content_type in ["all", "audio"]:
        resources += "<b>🎧 Audio Learning Resources:</b>\n"
        if language.lower() == "english":
            resources += "• <a href='https://www.bbc.co.uk/learningenglish'>BBC Learning English</a> - Podcasts & audio lessons\n"
            resources += "• <a href='https://www.eslpod.com'>ESL Pod</a> - English learning podcasts\n"
        elif language.lower() == "french":
            resources += "• <a href='https://www.france24.com/en/tag/learning-french/'>France 24 Learning French</a>\n"
            resources += "• <a href='https://coffeebreaklanguages.com/french/'>Coffee Break French</a> - Audio lessons\n"
        elif language.lower() == "khmer":
            resources += "• <a href='https://www.bbc.co.uk/languages/other/khmer/'>BBC Khmer Service</a>\n"
        resources += "\n"

    # Interactive websites
    if content_type in ["all", "interactive"]:
        resources += "<b>💻 Interactive Learning Websites:</b>\n"
        resources += "• <a href='https://www.duolingo.com'>Duolingo</a> - Gamified language learning\n"
        resources += "• <a href='https://www.memrise.com'>Memrise</a> - Vocabulary and phrases\n"
        resources += "• <a href='https://www.busuu.com'>Busuu</a> - Community-based learning\n"
        if language.lower() == "english":
            resources += "• <a href='https://www.englishgrammar101.com'>English Grammar 101</a> - Interactive exercises\n"
        resources += "\n"

    # Documentaries and cultural content
    if content_type in ["all", "cultural"]:
        resources += "<b>🎭 Cultural & Immersive Content:</b>\n"
        if language.lower() == "english":
            resources += "• <a href='https://www.netflix.com'>Netflix</a> - Watch shows with English subtitles\n"
            resources += "• <a href='https://www.bbc.co.uk/iplayer'>BBC iPlayer</a> - British English content\n"
        elif language.lower() == "french":
            resources += "• <a href='https://www.netflix.com'>Netflix</a> - French films and series\n"
            resources += "• <a href='https://www.france.tv'>France.tv</a> - French public television\n"
        elif language.lower() == "khmer":
            resources += "• <a href='https://www.youtube.com/results?search_query=khmer+movies'>Khmer Movies & Documentaries</a>\n"
        resources += "\n"

    # Study tips
    resources += "<b>💡 Multimedia Learning Tips:</b>\n"
    resources += "• Watch videos at 0.75x speed for better comprehension\n"
    resources += "• Use subtitles in your target language first, then native language\n"
    resources += "• Listen to podcasts during commutes or chores\n"
    resources += "• Practice speaking along with video content\n"
    resources += "• Take notes while watching educational videos\n\n"

    resources += "<b>🔗 Additional Resources:</b>\n"
    resources += "• <a href='https://www.opensubtitles.org'>OpenSubtitles</a> - Find subtitles for movies\n"
    resources += "• <a href='https://www.ted.com/talks'>TED Talks</a> - Inspiring talks in multiple languages\n"
    resources += "• <a href='https://www.coursera.org'>Coursera</a> - Free language courses from universities\n"

    return resources

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
        "is_quiz_generation": any(phrase in text_lower for phrase in ["create quiz", "generate quiz", "make quiz", "quiz me", "take quiz", "practice quiz"]),
        "is_quiz_answer_check": any(phrase in text_lower for phrase in ["check answers", "my answers", "quiz answers"]) and any(char.isdigit() for char in user_text),
        "is_progress_stats": any(phrase in text_lower for phrase in ["my progress", "progress stats", "statistics", "dashboard", "my stats", "learning progress", "show stats"]),
        "is_flashcard_generation": any(phrase in text_lower for phrase in ["create flashcards", "generate flashcards", "make flashcards", "flashcards for", "vocabulary cards"]),
        "is_flashcard_review": any(phrase in text_lower for phrase in ["review flashcards", "practice flashcards", "study cards", "flashcard review", "review vocab"]),
        "is_flashcard_answer": any(word in text_lower for word in ["show", "easy", "good", "hard", "again"]) and len(text_lower.split()) == 1,
        "is_create_group": any(phrase in text_lower for phrase in ["create group", "make group", "new group", "start group"]),
        "is_join_group": any(phrase in text_lower for phrase in ["join group", "find group", "group list", "available groups"]),
        "is_group_info": any(phrase in text_lower for phrase in ["my groups", "group info", "group stats", "group leaderboard"]),
        "is_learning_path": any(phrase in text_lower for phrase in ["learning path", "study plan", "personalized plan", "my plan", "learning plan", "study path"]),
        "is_multimedia": any(phrase in text_lower for phrase in ["multimedia resources", "video resources", "audio resources", "learning videos", "educational videos", "watch videos", "listen audio", "podcasts", "online resources"]),
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
• <b>Word Documents</b> - Essays, reports, study guides (DOCX, DOC)
• <b>PowerPoint Presentations</b> - Slides, lecture notes (PPTX, PPT)
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

<u>🧠 INTERACTIVE QUIZZES:</u>
• <b>Custom Quiz Generation</b> - Create personalized quizzes on any topic
• <b>Progress Tracking</b> - Track your quiz scores and improvement
• <b>Adaptive Learning</b> - Quizzes adjust to your skill level
• <b>Instant Feedback</b> - Get explanations for every answer

<u>📚 FLASHCARD SYSTEM:</u>
• <b>Spaced Repetition</b> - Smart vocabulary learning with optimal timing
• <b>Custom Decks</b> - Generate flashcards for any topic or subject
• <b>Progress Tracking</b> - Monitor your vocabulary improvement
• <b>Multiple Languages</b> - Support for English, Khmer, and French

<u>👥 STUDY GROUPS:</u>
• <b>Collaborative Learning</b> - Join or create study groups with friends
• <b>Group Leaderboards</b> - Compete with group members
• <b>Shared Progress</b> - Track collective improvement
• <b>Motivational Challenges</b> - Group study challenges and goals

<u>🧭 PERSONALIZED LEARNING PATHS:</u>
• <b>Custom Study Plans</b> - AI-generated learning paths based on your progress
• <b>Goal-Oriented Learning</b> - Structured plans to achieve your language goals
• <b>Adaptive Recommendations</b> - Plans that adjust to your strengths and weaknesses
• <b>Progress Milestones</b> - Clear checkpoints and achievements

<u>🎬 MULTIMEDIA LEARNING RESOURCES:</u>
• <b>Educational Videos</b> - YouTube channels and learning playlists
• <b>Audio Lessons</b> - Podcasts and audio learning resources
• <b>Interactive Websites</b> - Online platforms for practice
• <b>Cultural Content</b> - Immersive videos and documentaries

<u>🎤 PRONUNCIATION PRACTICE:</u>
• <b>Voice Message Analysis</b> - Send voice messages for pronunciation feedback
• <b>Phonetic Guidance</b> - Learn correct sound patterns
• <b>Language-Specific Tips</b> - English, Khmer, and French pronunciation
• <b>Practice Exercises</b> - Targeted pronunciation drills

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
• "Create a quiz about grammar" (I'll generate a custom quiz!)
• "Quiz me on vocabulary" (Interactive quizzes with instant feedback)
• "Generate a practice test on verb tenses"
• "Show my progress" (View your learning statistics and dashboard)
• "My stats" (See quiz scores, goals, and improvement tracking)
• "Create flashcards for business English" (Generate vocabulary cards)
• "Review flashcards" (Practice with spaced repetition)
• "Create group English Study Club" (Start a collaborative study group)
• "Join group" (Find and join existing study groups)
• "My groups" (View your study groups and leaderboards)
• "Show my learning path" (Get a personalized study plan)
• "My study plan" (AI-generated learning recommendations)
• "Show multimedia resources" (Get videos, podcasts, and online learning materials)
• "Educational videos for grammar" (Find relevant learning videos)
• Send a voice message (Get pronunciation feedback and practice tips)
• "How do I pronounce [word]?" (Learn correct pronunciation)

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
            "file_memory": [],
            "quiz_scores": [],
            "current_quiz": None,
            "total_quizzes_taken": 0,
            "average_score": 0.0,
            "study_streak": 0,
            "last_study_date": None,
            "flashcards": [],
            "current_flashcard_session": None,
            "daily_goals": {
                "quizzes_per_day": 1,
                "flashcards_per_day": 10,
                "study_minutes_per_day": 30
            },
            "today_progress": {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "quizzes_completed": 0,
                "flashcards_reviewed": 0,
                "study_minutes": 0
            }
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
            "file_memory": [],
            "quiz_scores": [],
            "current_quiz": None,
            "total_quizzes_taken": 0,
            "average_score": 0.0,
            "study_streak": 0,
            "last_study_date": None,
            "flashcards": [],
            "current_flashcard_session": None,
            "daily_goals": {
                "quizzes_per_day": 1,
                "flashcards_per_day": 10,
                "study_minutes_per_day": 30
            },
            "today_progress": {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "quizzes_completed": 0,
                "flashcards_reviewed": 0,
                "study_minutes": 0
            }
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

    # Handle quiz generation and checking
    if writing_request["is_quiz_generation"]:
        # Extract topic from user text
        topic = "general"
        if "grammar" in user_text.lower():
            topic = "grammar"
        elif "vocabulary" in user_text.lower() or "vocab" in user_text.lower():
            topic = "vocabulary"
        elif "tense" in user_text.lower():
            topic = "verb tenses"
        elif any(word in user_text.lower() for word in ["reading", "comprehension"]):
            topic = "reading comprehension"

        # Generate quiz
        quiz = generate_quiz(
            topic=topic,
            level=user_context[user_id]["level"],
            language=user_context[user_id]["language"],
            num_questions=5
        )

        if quiz:
            user_context[user_id]["current_quiz"] = quiz
            quiz_text = format_quiz_for_display(quiz)
            await update.message.reply_text(quiz_text, parse_mode="HTML")
            return
        else:
            await update.message.reply_text("❌ I couldn't generate a quiz right now. Please try again later.", parse_mode="HTML")
            return

    elif writing_request["is_quiz_answer_check"] and user_context[user_id]["current_quiz"]:
        # Parse user answers
        user_answers = []
        lines = user_text.split('\n')
        for line in lines:
            line = line.strip()
            if '.' in line:
                # Extract answer after the dot
                parts = line.split('.', 1)
                if len(parts) > 1:
                    answer = parts[1].strip()
                    user_answers.append(answer)

        if user_answers:
            results = check_quiz_answers(user_context[user_id]["current_quiz"], user_answers)

            # Update user stats
            user_context[user_id]["quiz_scores"].append({
                "score": results["score_percentage"],
                "total_questions": results["total_questions"],
                "correct_answers": results["correct_answers"],
                "topic": user_context[user_id]["current_quiz"]["topic"],
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            # Update average score
            total_scores = sum(score["score"] for score in user_context[user_id]["quiz_scores"])
            user_context[user_id]["average_score"] = round(total_scores / len(user_context[user_id]["quiz_scores"]), 1)
            user_context[user_id]["total_quizzes_taken"] = len(user_context[user_id]["quiz_scores"])

            # Update study streak and daily progress
            today = datetime.now().strftime("%Y-%m-%d")
            last_study = user_context[user_id].get("last_study_date")

            if last_study == today:
                # Already studied today, streak continues
                pass
            elif last_study == (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"):
                # Studied yesterday, increment streak
                user_context[user_id]["study_streak"] += 1
            else:
                # Streak broken or first day, reset to 1
                user_context[user_id]["study_streak"] = 1

            user_context[user_id]["last_study_date"] = today

            # Update daily progress
            if user_context[user_id]["today_progress"]["date"] != today:
                # Reset daily progress for new day
                user_context[user_id]["today_progress"] = {
                    "date": today,
                    "quizzes_completed": 0,
                    "flashcards_reviewed": 0,
                    "study_minutes": 0
                }

            user_context[user_id]["today_progress"]["quizzes_completed"] += 1
            # Estimate study time (5 minutes per quiz)
            user_context[user_id]["today_progress"]["study_minutes"] += 5

            # Clear current quiz
            user_context[user_id]["current_quiz"] = None

            results_text = format_quiz_results(results)
            await update.message.reply_text(results_text, parse_mode="HTML")
            return
        else:
            await update.message.reply_text("❌ I couldn't parse your answers. Please format them like:\n1. A\n2. True\n3. [your answer]", parse_mode="HTML")
            return

    elif writing_request["is_progress_stats"]:
        # Show progress statistics
        stats = get_progress_statistics(user_id)
        await update.message.reply_text(stats, parse_mode="HTML")
        return

    elif writing_request["is_flashcard_generation"]:
        # Generate flashcards
        topic = "general vocabulary"
        if "business" in user_text.lower():
            topic = "business"
        elif "academic" in user_text.lower():
            topic = "academic"
        elif "everyday" in user_text.lower():
            topic = "everyday conversation"
        elif "technical" in user_text.lower():
            topic = "technical"

        flashcards = generate_flashcards(
            topic=topic,
            language=user_context[user_id]["language"],
            level=user_context[user_id]["level"],
            count=10
        )

        if flashcards:
            # Add flashcards to user context
            user_context[user_id]["flashcards"].extend(flashcards)

            response = f"<b>📚 Generated {len(flashcards)} Flashcards</b>\n\n"
            response += f"<i>Topic: {topic.title()}</i>\n"
            response += f"<i>Language: {user_context[user_id]['language']}</i>\n\n"
            response += "Your flashcards have been added to your study deck!\n\n"
            response += "💡 <b>Commands:</b>\n"
            response += "• 'review flashcards' - Start reviewing due cards\n"
            response += "• 'practice flashcards' - Review all cards\n\n"
            response += f"You now have {len(user_context[user_id]['flashcards'])} flashcards in your deck."

            await update.message.reply_text(response, parse_mode="HTML")
            return
        else:
            await update.message.reply_text("❌ I couldn't generate flashcards right now. Please try again later.", parse_mode="HTML")
            return

    elif writing_request["is_flashcard_review"] or (user_context[user_id].get("current_flashcard_session") and writing_request["is_flashcard_answer"]):
        # Handle flashcard review session
        if not user_context[user_id].get("current_flashcard_session"):
            # Start new review session
            due_cards = get_due_flashcards(user_id)
            if not due_cards:
                await update.message.reply_text("🎉 <b>All caught up!</b>\n\nYou have no flashcards due for review right now. Great job staying on top of your studies!", parse_mode="HTML")
                return

            user_context[user_id]["current_flashcard_session"] = {
                "cards": due_cards,
                "current_index": 0,
                "showing_answer": False
            }

        session = user_context[user_id]["current_flashcard_session"]
        current_card = session["cards"][session["current_index"]]

        if writing_request["is_flashcard_answer"]:
            # Process answer quality rating
            quality_map = {
                "5": 5, "easy": 5, "perfect": 5,
                "4": 4, "good": 4,
                "3": 3, "hard": 3,
                "2": 2, "again": 1, "1": 1
            }

            quality = quality_map.get(user_text.lower().strip(), 3)

            # Update card progress
            updated_card = update_flashcard_progress(current_card.copy(), quality)

            # Update the card in user's flashcard list
            for i, card in enumerate(user_context[user_id]["flashcards"]):
                if card["word"] == current_card["word"] and card["created_at"] == current_card["created_at"]:
                    user_context[user_id]["flashcards"][i] = updated_card
                    break

            session["current_index"] += 1

        # Check if session is complete
        if session["current_index"] >= len(session["cards"]):
            completed_count = len(session["cards"])
            user_context[user_id]["current_flashcard_session"] = None

            # Update daily progress
            today = datetime.now().strftime("%Y-%m-%d")
            if user_context[user_id]["today_progress"]["date"] != today:
                user_context[user_id]["today_progress"] = {
                    "date": today,
                    "quizzes_completed": 0,
                    "flashcards_reviewed": 0,
                    "study_minutes": 0
                }

            user_context[user_id]["today_progress"]["flashcards_reviewed"] += completed_count
            # Estimate study time (1 minute per flashcard)
            user_context[user_id]["today_progress"]["study_minutes"] += completed_count

            response = f"<b>🎯 Review Session Complete!</b>\n\n"
            response += f"You reviewed {completed_count} flashcards.\n\n"
            response += "💪 <b>Keep up the great work!</b>\n"
            response += "Come back tomorrow for more reviews."

            await update.message.reply_text(response, parse_mode="HTML")
            return

        # Show next card
        current_card = session["cards"][session["current_index"]]
        card_text = format_flashcard(current_card)
        progress = f"Card {session['current_index'] + 1} of {len(session['cards'])}"

        full_response = f"<b>🧠 Flashcard Review</b>\n<i>{progress}</i>\n\n{card_text}"
        await update.message.reply_text(full_response, parse_mode="HTML")
        return

    elif writing_request["is_create_group"]:
        # Extract group name from user text
        group_name = "My Study Group"
        if "group" in user_text.lower():
            # Try to extract name after "group"
            parts = user_text.lower().split("group")
            if len(parts) > 1 and parts[1].strip():
                group_name = parts[1].strip().title()

        # Create the group
        group = create_study_group(group_name, user_id, f"Study group created by {username}")
        user_context[user_id]["owned_groups"].append(group["id"])

        response = f"<b>🎉 Study Group Created!</b>\n\n"
        response += f"<b>Group Name:</b> {group['name']}\n"
        response += f"<b>Group ID:</b> {group['id']}\n\n"
        response += "Share this Group ID with friends so they can join!\n\n"
        response += "<b>Commands:</b>\n"
        response += "• 'my groups' - View your groups\n"
        response += "• 'group leaderboard' - See rankings"

        await update.message.reply_text(response, parse_mode="HTML")
        return

    elif writing_request["is_join_group"]:
        # Show available groups
        if not study_groups:
            response = "<b>📚 No Study Groups Available</b>\n\n"
            response += "Be the first to create one!\n"
            response += "Say 'create group [name]' to start your own study group."
        else:
            response = "<b>📚 Available Study Groups</b>\n\n"
            for group_id, group in study_groups.items():
                response += f"<b>{group['name']}</b>\n"
                response += f"ID: {group_id}\n"
                response += f"Members: {len(group['members'])}\n"
                if group.get("description"):
                    response += f"📝 {group['description']}\n"
                response += "\n"

            response += "<b>To join a group, say:</b>\n"
            response += "'join group [group_id]'"

        await update.message.reply_text(response, parse_mode="HTML")
        return

    elif writing_request["is_group_info"]:
        # Show user's groups
        user_groups = user_context[user_id]["study_groups"]
        owned_groups = user_context[user_id]["owned_groups"]

        if not user_groups and not owned_groups:
            response = "<b>📚 You're not in any study groups yet!</b>\n\n"
            response += "<b>Join existing groups:</b>\n"
            response += "• Say 'join group' to see available groups\n\n"
            response += "<b>Or create your own:</b>\n"
            response += "• Say 'create group [name]' to start a new group"
        else:
            response = "<b>📚 Your Study Groups</b>\n\n"

            # Show owned groups
            if owned_groups:
                response += "<b>👑 Groups You Created:</b>\n"
                for group_id in owned_groups:
                    if group_id in study_groups:
                        group = study_groups[group_id]
                        response += f"• <b>{group['name']}</b> ({len(group['members'])} members)\n"
                response += "\n"

            # Show joined groups
            joined_groups = [gid for gid in user_groups if gid not in owned_groups]
            if joined_groups:
                response += "<b>👥 Groups You Joined:</b>\n"
                for group_id in joined_groups:
                    if group_id in study_groups:
                        group = study_groups[group_id]
                        response += f"• <b>{group['name']}</b> ({len(group['members'])} members)\n"
                response += "\n"

            # Show leaderboard for first group
            all_user_groups = owned_groups + joined_groups
            if all_user_groups and all_user_groups[0] in study_groups:
                group = study_groups[all_user_groups[0]]
                leaderboard = get_group_leaderboard(group["id"])

                if leaderboard:
                    response += f"<b>🏆 {group['name']} Leaderboard:</b>\n"
                    for i, member in enumerate(leaderboard[:5], 1):
                        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                        response += f"{medal} {member['name']}: {member['average_score']:.1f}% avg\n"

        await update.message.reply_text(response, parse_mode="HTML")
        return

    elif writing_request["is_learning_path"]:
        # Generate personalized learning path
        learning_path = generate_learning_path(user_id)
        await update.message.reply_text(learning_path, parse_mode="HTML")
        return

    elif writing_request["is_multimedia"]:
        # Provide multimedia resources
        topic = "general language learning"
        content_type = "all"

        # Extract topic from user text
        if "grammar" in user_text.lower():
            topic = "grammar"
        elif "vocabulary" in user_text.lower() or "vocab" in user_text.lower():
            topic = "vocabulary"
        elif "pronunciation" in user_text.lower():
            topic = "pronunciation"
        elif "conversation" in user_text.lower():
            topic = "conversation"
        elif "video" in user_text.lower():
            content_type = "video"
        elif "audio" in user_text.lower() or "podcast" in user_text.lower():
            content_type = "audio"

        language = user_context[user_id]["language"]
        resources = get_multimedia_resources(topic, language, content_type)
        await update.message.reply_text(resources, parse_mode="HTML", disable_web_page_preview=True)
        return

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
        supported_types = ['pdf', 'jpg', 'jpeg', 'png', 'docx', 'pptx', 'doc', 'ppt']
        if file_extension not in supported_types:
            await update.message.reply_text(
                f"❌ <b>Unsupported File Type</b>\n\n"
                f"I can process: PDF, JPG, PNG, DOCX, PPTX files.\n"
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

async def handle_voice_message(update: Update, context: CallbackContext):
    """Handle voice message uploads for pronunciation practice"""
    user_id = str(update.message.from_user.id)
    username = update.message.from_user.first_name or "Student"

    try:
        voice = update.message.voice

        # Send processing message
        processing_msg = await update.message.reply_text(
            "🎤 <b>Processing your voice message...</b>\n\n"
            "<i>Analyzing pronunciation...</i>\n"
            "This may take a few moments...",
            parse_mode="HTML"
        )

        # Download the voice file
        file = await voice.get_file()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_file:
            temp_path = temp_file.name
            await file.download_to_drive(temp_path)

        # For now, provide basic feedback (would need speech-to-text API integration)
        feedback = """
<b>🎤 Pronunciation Practice</b>

I've received your voice message! For full pronunciation analysis, I would need additional speech recognition integration.

<b>What I can help with:</b>
• <b>Phonetic guidance</b> - Learn correct pronunciation patterns
• <b>Common mistakes</b> - Address frequent pronunciation issues
• <b>Practice exercises</b> - Targeted pronunciation drills
• <b>Language-specific tips</b> - English, Khmer, and French pronunciation

<b>Try these commands:</b>
• "How do I pronounce [word]?"
• "Practice English vowels"
• "French pronunciation tips"
• "Khmer consonant sounds"

<i>Note: Full voice analysis requires speech-to-text API integration for real-time feedback.</i>
"""

        await processing_msg.edit_text(feedback, parse_mode="HTML")

        # Clean up temporary file
        os.unlink(temp_path)

    except Exception as e:
        log_info(f"Error processing voice: {e}", user_id)
        await update.message.reply_text(
            "❌ <b>Error Processing Voice Message</b>\n\n"
            "I encountered an error while processing your voice message. Please try again.",
            parse_mode="HTML"
        )

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
            
            # Add handlers for text, documents, photos, and voice messages
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
            application.add_handler(MessageHandler(filters.Document.ALL, handle_document_message))
            application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
            application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
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

