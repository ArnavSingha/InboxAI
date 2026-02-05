# InboxAI

> AI-powered email assistant with natural language commands

🔗 **Live Demo**: [https://inboxai.vercel.app](https://inboxai.vercel.app)

---

## 📖 Description

InboxAI is an intelligent email assistant that integrates directly with your Gmail account. Instead of clicking through buttons and menus, you can manage your inbox using natural language commands like "Show me emails about invoices" or "Reply to John". 

It uses **Google Gemini** to understand your intent, summarize complex customized emails, and draft professional replies, all within a secure, privacy-focused dashboard.

---

## ✨ Features

- **🗣️ Natural Language Control**: "Delete the spam from LinkedIn", "Organize my inbox".
- **🧠 Smart Support**:
  - **Summarization**: 1-2 sentence summaries of long threads.
  - **Drafting**: Context-aware replies generated in seconds.
  - **Categorization**: Auto-groups emails into Work, Personal, Promotions, etc.
  - **Daily Digest**: A compiled summary of your day's key messages.
- **🔐 Secure Auth**: Google OAuth 2.0 integration with HTTP-only session cookies.
- **⚡ Real-time**: Immediate actions on your actual Gmail inbox.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI (Python 3.11) |
| **Frontend** | Next.js 14 (App Router, TypeScript) |
| **AI Model** | Google Gemini (Gemini 1.5 Flash) |
| **Auth** | Google OAuth 2.0 |
| **Email** | Gmail API |
| **Testing** | Pytest, React Testing Library |

---

## 🚀 Setup & Development

### Prerequisites

- Node.js 18+
- Python 3.11+
- Google Cloud Project with:
  - Gmail API enabled
  - OAuth 2.0 Credentials configured
- Google Gemini API Key

### 1. Backend Setup

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
# source venv/bin/activate

pip install -r requirements.txt

# Create .env file (see below)
cp .env.example .env

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup

```bash
cd frontend
npm install

# Create .env.local file
cp .env.example .env.local

# Run dev server
npm run dev
```

Visit `http://localhost:3000` to start using the app.

---

## 🔑 Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLIENT_ID` | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | From Google Cloud Console |
| `GOOGLE_REDIRECT_URI` | `http://localhost:8000/api/auth/callback` (Local) |
| `FRONTEND_URL` | `http://localhost:3000` (Local) |
| `GEMINI_API_KEY` | Google AI Studio API Key |
| `SESSION_SECRET` | Random string for signing cookies |
| `DEBUG` | `true` for detailed logging |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` |

---

## ⚠️ Assumptions & Limitations

1. **Development Mode**: The Google OAuth app is likely in "Testing" mode. You must add your email address to the "Test Users" list in Google Cloud Console to log in.
2. **Context Window**: The AI analyzes the last 5-20 emails. It does not index your entire historical inbox due to API rate limits and performance latency.
3. **Drafts**: The "Reply" feature creates a draft in the UI for your approval. It sends the email immediately upon confirmation (it does not save a draft to Gmail's 'Drafts' folder first).
4. **Trash**: The "Delete" command moves emails to Trash, allowing for recovery. It does not permanently delete them.
5. **Single Account**: The app is designed for a single active Google session per browser context.

---

## 🧪 Running Tests

A comprehensive test suite covers Gmail parsing, Intent understanding, and Service logic.

```bash
cd backend
# Run all tests
pytest

# Run specific test file
pytest tests/test_intent_parser.py
```
