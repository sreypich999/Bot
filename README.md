# Comprehensive Language Tutor Bot

![Bot Image](https://github.com/sreypich999/Bot/blob/main/photo_2025-10-22_23-21-46.jpg)

A powerful Telegram bot designed to help students master English, Khmer, and French through interactive learning, comprehensive writing assistance, and advanced file upload support with complete memory retention.

## 🌟 Features

### 📚 Language Learning Support
- **Multi-language tutoring**: English, Khmer (កម្ពុជា), and French (Français)
- **All skill levels**: Beginner, Intermediate, and Advanced learners
- **Comprehensive grammar checking** with detailed error analysis and corrections
- **Vocabulary building** for academic, business, and technical terms
- **Translation services** between all supported languages

### ✍️ Writing Assistance
- **Essay writing** for all levels and types (Narrative, Descriptive, Expository, Persuasive, Argumentative)
- **Script writing** for presentations, speeches, and dialogues
- **Grammar correction** with style and tone improvements
- **Thesis development** and paragraph structuring
- **Outline creation** for organized writing projects

### 📁 Advanced File Upload Support
- **PDF document analysis**: Homework assignments, quizzes, study materials, research papers
- **Image processing**: Screenshots of questions, handwritten notes, textbook pages, worksheets
- **Complete file memory**: Remembers all uploaded files and can answer follow-up questions
- **Smart analysis**: Understands document requirements, explains exercises, and provides guidance

### 🧠 Intelligent Memory System
- **Conversation history**: Remembers past interactions and builds on previous lessons
- **File memory**: Stores complete analyses of uploaded documents for future reference
- **Personalized learning**: Tracks progress, strengths, weaknesses, and learning goals
- **Context-aware responses**: References previous discussions and uploaded content

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Google Gemini API Key (from [Google AI Studio](https://makersuite.google.com/app/apikey))



1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables**

   Create a `.env` file in the root directory:
   ```
   TELEGRAM_TOKEN=your_telegram_bot_token_here
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

3. **Run the bot**
   ```bash
   python bot.py
   ```

## 📖 Usage Examples

### Getting Started
Send `/start` or "hello" to begin your learning journey!

### Language Learning
- "Help me practice English grammar"
- "Explain French verb conjugations"
- "Give me Khmer vocabulary for business"

### Writing Assistance
- "Help me write an essay about climate change in French"
- "Check grammar in this paragraph: [your text]"
- "Create a presentation script about education reform"

### File Upload Support
- **Upload a PDF** and ask: "What does this assignment want me to do?"
- **Send a screenshot** and ask: "Help me answer these quiz questions"
- **Upload worksheets** and ask: "Help me complete this exercise"

### Follow-up Questions
- "Explain page 3 of my uploaded document"
- "What was the main point of my previous upload?"
- "Help me answer question 5 from my homework"

## 🛠️ Technical Details

### Dependencies
- `python-telegram-bot==21.4` - Telegram Bot API wrapper
- `google-generativeai==0.8.3` - Google Gemini AI integration
- `nest-asyncio==1.6.0` - Asyncio compatibility
- `python-dotenv==1.0.1` - Environment variable management
- `flask==3.0.2` - Keep-alive server for Replit
- `pillow==10.3.0` - Image processing support

### Architecture
- **Asynchronous processing** for handling multiple users concurrently
- **File memory system** with comprehensive document analysis storage
- **Context-aware AI responses** using conversation history and file memory
- **Error handling and retry logic** for robust operation
- **Health monitoring** with periodic status checks

### File Processing
- **Supported formats**: PDF, JPG, JPEG, PNG
- **Vision AI integration**: Uses Gemini 1.5 Flash for document and image analysis
- **Memory retention**: Stores up to 10 recent file analyses per user
- **Smart detection**: Automatically categorizes and analyzes different document types

## 🤖 Bot Capabilities

### Learning Features
- Grammar explanations with clear examples
- Vocabulary lessons with usage context
- Translation between English, Khmer, and French
- Pronunciation guidance and conversation practice
- Writing feedback and improvement suggestions

### File Analysis Features
- **Homework help**: Explains assignments and provides guidance
- **Quiz assistance**: Helps understand questions and find answers
- **Study material analysis**: Summarizes content and explains concepts
- **Writing sample review**: Provides feedback on essays and compositions
- **Exercise completion**: Guides through worksheets and practice materials

### Memory Features
- Remembers user preferences and learning goals
- Tracks progress across multiple sessions
- References previous conversations and uploaded files
- Builds on past lessons and discussions
- Maintains context for follow-up questions

## 📋 Commands and Features

| Command/Type | Description |
|-------------|-------------|
| `/start` | Initialize the bot and see welcome message |
| Text messages | General language learning questions |
| PDF uploads | Document analysis and homework help |
| Image uploads | Screenshot analysis and worksheet help |
| Follow-up questions | Reference previous uploads and discussions |

## 🔧 Configuration

### Environment Variables
- `TELEGRAM_TOKEN`: Your Telegram bot token from BotFather
- `GEMINI_API_KEY`: Your Google Gemini API key

### Optional Configuration
- Bot automatically detects user language preferences
- Adjusts difficulty level based on user feedback
- Maintains conversation history for personalized responses

## 🚀 Deployment

### Replit Deployment
The bot includes a keep-alive server specifically for Replit deployment to prevent sleeping.

### Local Development
Run the bot locally for development and testing:
```bash
python bot.py
```

### Production Deployment
- Set up proper environment variables
- Configure logging and monitoring
- Set up automatic restarts on failure

## 📊 Monitoring

The bot includes built-in health monitoring that tracks:
- Active users count
- Total messages processed
- Files stored in memory
- System performance metrics






