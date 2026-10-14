# 🩺 HIA — Health Insights Agent

AI-powered blood report analysis app. Upload a blood report (PDF or image), get instant AI analysis, ask follow-up questions, and export results as PDF.

## Features

- **AI Blood Report Analysis** — comprehensive analysis of CBC, metabolic panel, lipids, liver, thyroid markers
- **OCR Support** — scanned PDFs and JPG/PNG images via Tesseract
- **Biomarker Table** — color-coded (Normal / Low / High / Critical) extracted biomarkers
- **Chat Q&A** — ask follow-up questions about your report using RAG
- **Voice Input** — record questions via microphone (Groq Whisper transcription)
- **Multi-language** — 9 languages including Hindi, Arabic, Tamil, Chinese
- **PDF Export** — download full report with analysis and chat history
- **Secure Auth** — Supabase authentication, all data stored per user

## Tech Stack

- **Frontend**: Streamlit
- **AI**: Groq (qwen/qwen3.8-27b), LangChain, FAISS, HuggingFace Embeddings
- **OCR**: Tesseract + pdf2image
- **Auth & Storage**: Supabase
- **TTS**: gTTS | **STT**: Groq Whisper

## Deploy on Streamlit Cloud

1. Fork this repo
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app → connect repo
3. Set main file path: `src/main.py`
4. Add secrets in Streamlit Cloud dashboard:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-public-key"
GROQ_API_KEY = "your-groq-api-key"
```

## Supabase Schema

Run this SQL in your Supabase SQL Editor:

```sql
create table public.users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  name text,
  password_hash text not null,
  created_at timestamptz default now()
);

create table public.chat_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.users(id) on delete cascade,
  title text not null,
  created_at timestamptz default now()
);

create table public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references public.chat_sessions(id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'system')),
  content text not null,
  created_at timestamptz default now()
);
```

## Author

**Sindhu Priya B** — [github.com/sindhu-2211](https://github.com/sindhu-2211)
