import requests
import time
from youtube_transcript_api import YouTubeTranscriptApi
from youtubesearchpython import VideosSearch
import google.generativeai as genai

# 1. SETUP CREDENTIALS
# We bypass Reddit credentials using the JSON method for now
genai.configure(api_key="YOUR_GEMINI_API_KEY")
model = genai.GenerativeModel('gemini-2.0-flash')

def get_reddit_trends_json(subreddit="HomeAutomation"):
    """Fetches trending posts and comments without an API Key."""
    headers = {'User-Agent': 'Mozilla/5.0 BuzzVerified/1.0 (US/UK Research Agent)'}
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=5"
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        posts = data['data']['children']
        
        for post in posts:
            p = post['data']
            # Only pick posts with actual discussion
            if p['num_comments'] > 15 and not p['is_self'] == False: 
                # Fetch comments for this specific post
                comment_url = f"https://www.reddit.com{p['permalink']}.json"
                c_response = requests.get(comment_url, headers=headers)
                c_data = c_response.json()
                # Reddit JSON returns a list: [PostData, CommentData]
                comments = [c['data'].get('body', '') for c in c_data[1]['data']['children'][:10]]
                
                return {
                    "title": p['title'],
                    "comments": [c for c in comments if len(c) > 50]
                }
    except Exception as e:
        print(f"Reddit Error: {e}")
    return None

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
print("--- BuzzVerified Engine Starting ---")
trend = get_reddit_trends_json("Technology")

if trend:
    print(f"Trending Topic Found: {trend['title']}")
    context = get_yt_context_automated(trend['title'])
    
    print("Generating Sucheta's Report...")
    article = generate_sucheta_article(trend, context)
    
    print("\n--- FINAL ARTICLE ---\n")
    print(article)
else:
    print("No suitable trends found today.")