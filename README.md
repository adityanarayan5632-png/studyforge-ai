\# StudyForge AI 📚🤖



StudyForge AI is an AI-powered study assistant that helps students learn from their study materials more effectively.



Users can upload PDF documents, chat with their study material, generate structured notes, and create practice quizzes using Retrieval-Augmented Generation (RAG) and local Large Language Models (LLMs).



\---



\## 🚀 Features



\### 📄 PDF Upload \& Processing



\* Upload PDF study materials

\* Automatic text extraction

\* Intelligent chunking of content

\* Vector embedding generation



\### 💬 AI Tutor Chat



\* Ask questions directly from uploaded study material

\* Context-aware answers using RAG

\* Reduces hallucinations by grounding responses in document content



\### 📝 Study Notes Generator



\* Automatically creates structured notes

\* Generates:



&#x20; \* Summary

&#x20; \* Key Concepts

&#x20; \* Important Definitions

&#x20; \* Revision Points



\### 🧠 Quiz Generator



\* Generates multiple-choice questions from uploaded material

\* Includes:



&#x20; \* Questions

&#x20; \* Answer options

&#x20; \* Correct answers

&#x20; \* Explanations



\---



\## 🏗️ Architecture



```text

PDF Upload

&#x20;    ↓

Text Extraction

&#x20;    ↓

Chunking

&#x20;    ↓

Embeddings

&#x20;    ↓

ChromaDB Vector Store

&#x20;    ↓

RAG Retrieval

&#x20;    ↓

Ollama + Qwen2.5

&#x20;    ↓

Answers / Notes / Quiz

```



\---



\## 🛠️ Tech Stack



\### Frontend



\* Next.js

\* TypeScript

\* Tailwind CSS

\* Axios



\### Backend



\* FastAPI

\* Python



\### AI \& RAG



\* Ollama

\* Qwen2.5

\* Sentence Transformers

\* ChromaDB



\---



\## 📂 Project Structure



```text

studyforge-ai/

│

├── backend/

│   ├── app.py

│   ├── pdf\_processor.py

│   ├── chunker.py

│   ├── embedder.py

│   ├── vector\_store.py

│   ├── rag\_pipeline.py

│   ├── notes\_generator.py

│   ├── quiz\_generator.py

│   └── ollama\_client.py

│

├── frontend/

│   ├── app/

│   ├── public/

│   └── package.json

│

└── README.md

```



\---



\## ⚙️ Installation



\### Clone Repository



```bash

git clone https://github.com/adityanarayan5632-png/studyforge-ai.git

cd studyforge-ai

```



\### Backend Setup



```bash

cd backend



python -m venv venv



venv\\Scripts\\activate



pip install -r requirements.txt

```



\### Install Ollama



Download and install Ollama:



https://ollama.com



Pull the model:



```bash

ollama pull qwen2.5:3b

```



Run backend:



```bash

python -m uvicorn app:app --reload

```



Backend runs on:



```text

http://127.0.0.1:8000

```



\---



\### Frontend Setup



```bash

cd frontend



npm install



npm run dev

```



Frontend runs on:



```text

http://localhost:3000

```



\---



\## 🎯 Future Enhancements



\* Flashcard Generator

\* YouTube Lecture Analysis

\* Video Upload Support

\* Audio Lecture Support

\* Multi-PDF Chat

\* Chat History

\* Cloud Deployment

\* Groq/OpenAI Integration



\---



\## 👨‍💻 Author



\*\*Aditya Narayan\*\*



GitHub:

https://github.com/adityanarayan5632-png



\---



\## 📜 License



This project is developed for educational and portfolio purposes.




---

## Multi-modal uploads (backend setup)

The backend now accepts more than PDFs: audio, video, screenshots, and
YouTube links. Each source type gets converted to text, then flows through
the same chunk → embed → store pipeline as PDFs always have.

| Source | Extensions | How it's read |
|---|---|---|
| PDF | `.pdf` | Text extraction via PyMuPDF |
| Audio | `.mp3 .wav .m4a .ogg .flac .aac` | Transcribed locally with Whisper |
| Video | `.mp4 .mov .avi .mkv .webm` | Audio track extracted (ffmpeg), then transcribed with Whisper |
| Screenshot | `.png .jpg .jpeg .webp` | OCR via Tesseract |
| YouTube | any video URL | Existing captions used if available, otherwise audio is downloaded and transcribed |

### Additional system dependencies

Beyond `pip install -r requirements.txt`, these system binaries must be
installed and on `PATH`:

- **ffmpeg** — used for video audio extraction and YouTube audio fallback
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `apt-get install ffmpeg`
- **tesseract-ocr** — used for screenshot OCR
  - macOS: `brew install tesseract`
  - Ubuntu/Debian: `apt-get install tesseract-ocr`

The first audio/video/YouTube upload will download the Whisper model
locally (size depends on `WHISPER_MODEL`, default `base`) — this needs
internet access on first run only, after which it's cached.

### Known limitation

Whisper transcription (audio/video/YouTube fallback) runs synchronously in
the request — a long lecture recording will make that `/upload` call take
a while and block the worker. Fine for local single-user use; a real
deployment would want this moved to a background job.
