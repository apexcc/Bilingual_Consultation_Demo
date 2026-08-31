# Bilingual Consultation Demo — bilingual-chat-server

This branch adds a simple Flask-based bilingual chat server that accepts voice input
(uploads or server-side file paths), transcribes it, optionally runs translation/reasoning
via an LLM, and returns translated text plus synthesized voice (TTS).

Files added:
- app.py — Flask callback server (POST /process)
- processor.py — ASR/Translation/TTS orchestration
- test_api.py — CLI test client that posts a local MP3 to the server
- requirements.txt — Python dependencies

How to run (quick):
1. pip install -r requirements.txt
2. Optional: export OPENAI_API_KEY="sk-..." if you want OpenAI ASR/LLM
3. python app.py
4. python test_api.py /path/to/your_input.mp3

Notes:
- The implementation uses OpenAI (if OPENAI_API_KEY available) or local Whisper for ASR,
  OpenAI Chat for reasoning/translation (optional), googletrans as a fallback translator,
  and gTTS for TTS.
- For production, add authentication, file size/type checks, and replace gTTS with a
  higher-quality TTS provider if necessary.
