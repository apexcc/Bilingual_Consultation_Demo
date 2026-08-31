import os
import base64
import tempfile
from pathlib import Path

# Optional dependencies
try:
    import openai
except Exception:
    openai = None

try:
    from gtts import gTTS
except Exception:
    gTTS = None

# optional translator fallback
try:
    from googletrans import Translator
except Exception:
    Translator = None

# optional local whisper
try:
    import whisper
except Exception:
    whisper = None


def transcribe_with_openai(audio_path, language=None):
    if openai is None:
        raise RuntimeError("openai package not installed or OPENAI_API_KEY not provided.")
    openai.api_key = os.getenv("OPENAI_API_KEY")
    with open(audio_path, "rb") as f:
        # Pass language as a keyword argument for openai 0.28.1 compatibility
        kwargs = {"model": "whisper-1", "file": f}
        if language:
            kwargs["language"] = language
        transcript = openai.Audio.transcribe(**kwargs)
    text = transcript.get("text") if isinstance(transcript, dict) else getattr(transcript, "text", None)
    return text


def transcribe_with_local_whisper(audio_path, language=None, model="small"):
    if whisper is None:
        raise RuntimeError("whisper is not installed. Install via `pip install -U openai-whisper` or choose OpenAI ASR.")
    model = whisper.load_model(model)
    result = model.transcribe(audio_path, language=language)
    return result.get("text")


def translate_with_openai(text, source_lang="zh-TW", target_lang="en"):
    if openai is None:
        raise RuntimeError("openai package not installed or OPENAI_API_KEY not provided.")
    openai.api_key = os.getenv("OPENAI_API_KEY")
    system = {
        "role": "system",
        "content": "You are a helpful translator assistant. Output only a JSON object with keys: translation, reasoning"
    }
    user = {
        "role": "user",
        "content": f"Translate the following text from {source_lang} to {target_lang}. Provide a brief reasoning/explanation for any non-literal choices.\n\nText:\n{text}"
    }
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[system, user],
        max_tokens=500,
        temperature=0.2,
    )
    out = resp["choices"][0]["message"]["content"].strip()
    # Expect JSON; attempt to parse, otherwise return raw translation
    try:
        import json
        j = json.loads(out)
        return j.get("translation"), j.get("reasoning")
    except Exception:
        # fallback: place all into translation, empty reasoning
        return out, ""


def translate_with_googletrans(text, source_lang="zh-TW", target_lang="en"):
    if Translator is None:
        raise RuntimeError("googletrans not installed; install with `pip install googletrans==4.0.0-rc1`")
    tr = Translator()
    # googletrans uses language codes like 'zh-tw' or 'zh-cn' sometimes; pass 'zh-TW' maps to 'zh-tw'
    t = tr.translate(text, src=source_lang, dest=target_lang)
    return t.text, ""


def synthesize_gtts(text, lang="en", out_path=None):
    if gTTS is None:
        raise RuntimeError("gTTS not installed. Install with `pip install gTTS`")
    tts = gTTS(text=text, lang=lang)
    if not out_path:
        out_path = os.path.join(tempfile.gettempdir(), "tts_out.mp3")
    tts.save(out_path)
    return out_path


def process_audio_request(file_path, source_lang="zh-TW", target_lang="en",
                          asr_backend="openai", llm_backend="openai",
                          tts_backend="gtts", tmp_dir=None, return_audio_base64=True):
    """
    Orchestrates ASR -> (LLM translation or fallback) -> TTS.
    Returns a dictionary with transcription, translation, reasoning (optional), and audio path/base64.
    """
    tmp_dir = tmp_dir or tempfile.gettempdir()
    file_path = str(file_path)
    # 1) Transcribe
    if asr_backend == "openai":
        transcript = transcribe_with_openai(file_path, language=source_lang)
    elif asr_backend == "local":
        transcript = transcribe_with_local_whisper(file_path, language=source_lang)
    else:
        raise ValueError("Unsupported ASR backend: " + asr_backend)

    # 2) Translate / Reason
    reasoning = ""
    if llm_backend == "openai":
        try:
            translation, reasoning = translate_with_openai(transcript, source_lang=source_lang, target_lang=target_lang)
        except Exception as e:
            # fallback to translator
            translation, reasoning = translate_with_googletrans(transcript, source_lang=source_lang, target_lang=target_lang)
    elif llm_backend == "none":
        translation, reasoning = translate_with_googletrans(transcript, source_lang=source_lang, target_lang=target_lang)
    else:
        raise ValueError("Unsupported LLM backend: " + llm_backend)

    # 3) TTS
    out_audio = os.path.join(tmp_dir, f"tts_{Path(file_path).stem}_{target_lang}.mp3")
    if tts_backend == "gtts":
        synth_path = synthesize_gtts(translation, lang=target_lang[:2], out_path=out_audio)
    else:
        raise ValueError("Unsupported TTS backend: " + tts_backend)

    audio_base64 = None
    if return_audio_base64:
        with open(synth_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode("utf-8")

    return {
        "transcript": transcript,
        "translation": translation,
        "reasoning": reasoning,
        "audio_file": synth_path,
        "audio_base64": audio_base64
    }
