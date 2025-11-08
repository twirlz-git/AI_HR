# AI HR System

An AI-powered HR interview assistant with real-time speech recognition and intelligent resume analysis. Built for modern recruitment workflows, this system automates candidate evaluation and conducts structured interviews.

## ✨ Features

### 🎤 Real-Time Speech Recognition
- Live audio transcription using Vosk STT engine
- WebSocket-based streaming for instant feedback
- FFmpeg audio processing pipeline
- Automatic silence detection and speech segmentation

### 📄 Intelligent Resume Analysis
- AI-powered resume parsing and evaluation
- Multi-format support (PDF, DOCX, TXT, RTF)
- Automated candidate-job matching with scoring
- Bulk resume comparison and ranking

### 🧠 AI Interview Assistant
- Structured interview flow with AI-generated questions
- Real-time response evaluation using Claude 3.5 Sonnet
- Context-aware follow-up questions
- Interview session management

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- FFmpeg installed on your system

### Backend Setup

1. **Clone the repository:**
```
git clone https://github.com/twirlz-git/AI_HR.git
cd AI_HR/AI_HR/backend
```

2. **Create virtual environment:**
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```
pip install -r requirements.txt
```

4. **Download Vosk model:**
```
# Download Russian language model from https://alphacephei.com/vosk/models
# Extract to models/vosk-model-ru or set path in settings
```

5. **Configure API key:**
```
export OPENROUTER_API_KEY="your-openrouter-api-key"
# Or create .env file with OPENROUTER_API_KEY=your-key
```

6. **Start the backend:**
```
python main.py
```
Backend will run on `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend directory:**
```
cd ../frontend-react
```

2. **Install dependencies:**
```
npm install
```

3. **Start development server:**
```
npm start
```
Frontend will open at `http://localhost:3000`

## 📡 API Endpoints

### REST API

- `GET /` - API status check
- `GET /health` - Server health and Vosk model status
- `POST /analyze_resumes` - Analyze multiple resumes against job description (JSON)
- `POST /upload_analyze` - Analyze uploaded files (job description + resumes)

### WebSocket

- `WS /ws` - Real-time audio streaming and interview management
  - Send audio chunks as binary data
  - Send JSON commands for interview control

## 🛠️ Technology Stack

### Backend
- **FastAPI** - Modern async web framework
- **Vosk** - Offline speech recognition engine
- **OpenRouter API** - LLM integration (Claude 3.5 Sonnet)
- **FFmpeg** - Audio processing and transcoding
- **PyMuPDF4LLM** - PDF text extraction
- **python-docx** - DOCX parsing
- **WebSockets** - Real-time bidirectional communication

### Frontend
- **React** - UI library
- **TypeScript** - Type-safe development
- **Modern CSS** - Responsive design

## 📂 Project Structure

```
AI_HR/
├── backend/
│   ├── core_speech_recognition/  # Speech recognition module
│   │   ├── vosk_handler.py       # Vosk STT integration
│   │   └── settings.py           # Configuration
│   ├── resume_analysis/          # Resume analysis module
│   ├── main.py                   # FastAPI application
│   └── requirements.txt
└── frontend-react/               # React application
    ├── src/
    └── package.json
```

## 🎯 Use Cases

1. **Automated Resume Screening** - Upload job description and multiple resumes to get ranked candidates
2. **AI-Conducted Interviews** - Let the system conduct initial screening interviews
3. **Speech-to-Text HR Notes** - Real-time transcription of interview conversations
4. **Candidate Evaluation** - AI-powered scoring and matching against job requirements

## 🔧 Configuration

Edit `backend/core_speech_recognition/settings.py` to customize:
- Vosk model path
- FFmpeg parameters
- API keys and endpoints
- Server host and port
- Logging level

## 👥 Contributors

- **DMomot** (Dmitry Momot) - Core development
- **twirlz-git** (McLovin) - Core development

## 📝 License

No license information provided.

## 🐛 Known Issues

- Requires FFmpeg to be installed system-wide
- Vosk model must be downloaded separately
- OpenRouter API key required for resume analysis features

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

**Made with ❤️ for modern HR workflows**
