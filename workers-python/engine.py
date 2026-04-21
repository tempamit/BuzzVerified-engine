import os
import time
import json
import requests
import urllib.parse
from bs4 import BeautifulSoup
from groq import Groq
from youtube_transcript_api import YouTubeTranscriptApi
from youtubesearchpython import VideosSearch

# 1. SETUP CREDENTIALS
groq_key = os.environ.get("GROQ_API_KEY")
wp_user = os.environ.get("WP_USERNAME")
wp_pass = os.environ.get("WP_APP_PASSWORD")

if not groq_key or not wp_user or not wp_pass:
    raise ValueError("CRITICAL: Missing API keys or WordPress credentials in Coolify!")

client = Groq(api_key=groq_key)
WP_BASE_URL = "https://buzzverified.com/wp-json/wp/v2"

# 2. WORDPRESS UTILITIES (Anti-Duplication & Images)
def check_duplicate_post(title):
    """Checks if a post with a similar title already exists on BuzzVerified."""
    print(f"Checking for duplicates: {title}")
    # Search the first 5 words to be safe
    search_query = urllib.parse.quote(" ".join(title.split()[:5]))
    url = f"{WP_BASE_URL}/posts?search={search_query}"
    
    try:
        response = requests.get(url, auth=(wp_user, wp_pass), timeout=10)
        if response.status_code == 200 and len(response.json()) > 0:
            print("Duplicate found! Skipping this topic.")
            return True
    except Exception as e:
        print(f"Duplicate check failed: {e}")
    return False

def upload_featured_image(image_url, fallback_title):
    """Downloads image from URL or generates one, then uploads to WP Media Library."""
    print("Acquiring Featured Image...")
    final_image_url = image_url
    
    # Fallback to AI generation if no source image exists
    if not final_image_url:
        print("No source image. Generating via AI...")
        safe_title = urllib.parse.quote(fallback_title)
        final_image_url = f"https://image.pollinations.ai/prompt/Tech%20news%20concept%20{safe_title}?width=1200&height=630&nologo=true"

    try:
        # Download the image bytes
        img_response = requests.get(final_image_url, stream=True, timeout=15)
        if img_response.status_code == 200:
            # Upload to WordPress
            media_url = f"{WP_BASE_URL}/media"
            headers = {
                'Content-Disposition': f'attachment; filename="buzz-featured-{int(time.time())}.jpg"',
                'Content-Type': 'image/jpeg'
            }
            upload_res = requests.post(
                media_url, 
                headers=headers, 
                data=img_response.content, 
                auth=(wp_user, wp_pass),
                timeout=20
            )
            if upload_res.status_code == 201:
                media_id = upload_res.json().get('id')
                print(f"Successfully uploaded Featured Image! Media ID: {media_id}")
                return media_id
    except Exception as e:
        print(f"Image upload failed: {e}")
    return None

# 3. DATA FETCHING (Hacker News + Image Scraper)
def get_hackernews_trends():
    """Fetches the #1 trending tech story, comments, and attempts to scrape the original image."""
    print("Connecting to open Hacker News API...")
    try:
        top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        story_ids = requests.get(top_stories_url, timeout=10).json()

        for story_id in story_ids[:5]: # Check the top 5 to find one that isn't a duplicate
            story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
            story = requests.get(story_url, timeout=10).json()
            title = story.get('title', 'Unknown Title')
            
            if check_duplicate_post(title):
                continue # Try the next story
            
            print(f"Found Fresh Top Story: {title}")
            target_url = story.get('url', '')
            source_image = None
            
            # Attempt to scrape the original article's featured image
            if target_url:
                try:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    page = requests.get(target_url, headers=headers, timeout=5)
                    soup = BeautifulSoup(page.content, 'html.parser')
                    og_image = soup.find('meta', property='og:image')
                    if og_image:
                        source_image = og_image['content']
                except:
                    pass # Silently fail and use AI fallback later

            # Fetch Comments
            comment_ids = story.get('kids', [])[:5]
            comments = []
            for cid in comment_ids:
                time.sleep(1)
                c_data = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{cid}.json", timeout=10).json()
                if c_data and 'text' in c_data:
                    clean_text = c_data['text'].replace('<p>', ' ').replace('&#x27;', "'").replace('&quot;', '"')
                    if len(clean_text) > 50:
                        comments.append(clean_text)

            return {
                "title": title,
                "comments": comments,
                "image_url": source_image
            }
    except Exception as e:
        print(f"Hacker News Error: {e}")
    return None

