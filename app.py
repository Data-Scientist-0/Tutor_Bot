import streamlit as st
import google.genai as genai
from gtts import gTTS
import os
import speech_recognition as sr
from pydub import AudioSegment
import threading
import time
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# 1. SETUP - Using the latest Gemini model
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    st.error("API_KEY not found in .env file. Please check your .env file.")
    st.stop()
client = genai.Client(api_key=API_KEY)

# Use 'gemini-2.5-flash' for the best performance
MODEL_ID = "gemini-2.5-flash"

TEACHER_PROMPT = """
Role: You are Layan's personal, expert tutor.
Goal: Efficient, baby-step learning with no wasted time.
Rules:
- Explain 1 Concept (1 sentence) + 1 Analogy + 1 Example.
- ALWAYS end with a Task for Layan.
- If Layan sends audio, listen carefully to her tone and understanding.
"""



def transcribe_audio(audio_file):
    try:
        # Convert to WAV if necessary
        if audio_file.name.endswith('.mp3'):
            audio = AudioSegment.from_mp3(audio_file)
            audio.export("temp_transcribe.wav", format="wav")
            audio_path = "temp_transcribe.wav"
        else:
            audio_path = audio_file.name
            with open(audio_path, "wb") as f:
                f.write(audio_file.getbuffer())

        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            return text
    except Exception as e:
        st.error(f"Transcription failed: {str(e)}")
        return ""

def tutor_chat(audio_input, text_input, history, language):
    try:
        # Get dynamic prompt based on language
        prompt = get_teacher_prompt(language)
        # Rebuild history for Gemini API
        contents = [{"role": "model", "parts": [{"text": prompt}]}]
        for msg in history:
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        # Process Input
        if audio_input:
            # Save uploaded file to temp
            with open("temp_audio.wav", "wb") as f:
                f.write(audio_input.getbuffer())
            audio_file = genai.upload_file(path="temp_audio.wav")
            contents.append({"role": "user", "parts": [audio_file]})
            user_display = "🎤 [Voice Message]"
        else:
            user_text = text_input
            contents.append({"role": "user", "parts": [{"text": user_text}]})
            user_display = user_text

        response = client.models.generate_content(model=MODEL_ID, contents=contents)

        # Generate Voice Output
        lang_code = language_options.get(language, 'en')
        tts = gTTS(text=response.text, lang=lang_code)
        tts.save("response.mp3")

        # Append to history
        history.append({"role": "user", "content": user_display})
        history.append({"role": "assistant", "content": response.text})
        return history, "response.mp3"
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return history, None

# Function to get base64 encoded image
def get_base64_image(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    return f"data:image/jpeg;base64,{encoded_string}"

# UI Setup
st.title("🎓 Layan's personel Expert Tutor")

# Set background image
bg_image = get_base64_image("image.jpg")
st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url('{bg_image}');
        background-size: cover;
        background-repeat: no-repeat;
        background-attachment: fixed;
        background-position: center;
        color: black;
    }}
    .stApp * {{
        color: black !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

if "history" not in st.session_state:
    st.session_state.history = []

if "language" not in st.session_state:
    st.session_state.language = "English"

# Language selector
language_options = {"English": "en", "Arabic": "ar"}
selected_language = st.sidebar.selectbox("Select Language", list(language_options.keys()), index=list(language_options.keys()).index(st.session_state.language))
st.session_state.language = selected_language

def get_teacher_prompt(language):
    base_prompt = """
Role: You are Layan's personal, expert tutor.
Goal: Efficient, baby-step learning with no wasted time.
Rules:
- Explain 1 Concept (1 sentence) + 1 Analogy + 1 Example.
- ALWAYS end with a Task for Layan.
- If Layan sends audio, listen carefully to her tone and understanding.
"""
    if language == "Arabic":
        return base_prompt + "\nRespond in Arabic."
    return base_prompt

# Sidebar for audio features
with st.sidebar:
    st.header("Audio Features")
    audio_in = st.file_uploader("Upload Audio", type=["wav", "mp3", "m4a"])
    recorded_audio = st.audio_input("Record Voice Message")
    if st.button("Transcribe Audio"):
        if audio_in:
            transcribed_text = transcribe_audio(audio_in)
            st.text_area("Transcribed Text", transcribed_text, height=100)
        elif recorded_audio:
            # Save recorded audio
            with open("recorded_audio.wav", "wb") as f:
                f.write(recorded_audio.getbuffer())
            transcribed_text = transcribe_audio(recorded_audio)
            st.text_area("Transcribed Text", transcribed_text, height=100)
        else:
            st.warning("Please upload or record an audio file to transcribe.")
    if st.button("Send Audio to Teacher"):
        if audio_in:
            st.session_state.history, audio_out = tutor_chat(audio_in, "", st.session_state.history, st.session_state.language)
            st.rerun()
        elif recorded_audio:
            st.session_state.history, audio_out = tutor_chat(recorded_audio, "", st.session_state.history, st.session_state.language)
            st.rerun()
        else:
            st.warning("Please upload or record an audio file.")
    if st.button("Clear Chat"):
        st.session_state.history = []
        st.rerun()

# Display chat history
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Chat input at bottom
text_input = st.chat_input("Type your message...")
if text_input:
    st.session_state.history, audio_out = tutor_chat("", text_input, st.session_state.history, st.session_state.language)
    st.rerun()

# Audio output
if os.path.exists("response.mp3"):
    st.audio("response.mp3", format="audio/mp3")
