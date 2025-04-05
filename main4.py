import streamlit as st
import google.generativeai as genai
import pyttsx3
import base64
from audio_recorder_streamlit import audio_recorder
import speech_recognition as sr
import tempfile
import os

# Configure Gemini AI (using Streamlit secrets for security)
genai.configure(api_key=st.secrets["AIzaSyCc4B5Og2hOxnERFBSp95iQ9aT-urSCKM8"])

# Page configuration
st.set_page_config(
    page_title="Gemini AI Voice Chat",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Initialize Text-to-Speech Engine
@st.cache_resource
def init_tts():
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    return engine

engine = init_tts()

# Function to convert text to speech and return as audio file
def text_to_speech(text):
    audio_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    engine.save_to_file(text, audio_file.name)
    engine.runAndWait()
    return audio_file.name

# Function to transcribe audio
def transcribe_audio(audio_bytes):
    recognizer = sr.Recognizer()
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_file.flush()
        
        with sr.AudioFile(tmp_file.name) as source:
            audio = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio)
                return text
            except sr.UnknownValueError:
                st.error("Could not understand audio")
                return None
            except sr.RequestError:
                st.error("Could not request results from Google Speech Recognition service")
                return None
    os.unlink(tmp_file.name)

# Function to get AI response
@st.cache_data(show_spinner=False)
def get_ai_response(_model, user_input):
    response = _model.generate_content(user_input)
    return response.text

# Initialize Gemini model
@st.cache_resource
def load_model():
    return genai.GenerativeModel("gemini-1.5-pro-latest")

model = load_model()

# Custom CSS for better UI
st.markdown("""
    <style>
    .stChatInput textarea {
        min-height: 120px !important;
    }
    .stAudio {
        width: 100%;
    }
    .stButton button {
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

# App Header
st.title("🎙️ Gemini AI Voice Chat")
st.markdown("Chat with Google's Gemini AI using text or voice input")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Hello! I'm your Gemini AI assistant. How can I help you today?",
        "audio": None
    })

# Sidebar with settings
with st.sidebar:
    st.header("Settings")
    input_method = st.radio(
        "Input Method:",
        ("Text", "Voice"),
        index=0,
        help="Choose between text or voice input"
    )
    
    voice_enabled = st.checkbox(
        "Enable Voice Responses", 
        value=True,
        help="Toggle text-to-speech for AI responses"
    )
    
    st.markdown("---")
    st.markdown("**About**")
    st.markdown("This chatbot uses Google's Gemini AI with voice capabilities.")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["audio"] and voice_enabled:
            st.audio(message["audio"], format='audio/wav')

# Handle user input
if input_method == "Text":
    if prompt := st.chat_input("Type your message..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt, "audio": None})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.spinner("Gemini is thinking..."):
            response = get_ai_response(model, prompt)
            audio_file = text_to_speech(response) if voice_enabled else None
            
            # Read audio file if exists
            audio_bytes = None
            if audio_file:
                with open(audio_file, 'rb') as f:
                    audio_bytes = f.read()
                os.unlink(audio_file)
            
            # Add assistant response to chat history
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response,
                "audio": audio_bytes
            })
            
            # Display assistant response
            with st.chat_message("assistant"):
                st.markdown(response)
                if audio_bytes and voice_enabled:
                    st.audio(audio_bytes, format='audio/wav')
else:
    st.write("Click the microphone to record your voice:")
    audio_bytes = audio_recorder(pause_threshold=2.0)
    
    if audio_bytes:
        # Transcribe audio
        with st.spinner("Processing your voice..."):
            prompt = transcribe_audio(audio_bytes)
            
        if prompt:
            # Add user message to chat history
            st.session_state.messages.append({
                "role": "user", 
                "content": prompt,
                "audio": audio_bytes
            })
            
            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)
                st.audio(audio_bytes, format='audio/wav')
            
            # Get AI response
            with st.spinner("Gemini is thinking..."):
                response = get_ai_response(model, prompt)
                audio_file = text_to_speech(response) if voice_enabled else None
                
                # Read audio file if exists
                response_audio = None
                if audio_file:
                    with open(audio_file, 'rb') as f:
                        response_audio = f.read()
                    os.unlink(audio_file)
                
                # Add assistant response to chat history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response,
                    "audio": response_audio
                })
                
                # Display assistant response
                with st.chat_message("assistant"):
                    st.markdown(response)
                    if response_audio and voice_enabled:
                        st.audio(response_audio, format='audio/wav')

# Clear chat button
if st.button("Clear Conversation"):
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Hello! I'm your Gemini AI assistant. How can I help you today?",
        "audio": None
    }]
    st.rerun()