import speech_recognition as sr
import os
import webbrowser
import google.generativeai as genai
import datetime
import pyttsx3
import asyncio
import random
import re
import time
import subprocess
import requests
from mistralai.async_client import MistralAsyncClient
from mistralai.models.chat_completion import ChatMessage
from serpapi import GoogleSearch
from config import GEMINI_API_KEY, MISTRAL_API_KEY, WEATHER_API_KEY, SERPAPI_KEY, SPOTIFY_CMD

# Initialize AI Models
genai.configure(api_key=GEMINI_API_KEY)
mistral_client = MistralAsyncClient(api_key=MISTRAL_API_KEY)

# Initialize text-to-speech
engine = pyttsx3.init()
engine.setProperty("rate", 175)
engine.setProperty("volume", 1.0)

chatStr = ""

def say(text):
    """Convert text to speech."""
    engine.say(text)
    engine.runAndWait()

async def search_web(query):
    """Fetch real-time search results using SerpAPI and format response."""
    params = {
        "q": query,
        "location": "India",
        "hl": "en",
        "gl": "in",
        "api_key": SERPAPI_KEY
    }
    try:
        search = GoogleSearch(params)
        results = search.get_dict()

        if "organic_results" in results and results["organic_results"]:
            raw_snippets = [result["snippet"] for result in results["organic_results"][:5]]
            full_text = "\n".join(set(raw_snippets))  # Remove duplicates

            ai_prompt = f"Here are web search results:\n{full_text}\n\nPlease format this into a natural-sounding response."
            return await chat_with_ai(ai_prompt)
        else:
            return "I couldn't find a clear answer for that."
    except Exception as e:
        print(f"Error fetching search results: {e}")
        return "I'm having trouble retrieving information right now."


async def process_query(query):
    """Decide whether to fetch live data or use AI models."""
    query_lower = query.lower()

    # Explicit checks for date and time queries

    # Real-time search trigger conditions
    keywords = ["latest", "recent", "news", "who won", "current", "today", "2024", "2025", "next", "yesterday",
                "tomorrow", "new"]
    if any(word in query_lower for word in keywords):
        return await search_web(query)

    return await chat_with_ai(query)

def detect_language(text):
    """Detect the programming language based on the user query."""
    languages = {
        "python": ".py",
        "c++": ".cpp",
        "cpp": ".cpp",
        "java": ".java",
        "c": ".c",
        "javascript": ".js",
        "html": ".html"
    }
    for lang in languages:
        if lang in text.lower():
            return lang, languages[lang]
    return None, None

def extract_code_block(text):
    """Extract code inside triple backticks (```...`) from AI response."""
    matches = re.findall(r"```(?:\w+\n)?(.*?)```", text, re.DOTALL)
    if matches:
        return matches[0].strip()
    else:
        return None

def is_code(text):
    """Check if the given text looks like code."""
    # If text starts with ``` or contains keywords like def, class, #include
    if text.strip().startswith("```") or "def " in text or "#include" in text or "public class" in text:
        return True
    return False

def split_into_tasks(query):
    """Splits the query into multiple tasks if 'and' is found."""
    tasks = query.lower().split(" and ")
    return [task.strip() for task in tasks if task.strip()]

def generate_filename(code, extension, query="factorial"):
    """Generate a better filename based on the code content or user query."""
    # Try to find a function or class name in the code (this works for Python, Java, etc.)
    function_match = re.search(r"\bdef\s+(\w+)\s?\(", code)  # For Python
    class_match = re.search(r"\bclass\s+(\w+)\s?", code)  # For class names

    # First, try using the function or class name
    if function_match:
        filename_base = function_match.group(1)
    elif class_match:
        filename_base = class_match.group(1)
    else:
        # Fall back to the query if no function/class is found
        filename_base = re.sub(r'[^a-zA-Z0-9_]', '_', query[:20])  # First 20 chars of query

    # Make sure the filename is valid (avoid spaces and special characters)
    filename_base = re.sub(r'[^a-zA-Z0-9_]', '_', filename_base)

    # Ensure filename doesn't exceed typical length limits
    filename_base = filename_base[:30]

    # Return the final filename
    return f"{filename_base}{extension}"

