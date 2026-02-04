from flask import Flask, request, jsonify
from googletrans import Translator
import speech_recognition as sr
from gtts import gTTS
import moviepy.editor as mp
import tempfile
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("API_KEY")

@app.before_request
def check_api_key():
    api_key = request.headers.get("x-api-key")
    if not api_key or api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401


@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Video Translation API is running"})


@app.route("/translate", methods=["POST"])
def translate_video():
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    video_file = request.files["video"]
    source_language = request.form.get("source_language", "en")
    target_language = request.form.get("target_language", "en")

    video_path = tempfile.mktemp(suffix=".mp4")
    audio_path = tempfile.mktemp(suffix=".wav")
    translated_audio_path = tempfile.mktemp(suffix=".mp3")
    output_video_path = tempfile.mktemp(suffix="_output.mp4")

    try:
        video_file.save(video_path)

        clip = mp.VideoFileClip(video_path)
        clip.audio.write_audiofile(audio_path)

        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)

        recognized_text = recognizer.recognize_google(audio_data, language=source_language)

        translator = Translator()
        translated_text = translator.translate(recognized_text, dest=target_language).text

        tts = gTTS(text=translated_text, lang=target_language)
        tts.save(translated_audio_path)

        new_audio = mp.AudioFileClip(translated_audio_path)
        final_video = clip.set_audio(new_audio)

        final_video.write_videofile(
            output_video_path,
            codec="libx264",
            audio_codec="aac"
        )

        return jsonify({
            "message": "Translation successful",
            "output_video": output_video_path,
            "recognized_text": recognized_text,
            "translated_text": translated_text
        })

    except sr.UnknownValueError:
        return jsonify({"error": "Speech could not be recognized"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        for path in [video_path, audio_path, translated_audio_path]:
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    app.run(debug=True)
