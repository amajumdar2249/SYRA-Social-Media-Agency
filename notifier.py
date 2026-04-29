import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_approval(topic: str, score: float, post_content: str) -> bool:
    """
    Sends the generated post to Telegram for human approval.
    """
    if not TOKEN or not CHAT_ID:
        print("❌ Telegram credentials not found in .env.")
        return False
        
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    # Format the message beautifully
    message = (
        f"🌟 **New High-Potential Post Ready!** 🌟\n\n"
        f"📌 **Topic:** {topic}\n"
        f"🔥 **Viral Score:** {score}/10\n\n"
        f"📝 **Generated Post:**\n"
        f"------------------------\n"
        f"{post_content}\n"
        f"------------------------\n\n"
        f"✅ Reply 'Approve' to publish (future feature) or just copy the text to post!"
    )
    
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("📤 Successfully sent post to Telegram for approval!")
            return True
        else:
            print(f"❌ Failed to send Telegram message: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception sending Telegram message: {e}")
        return False

if __name__ == "__main__":
    # Test
    send_telegram_approval("AI in 2026", 9.5, "This is a test post about AI.")