async def generate_code(query):
    """Generates one or multiple code programs based on user query."""
    lang, extension = detect_language(query)
    if not lang:
        say("Sorry, I couldn't detect a programming language in your request.")
        return

    say(f"Generating {lang} programs. Please wait.")
    tasks = split_into_tasks(query)

    for idx, task in enumerate(tasks, start=1):
        full_reply = ""

        # Try Gemini first
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(task)
            full_reply = response.candidates[0].content.parts[0].text.strip()
        except Exception as e:
            print(f"Gemini AI failed for task {idx}: {e}")
            say("Primary AI failed. Switching to backup AI, Mistral.")
            try:
                messages = [ChatMessage(role="user", content=f"Write {task}")]
                response = await mistral_client.chat(model="mistral-medium", messages=messages)
                full_reply = response.choices[0].message.content.strip()
            except Exception as e:
                print(f"Mistral AI failed for task {idx}: {e}")
                say(f"Sorry, I'm unable to generate the program {idx} right now.")
                continue

        # Now extract only code part
        code = extract_code_block(full_reply)

        if code:
            # Generate filename using the new function
            filename = generate_filename(code, extension)

            with open(filename, "w", encoding="utf-8") as f:
                f.write(code)
            say(f"Saved program {idx} as {filename}.")
            print(f"\n[Saved CODE {idx} to {filename}]:\n\n{code}\n")
        else:
            say(f"Sorry, I couldn't extract proper code for program {idx}.")
            print(f"[Full AI reply was]:\n{full_reply}\n")

async def chat_with_mistral(query):
    """Handles chat using Mistral AI."""
    global chatStr
    chatStr += f"User: {query}\nKai: "

    try:
        messages = [ChatMessage(role="user", content=query)]
        response = await mistral_client.chat(model="mistral-medium", messages=messages)
        reply = response.choices[0].message.content.strip()
        say(reply)
        chatStr += f"{reply}\n"
        return reply
    except Exception as e:
        print(f"Mistral AI failed: {e}")
        say("I'm facing technical difficulties. Please try again later.")
        return "I'm facing an issue, please try again later."

async def chat_with_ai(query):
    """Uses Gemini AI first, then falls back to Mistral if needed."""
    global chatStr
    chatStr += f"User: {query}\nKai: "

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(query)
        reply = response.candidates[0].content.parts[0].text.strip()

        if is_code(reply):
            print("\n[CODE OUTPUT]:\n")
            print(reply)
            say("Here is the code. Please check the terminal.")

        chatStr += f"{reply}\n"
        return reply
    except Exception as e:
        print(f"Gemini AI failed: {e}")
        say("Primary AI failed. Switching to backup AI, Mistral.")
        return await chat_with_mistral(query)

def get_weather(city="Hyderabad"):
    """Fetches real-time weather information."""
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    try:
        response = requests.get(url)
        data = response.json()
        if data.get("cod") == 200:
            temp = data["main"]["temp"]
            description = data["weather"][0]["description"]
            return f"The temperature in {city} is {temp}°C with {description}."
        else:
            return f"Error: {data.get('message', 'Could not fetch weather details.')}"
    except Exception as e:
        print(f"Weather API error: {e}")
        return "I am unable to retrieve the weather right now."

def extract_city(query):
    """Extracts city name from the user's query."""
    match = re.search(r"(?:weather|temperature) in ([a-zA-Z\s]+)", query)
    return match.group(1).strip().title() if match else "Hyderabad"

def play_music():
    """Open Spotify and play the last song automatically."""
    os.system(SPOTIFY_CMD)
    say("Opening Spotify. Enjoy your music!")

    # Wait a few seconds to allow Spotify to open
    time.sleep(5)

    # Simulate pressing Spacebar (to start/resume music)
    subprocess.run(["powershell", "-Command", "$wshell = New-Object -ComObject wscript.shell; $wshell.SendKeys(' ')"])

def open_website(query):
    """Opens a website based on user input."""
    site = query.replace("open", "").strip().replace(" ", "")
    url = f"https://www.{site}.com"
    webbrowser.open(url)

async def main(query):
    """Processes single queries dynamically instead of an infinite loop."""
    if query.lower() in ["exit", "quit", "stop", "shutdown", "kai quit"]:
        return "Goodbye! Have a nice day!"

    if "write a" in query and "program" in query:
        return await generate_code(query)

    if "open" in query:
        open_website(query)
        return f"Opening {query.replace('open', '').strip()}."

    if "time" in query or "current time" in query:
        return f"The time is {datetime.datetime.now().strftime('%I:%M %p')}"

    if "date" in query or "current date" in query:
        return f"Today's date is {datetime.datetime.now().strftime('%B %d, %Y')}"

    if "play music" in query or "open music" in query:
        play_music()
        return "Playing music."

    if any(keyword in query for keyword in ["weather in", "temperature in"]):
        city = extract_city(query)
        return get_weather(city)

    return await process_query(query)  # Default fallback to AI processing