def get_yt_context_automated(query):
    try:
        search = VideosSearch(query + " review", limit=1)
        result = search.result()['result']
        if not result: return "No relevant video found."
        video_id = result[0]['id']
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t['text'] for t in transcript_list])
    except Exception:
        return "YouTube Context Unavailable."

# 4. LLM GENERATOR (Strict SEO, JSON formatting, AI Bypass)
def generate_sucheta_article(trend_data, yt_context):
    prompt = f"""
    You are an expert, veteran tech journalist. Write a comprehensive 'Consensus Report' for a US/UK audience.
    
    TOPIC: {trend_data['title']}
    FORUM VOICES: {trend_data['comments']}
    YOUTUBE TECHNICAL DEEP-DIVE: {yt_context}

    CRITICAL RULES FOR BYPASSING AI DETECTION:
    - DO NOT use words like: delve, furthermore, overarching, testament, utilize, crucial, landscape, tapestry.
    - Keep vocabulary simple (9th-grade reading level), but keep the tone formal and authoritative.
    - Vary sentence lengths drastically. Use some very short punchy sentences. Follow them with longer conversational ones.
    
    CONTENT REQUIREMENTS:
    1. Executive TL;DR: 3 bullet points at the very top.
    2. The Buzz Score: A bold sentiment analysis (e.g., "The Internet's Verdict: 70% Hyped, 30% Skeptical").
    3. H2 and H3 tags to structure the flow (Intro, What the Crowd Says, What the Pros Say, Final Verdict).
    4. RECEIPTS: You MUST embed at least 2 direct, verbatim quotes from the 'FORUM VOICES' using HTML <blockquote> tags.

    OUTPUT FORMAT: You must return ONLY a valid JSON object with the following exact keys:
    {{
        "seo_title": "Catchy H1 title including the focus keyword",
        "focus_keyword": "2-3 word keyword",
        "meta_description": "150 character engaging description",
        "article_html": "The full formatted HTML content of the article (do not include the H1 title in here, start with the TL;DR)"
    }}
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            response_format={"type": "json_object"} # Forces Groq to return pure JSON
        )
        return json.loads(chat_completion.choices[0].message.content)
    except Exception as e:
        print(f"Groq API Error: {e}")
        return None

# 5. THE CONTINUOUS WORKER LOOP
def run_buzz_engine():
    print("\n--- BuzzVerified Engine Waking Up ---")
    
    trend = get_hackernews_trends()

    if trend:
        context = get_yt_context_automated(trend['title'])
        
        # 1. Generate the Image
        media_id = upload_featured_image(trend['image_url'], trend['title'])
        
        # 2. Generate the Article via LLM
        print("Drafting article via Groq (JSON Mode)...")
        article_data = generate_sucheta_article(trend, context)
        
        if not article_data:
            return print("Failed to generate article data.")

        # 3. Post to WordPress
        print("Publishing to BuzzVerified...")
        
        # Append SEO Metadata cleanly to the bottom of the content for plugins to read
        final_html = article_data['article_html'] + f"\n\n<hr><p><small><strong>Focus Keyword:</strong> {article_data['focus_keyword']}</small></p>"

        wp_payload = {
            "title": article_data['seo_title'],
            "content": final_html,
            "excerpt": article_data['meta_description'], # WP natively uses excerpt for meta description
            "status": "publish"
        }
        
        if media_id:
            wp_payload["featured_media"] = media_id

        try:
            response = requests.post(
                f"{WP_BASE_URL}/posts",
                auth=(wp_user, wp_pass),
                json=wp_payload,
                timeout=15
            )
            if response.status_code == 201:
                print(f"SUCCESS! Article published: {article_data['seo_title']}")
            else:
                print(f"WordPress Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Critical WordPress Connection Error: {e}")
            
    else:
        print("No suitable/fresh trends found right now.")

# 6. SERVER HEARTBEAT
if __name__ == "__main__":
    print("Sucheta Worker Booted Successfully. Entering strictly paced background schedule.")
    
    while True:
        try:
            run_buzz_engine()
        except Exception as e:
            print(f"Engine encountered a critical fault: {e}")
        
        # EXACT PACING: 10 posts per 24 hours = 1 post every 8,640 seconds
        print("\nWorker is going to sleep for 2.4 hours to maintain editorial pacing...")
        time.sleep(8640)