"""
Simple CLI tester for the Flask /process endpoint.

Usage:
  python test_api.py /path/to/input.mp3

It will:
  - POST the file to http://localhost:5000/process
  - Print transcript, translation, reasoning
  - Save returned audio to ./out_tts.mp3 (if base64 returned)
"""
import sys
import requests
import base64
import os

SERVER = os.environ.get("BILINGUAL_SERVER", "http://127.0.0.1:5000")


def run_test_local_file(file_path):
    url = SERVER + "/process"
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "audio/mpeg")}
        # optional params: source_lang, target_lang, asr_backend, llm_backend
        data = {
            "source_lang": "zh-TW",
            "target_lang": "en",
            "asr_backend": "openai",    # or 'local'
            "llm_backend": "openai",    # or 'none'
            "return_audio_base64": "true"
        }
        r = requests.post(url, files=files, data=data, timeout=120)
    r.raise_for_status()
    j = r.json()
    print("=== TRANSCRIPT ===")
    print(j.get("transcript"))
    print("\n=== TRANSLATION ===")
    print(j.get("translation"))
    print("\n=== REASONING ===")
    print(j.get("reasoning"))
    audio_b64 = j.get("audio_base64")
    if audio_b64:
        out_path = "out_tts.mp3"
        with open(out_path, "wb") as fh:
            fh.write(base64.b64decode(audio_b64))
        print(f"\nSaved TTS audio to {out_path}")
    else:
        print("No audio returned.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_api.py /path/to/input.mp3")
        sys.exit(1)
    run_test_local_file(sys.argv[1])
