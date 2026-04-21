import os
import time
import requests
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from youtubesearchpython import VideosSearch

# 1. SETUP CREDENTIALS (Securely fetching from Coolify)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Initialize your suite of models
gemini_models = {
    "flash_latest": genai.GenerativeModel('gemini-2.5-flash'),
    "flash_stable": genai.GenerativeModel('gemini-2.0-flash'),
    "pro_preview": genai.GenerativeModel('gemini-3.1-pro-preview'),
    "lite": genai.GenerativeModel('gemini-3.1-flash-lite-preview')
}

# Call the specific model you need for the task
response = gemini_models["flash_stable"].generate_content("Analyze this Hacker News trend.")

def get_hackernews_trends():
    """Fetches the #1 trending tech story from Hacker News (Zero API Keys required)."""
    print("Connecting to open Hacker News API...")
    
    try:
        # 1. Get the list of current top story IDs
        top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        story_ids = requests.get(top_stories_url, timeout=10).json()

        # 2. Fetch the details of the #1 story
        top_story_id = story_ids[0]
        story_url = f"https://hacker-news.firebaseio.com/v0/item/{top_story_id}.json"
        story = requests.get(story_url, timeout=10).json()

        title = story.get('title', 'Unknown Title')
        print(f"Found Top Story: {title}")
        
        # 3. Fetch the top 5 comments for context
        comment_ids = story.get('kids', [])[:5]
        comments = []
        
        for cid in comment_ids:
            time.sleep(1) # Be polite to the API
            c_url = f"https://hacker-news.firebaseio.com/v0/item/{cid}.json"
            c_data = requests.get(c_url, timeout=10).json()
            
            if c_data and 'text' in c_data:
                # Clean up basic HTML from HN comments
                clean_text = c_data['text'].replace('<p>', ' ').replace('&#x27;', "'").replace('&quot;', '"')
                if len(clean_text) > 50:
                    comments.append(clean_text)

        return {
            "title": title,
            "comments": comments
        }
        
    except Exception as e:
        print(f"Hacker News API Error: {e}")
        return None
####


def get_yt_context_automated(query):
    """Automatically finds the top video and fetches its transcript."""
    try:
        # Search for the trending topic on YouTube
        search = VideosSearch(query + " review", limit=1)
        result = search.result()['result']
        
        if not result:
            return "No relevant video found."
            
        video_id = result[0]['id']
        video_title = result[0]['title']
        print(f"Found YouTube Context: {video_title}")
        
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t['text'] for t in transcript_list])
    except Exception as e:
        return f"YouTube Error: {e}"

def generate_sucheta_article(trend_data, yt_context):
    """The Brain: Synthesizes data into Sucheta's persona."""
    prompt = f"""
    You are Sucheta, a tech veteran with 20 years of experience. Write for a US/UK audience.
    SYSTEM ROLE: Agentic Research Analyst for BuzzVerified.com.

    TOPIC: {trend_data['title']}
    REDDIT VOICES: {trend_data['comments']}
    YOUTUBE TECHNICAL DEEP-DIVE: {yt_context}

    TASK: Write a 1,200-word 'Consensus Report'.
    1. H1 Title: Something catchy with 'Buzz' or 'Verdict'.
    2. Structure: Introduction, 'What the Crowd Says' (Reddit), 'What the Pros Say' (YouTube), and 'Sucheta’s Final Verdict'.
    3. Formatting: Use H2, H3, and bold key phrases.
    4. SEO: Include a Meta Description and 5 Keywords at the end.
    """
    response = model.generate_content(prompt)
    return response.text

# 5. EXECUTE THE ENGINE
# 5. THE CONTINUOUS WORKER LOOP
def run_buzz_engine():
    print("--- BuzzVerified Engine Waking Up ---")
    
    # Use the open Hacker News API instead!
    trend = get_hackernews_trends()

    if trend:
        print(f"Trending Topic Found: {trend['title']}")
        context = get_yt_context_automated(trend['title'])
        
        print("Generating Sucheta's Report...")
        article = generate_sucheta_article(trend, context)
        
        print("\n--- FINAL ARTICLE ---\n")
        print(article)
        
        # NOTE: Later, we will add the WordPress posting code here!
    else:
        print("No suitable trends found right now.")

# The "Heartbeat" that keeps the Docker container alive
if __name__ == "__main__":
    print("Sucheta Worker Booted Successfully. Entering background schedule.")
    
    while True:
        try:
            run_buzz_engine()
        except Exception as e:
            print(f"Engine encountered a critical fault: {e}")
        
        # Sleep for 4 hours (14400 seconds) before checking for the next trend
        print("Worker is going to sleep for 4 hours to respect API rate limits...")
        time.sleep(14400)