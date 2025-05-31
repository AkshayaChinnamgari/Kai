import customtkinter as ctk
import tkinter as tk
import threading
import asyncio
import re
import pyttsx3
import speech_recognition as sr
import webbrowser
from main import (
    process_query, generate_code, say,
    extract_city, get_weather, play_music, main
)
from datetime import datetime

# Initialize Text-to-Speech Engine
engine = pyttsx3.init()
engine.setProperty("rate", 175)
engine.setProperty("volume", 1.0)

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class KaiGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🤖 Kai A.I. Voice Assistant")
        self.geometry("800x580")
        self.resizable(False, False)

        self.dark_mode = ctk.get_appearance_mode() == "dark"
        self.mic_on = False
        self.full_response_text = ""
        self.speech_thread = None
        self.speech_stop_event = threading.Event()

        # Background Frame
        self.bg_frame = ctk.CTkFrame(self, fg_color=("gray10", "gray90"), corner_radius=0)
        self.bg_frame.pack(fill="both", expand=True)

        # Title Label
        self.title_label = ctk.CTkLabel(self.bg_frame, text="Kai A.I.", font=("Helvetica", 24, "bold"))
        self.title_label.pack(pady=10)

        # Chat Area
        self.chat_area = ctk.CTkTextbox(self.bg_frame, width=760, height=350, wrap=tk.WORD, corner_radius=15)
        self.chat_area.pack(pady=10)

        # User Input Field
        self.input_entry = ctk.CTkEntry(self.bg_frame, placeholder_text="Ask me anything...", width=500, corner_radius=10)
        self.input_entry.pack(pady=10)

        # Button Row
        btn_frame = ctk.CTkFrame(self.bg_frame, fg_color="transparent")
        btn_frame.pack(pady=10)

        self.submit_btn = ctk.CTkButton(btn_frame, text="Submit", command=self.process_input, fg_color="#61afef",
                                        hover_color="#528bbe", width=100, corner_radius=12)
        self.submit_btn.pack(side="left", padx=5)

        self.clear_btn = ctk.CTkButton(btn_frame, text="Clear", command=self.clear_chat, fg_color="#e06c75",
                                       hover_color="#be5757", width=100, corner_radius=12)
        self.clear_btn.pack(side="left", padx=5)

        self.theme_btn = ctk.CTkButton(btn_frame, text="🌗 Toggle Theme", command=self.toggle_theme, fg_color="#abb2bf",
                                       hover_color="#9099a3", width=150, corner_radius=12)
        self.theme_btn.pack(side="left", padx=5)

        self.stop_speak_btn = ctk.CTkButton(
            btn_frame, text="🛑 Stop Speaking", command=self.stop_speaking,
            fg_color="#ffb347", hover_color="#e59400", width=150, corner_radius=12
        )
        self.stop_speak_btn.pack(side="left", padx=5)

        self.mic_btn = ctk.CTkButton(btn_frame, text="🎤 Mic OFF", command=self.toggle_mic, fg_color="#c678dd",
                                     hover_color="#9c52b3", width=150, corner_radius=12)
        self.mic_btn.pack(side="left", padx=5)

        self.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.mic_thread = None
        self.mic_lock = threading.Lock()

        self.apply_theme()

    def takeCommand(self):
        """Captures voice input reliably & updates both GUI & terminal."""
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("🎤 Listening...")
            self.display_message("\n🎤 Listening...")

            r.adjust_for_ambient_noise(source, duration=1)
            r.pause_threshold = 0.7
            r.phrase_time_limit = 8
            audio = r.listen(source)

        try:
            return r.recognize_google(audio, language="en-in").lower()
        except sr.UnknownValueError:
            self.display_message("\n❌ Could not understand audio.")
            print("❌ Could not understand audio.")
            return None
        except sr.RequestError:
            self.display_message("\n⚠️ Speech recognition service unavailable.")
            print("⚠️ Speech recognition service unavailable.")
            return None

    def speak_response(self, response):
        """Handles text-to-speech execution with interruption control."""
        if self.speech_thread is not None and self.speech_thread.is_alive():
            self.stop_speaking()  # Stop previous speech

        self.speech_thread = threading.Thread(target=self._run_speech, args=(response,), daemon=True)
        self.speech_thread.start()

    def _run_speech(self, text):
        """Speaks the full response without pauses."""
        self.speech_stop_event.clear()

        try:
            engine.say(text)
            engine.runAndWait()
        except RuntimeError:
            pass

        self.speech_thread = None  # Reset thread for future speech

    def stop_speaking(self):
        """Interrupts ongoing speech but ensures next query works fine."""
        if self.speech_thread and self.speech_thread.is_alive():
            self.speech_stop_event.set()
            engine.stop()
            self.speech_thread = None  # Reset speech thread for the next query

    def on_exit(self):
        self.mic_on = False
        self.quit()
        self.destroy()

    def process_input(self):
        query = self.input_entry.get()
        self.input_entry.delete(0, tk.END)

        if query:
            self.display_message(f"\n👤 You: {query}\n")
            response = asyncio.run(main(query))
            self.full_response_text = response
            self.speak_response(response)
            self.display_message(f"🤖 Kai: {response}\n")

    def display_message(self, message):
        cleaned_message = re.sub(r"\*\*(.*?)\*\*", r"\1", message)
        self.chat_area.insert("end", cleaned_message + "\n")
        self.chat_area.see("end")

    def clear_chat(self):
        self.chat_area.delete("1.0", "end")

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        new_theme = "dark" if self.dark_mode else "light"
        ctk.set_appearance_mode(new_theme)
        self.title_label.configure(text_color="white" if self.dark_mode else "black")
        self.bg_frame.configure(fg_color="gray10" if self.dark_mode else "gray90")
        self.update()

    def apply_theme(self):
        self.dark_mode = ctk.get_appearance_mode() == "dark"
        self.title_label.configure(text_color="white" if self.dark_mode else "black")

    def toggle_mic(self):
        if self.speech_thread is not None and self.speech_thread.is_alive():
            return

        self.mic_on = not self.mic_on
        self.mic_btn.configure(text="🎤 Mic ON" if self.mic_on else "🎤 Mic OFF")

        if self.mic_on:
            if self.mic_thread is None or not self.mic_thread.is_alive():
                self.mic_thread = threading.Thread(target=self.listen_mic, daemon=True)
                self.mic_thread.start()

    def listen_mic(self):
        """Listens and processes user speech."""
        self.last_query = ""

        while self.mic_on:
            self.last_query = self.takeCommand()

        if self.last_query:
            print("🔍 Recognizing...")
            self.display_message("\n🔍 Recognizing...")
            self.display_message(f"\n👤 You (via Mic): {self.last_query}\n")
            response = asyncio.run(main(self.last_query))
            self.full_response_text = response
            self.speak_response(response)
            self.display_message(f"🤖 Kai: {response}\n")

if __name__ == "__main__":
    app = KaiGUI()
    app.mainloop()