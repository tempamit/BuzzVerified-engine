import os
import time
import requests
from groq import Groq
from youtube_transcript_api import YouTubeTranscriptApi
from youtubesearchpython import VideosSearch

# 1. SETUP CREDENTIALS
groq_key = os.environ.get("GROQ_API_KEY")
wp_user = os.environ.get("WP_USERNAME")
wp_pass = os.environ.get("WP_APP_PASSWORD")

if not groq_key or not wp_user or not wp_pass:
    raise ValueError("CRITICAL: Missing API keys or WordPress credentials in Coolify!")


# Initialize the Groq Client
client = Groq(api_key=groq_key)

# 2. HACKER NEWS FETCHER
def get_hackernews_trends():
    """Fetches the #1 trending tech story from Hacker News (Zero API Keys required)."""
    print("Connecting to open Hacker News API...")
    
    try:
        top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        story_ids = requests.get(top_stories_url, timeout=10).json()

        top_story_id = story_ids[0]
        story_url = f"https://hacker-news.firebaseio.com/v0/item/{top_story_id}.json"
        story = requests.get(story_url, timeout=10).json()

        title = story.get('title', 'Unknown Title')
        print(f"Found Top Story: {title}")
        
        comment_ids = story.get('kids', [])[:5]
        comments = []
        
        for cid in comment_ids:
            time.sleep(1) # Be polite to the API
            c_url = f"https://hacker-news.firebaseio.com/v0/item/{cid}.json"
            c_data = requests.get(c_url, timeout=10).json()
            
            if c_data and 'text' in c_data:
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

# 3. YOUTUBE CONTEXT FETCHER
def get_yt_context_automated(query):
    """Automatically finds the top video and fetches its transcript."""
    try:
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

# 4. LLM GENERATOR (Now using Groq & Llama 3)
def generate_sucheta_article(trend_data, yt_context):
    """The Brain: Synthesizes data into Sucheta's persona using Groq."""
    prompt = f"""
    You are Sucheta, a tech veteran with 20 years of experience. Write for a US/UK audience.
    SYSTEM ROLE: Agentic Research Analyst for BuzzVerified.com.

    TOPIC: {trend_data['title']}
    FORUM VOICES: {trend_data['comments']}
    YOUTUBE TECHNICAL DEEP-DIVE: {yt_context}

    TASK: Write a 1,200-word 'Consensus Report'.
    1. H1 Title: Something catchy with 'Buzz' or 'Verdict'.
    2. Structure: Introduction, 'What the Crowd Says' (Forums), 'What the Pros Say' (YouTube), and 'Sucheta’s Final Verdict'.
    3. Formatting: Use H2, H3, and bold key phrases.
    4. SEO: Include a Meta Description and 5 Keywords at the end.
    """
    
    try:
        # Using Llama 3.3 70B - an incredibly powerful, open-weights model
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Groq API Error: {e}"

def post_to_wordpress(title, content):
    """Pushes the final article directly to BuzzVerified.com"""
    print(f"Attempting to post to BuzzVerified: {title}")
    
    url = "https://buzzverified.com/wp-json/wp/v2/posts"
    
    # We format the payload for WordPress
    data = {
        "title": f"The Consensus: {title}",
        "content": content,
        "status": "publish" # Change to "draft" if you want to review them manually first!
    }
    
    try:
        response = requests.post(
            url,
            auth=(wp_user, wp_pass),
            json=data,
            timeout=15
        )
        
        if response.status_code == 201:
            print(f"SUCCESS! Article published to BuzzVerified.")
        else:
            print(f"WordPress Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Critical WordPress Connection Error: {e}")

# 5. THE CONTINUOUS WORKER LOOP
def run_buzz_engine():
    print("--- BuzzVerified Engine Waking Up ---")
    
    trend = get_hackernews_trends()

    if trend:
        context = get_yt_context_automated(trend['title'])
        
        print("Generating Sucheta's Report via Groq...")
        article = generate_sucheta_article(trend, context)
        
        print("\n--- FINAL ARTICLE GENERATED ---\n")
        
        # ACTUALLY POST IT TO THE WEBSITE!
        post_to_wordpress(trend['title'], article)
        
    else:
        print("No suitable trends found right now.")

# 6. SERVER HEARTBEAT
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