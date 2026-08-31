from flask import Flask, request, jsonify, send_file
from processor import process_audio_request
import os

app = Flask(__name__)
TEMP_DIR = os.path.join(os.path.dirname(__file__), "tmp")
os.makedirs(TEMP_DIR, exist_ok=True)

@app.route("/process", methods=["POST"])
def process():
    """
    Accepts:
      - multipart/form-data with 'file' (uploaded voice) OR
      - application/json with "file_path" (server-side path)
    Optional form/json fields:
      - source_lang: default 'zh-TW'
      - target_lang: default 'en'
      - asr_backend: 'openai' or 'local' (default 'openai' if OPENAI_API_KEY present else 'local')
      - llm_backend: 'openai' or 'none' (default 'openai' if OPENAI_API_KEY present else 'none')
      - tts_backend: 'gtts' (default)
      - return_audio_base64: 'true' or 'false' (default true)
    Returns JSON:
      { "transcript": "...",
        "translation": "...",
        "reasoning": "...",         # optional if LLM used and asked to explain
        "audio_file": "path or filename",
        "audio_base64": "..."       # optional
      }
    """
    # pick params from form or json
    json_data = None
    if request.is_json:
        try:
            json_data = request.get_json()
        except Exception:
            json_data = {}
    source_lang = request.form.get("source_lang") or (json_data.get("source_lang") if json_data else None)
    target_lang = request.form.get("target_lang") or (json_data.get("target_lang") if json_data else None)
    asr_backend = request.form.get("asr_backend") or (json_data.get("asr_backend") if json_data else None)
    llm_backend = request.form.get("llm_backend") or (json_data.get("llm_backend") if json_data else None)
    tts_backend = request.form.get("tts_backend") or (json_data.get("tts_backend") if json_data else None)
    return_base64 = (request.form.get("return_audio_base64") or (json_data.get("return_audio_base64") if json_data else None)) or "true"

    # defaults
    source_lang = source_lang or "zh-TW"
    target_lang = target_lang or "en"
    tts_backend = tts_backend or "gtts"
    # if the user didn't state backends, choose 'openai' if key present
    if asr_backend is None:
        asr_backend = "openai" if os.getenv("OPENAI_API_KEY") else "local"
    if llm_backend is None:
        llm_backend = "openai" if os.getenv("OPENAI_API_KEY") else "none"

    # handle file upload or file_path
    uploaded_file = None
    file_path = None
    if "file" in request.files:
        uploaded_file = request.files["file"]
        tmp_path = os.path.join(TEMP_DIR, uploaded_file.filename)
        uploaded_file.save(tmp_path)
        file_path = tmp_path
    else:
        # JSON body expected
        data = json_data or {}
        file_path = data.get("file_path")
        if not file_path or not os.path.exists(file_path):
            return jsonify({"error": "No file received and 'file_path' not provided or does not exist."}), 400

    try:
        result = process_audio_request(
            file_path=file_path,
            source_lang=source_lang,
            target_lang=target_lang,
            asr_backend=asr_backend,
            llm_backend=llm_backend,
            tts_backend=tts_backend,
            tmp_dir=TEMP_DIR,
            return_audio_base64=(str(return_base64).lower() == "true")
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
