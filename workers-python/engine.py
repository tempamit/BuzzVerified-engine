import requests
import time
from youtube_transcript_api import YouTubeTranscriptApi
from youtubesearchpython import VideosSearch
import os
import google.generativeai as genai

# Read from Coolify Environment Variables
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in Environment Variables!")

genai.configure(api_key=api_key)

# 1. SETUP CREDENTIALS
# We bypass Reddit credentials using the JSON method for now
genai.configure(api_key="YOUR_GEMINI_API_KEY")
model = genai.GenerativeModel('gemini-2.0-flash')

def get_reddit_trends_json(subreddit="HomeAutomation"):
    """Fetches trending posts and comments without an API Key."""
    
    # We must look like a standard Windows Chrome browser to bypass the VPS block
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=5"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # Check exactly what Reddit sent back
        if response.status_code != 200:
            print(f"Reddit blocked us! Status: {response.status_code}")
            # Print the first 100 characters of the block page to be sure
            print(f"Response: {response.text[:100]}")
            return None
            
        data = response.json()
        posts = data['data']['children']
        
        for post in posts:
            p = post['data']
            if p.get('num_comments', 0) > 15 and not p.get('is_self') == False: 
                comment_url = f"https://www.reddit.com{p['permalink']}.json"
                
                # Sleep for 2 seconds before hitting the comments to act 'human'
                time.sleep(2) 
                
                c_response = requests.get(comment_url, headers=headers, timeout=10)
                if c_response.status_code == 200:
                    c_data = c_response.json()
                    comments = [c['data'].get('body', '') for c in c_data[1]['data']['children'][:10]]
                    
                    return {
                        "title": p['title'],
                        "comments": [c for c in comments if len(c) > 50]
                    }
    except Exception as e:
        print(f"Reddit Error: {e}")
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
    
    # We pass 'HomeAutomation' or 'Technology' here
    trend = get_reddit_trends_json("Technology")

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