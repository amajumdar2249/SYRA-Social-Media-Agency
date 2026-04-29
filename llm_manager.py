import os
import re
import json
import google.generativeai as genai
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key:
    genai.configure(api_key=gemini_key)
    # Using the standard models. Gemini 1.5 is standard now.
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    gemini_model = None

# Configure Groq
groq_key = os.getenv("GROQ_API_KEY")
if groq_key:
    groq_client = Groq(api_key=groq_key)
else:
    groq_client = None

def rate_topic_gemini(title: str, summary: str) -> float:
    """Rates a topic using Gemini API."""
    if not gemini_model:
        raise Exception("Gemini API key not configured.")
        
    prompt = f"""
    You are a viral social media strategist.
    Analyze this news topic and rate its potential to go viral on LinkedIn and Twitter.
    Topic: {title}
    Summary: {summary}
    
    Return ONLY a valid JSON object with a single key "score" containing a float between 1.0 and 10.0.
    Example: {{"score": 8.7}}
    """
    
    response = gemini_model.generate_content(prompt)
    text = response.text
    return extract_score_from_json(text)

def rate_topic_groq(title: str, summary: str) -> float:
    """Rates a topic using Groq API (Llama 3)."""
    if not groq_client:
        raise Exception("Groq API key not configured.")
        
    prompt = f"""
    You are a viral social media strategist.
    Analyze this news topic and rate its potential to go viral on LinkedIn and Twitter.
    Topic: {title}
    Summary: {summary}
    
    Return ONLY a valid JSON object with a single key "score" containing a float between 1.0 and 10.0.
    Example: {{"score": 8.7}}
    """
    
    completion = groq_client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    
    text = completion.choices[0].message.content
    return extract_score_from_json(text)

def rate_topic(title: str, summary: str) -> float:
    """Main routing function for rating. Tries Gemini, falls back to Groq."""
    try:
        print(f"🧠 Rating via Gemini: {title[:30]}...")
        return rate_topic_gemini(title, summary)
    except Exception as e:
        print(f"⚠️ Gemini failed: {e}. Falling back to Groq...")
        try:
            return rate_topic_groq(title, summary)
        except Exception as e2:
            print(f"❌ Groq also failed: {e2}")
            return 0.0

def generate_post_gemini(title: str, summary: str) -> str:
    """Generates a post using Gemini."""
    if not gemini_model:
        raise Exception("Gemini API key not configured.")
        
    prompt = f"""
    Write a highly engaging, premium LinkedIn post and a short Twitter thread about the following topic.
    Use psychological hooks and modern formatting.
    
    Topic: {title}
    Summary: {summary}
    
    Return the raw text of the post.
    """
    response = gemini_model.generate_content(prompt)
    return response.text.strip()

def generate_post_groq(title: str, summary: str) -> str:
    """Generates a post using Groq (Llama 3)."""
    if not groq_client:
        raise Exception("Groq API key not configured.")
        
    prompt = f"""
    Write a highly engaging, premium LinkedIn post and a short Twitter thread about the following topic.
    Use psychological hooks and modern formatting.
    
    Topic: {title}
    Summary: {summary}
    
    Return the raw text of the post.
    """
    completion = groq_client.chat.completions.create(
        model="llama3-70b-8192", # Using 70b for better writing quality
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return completion.choices[0].message.content.strip()

def generate_post(title: str, summary: str) -> str:
    """Main routing function for generation. Tries Gemini, falls back to Groq."""
    try:
        print(f"✍️ Generating post via Gemini for: {title[:30]}...")
        return generate_post_gemini(title, summary)
    except Exception as e:
        print(f"⚠️ Gemini failed to generate: {e}. Falling back to Groq...")
        try:
            return generate_post_groq(title, summary)
        except Exception as e2:
            print(f"❌ Groq also failed to generate: {e2}")
            return "Failed to generate post."

def extract_score_from_json(text: str) -> float:
    """Helper to safely extract the score from LLM text output."""
    try:
        # Strip markdown code blocks if present
        text = text.strip()
        if text.startswith('```json'):
            text = text[7:]
        if text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
            
        data = json.loads(text.strip())
        return float(data.get("score", 0.0))
    except json.JSONDecodeError:
        # Fallback: regex to find the first number after "score"
        match = re.search(r'"score"\s*:\s*([0-9.]+)', text)
        if match:
            return float(match.group(1))
        return 0.0
