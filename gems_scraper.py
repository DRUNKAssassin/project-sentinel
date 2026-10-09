import os
import json
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from google.genai import types
from dotenv import load_dotenv

# --- CONFIGURATION ---
# Define what the agent should search for on YouTube
SEARCH_QUERY = "Kashmir offbeat hidden gems travel vlog"
MAX_VIDEOS_TO_CHECK = 5 # How many recent videos to look at per run
TRACKING_FILE = "processed_links.txt"

# 1. Exact folder path resolution for .env
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
print(f"--- DEBUG: Looking for .env file exactly here: {env_path} ---")
load_dotenv(dotenv_path=env_path)

# --- API KEYS ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError(f"GEMINI_API_KEY not found! Please check {env_path}")

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    print("⚠️ WARNING: YOUTUBE_API_KEY not found in .env! You need this for autonomous searching.")

client = genai.Client(api_key=GEMINI_API_KEY)

# --- AUTONOMOUS AGENT FUNCTIONS ---

def get_processed_videos():
    """Reads the tracking file to remember which videos we've already scraped."""
    if not os.path.exists(TRACKING_FILE):
        return set()
    with open(TRACKING_FILE, 'r') as f:
        # Returns a set of video IDs
        return set(line.strip() for line in f.readlines())

def mark_video_processed(video_id):
    """Saves a successfully scraped video ID to the tracking file."""
    with open(TRACKING_FILE, 'a') as f:
        f.write(f"{video_id}\n")

def search_new_youtube_videos(query, max_results=5):
    """Asks YouTube for the latest videos matching our search term."""
    print(f"\n🔍 Searching YouTube for new videos: '{query}'...")
    if not YOUTUBE_API_KEY:
        print("❌ Missing YouTube API Key. Cannot perform search.")
        return []

    # Call the raw YouTube Data API v3
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&order=date&maxResults={max_results}&q={requests.utils.quote(query)}&key={YOUTUBE_API_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if 'error' in data:
            print(f"❌ YouTube API Error: {data['error']['message']}")
            return []
            
        video_ids = [item['id']['videoId'] for item in data.get('items', [])]
        print(f"✅ Found {len(video_ids)} recent videos on YouTube.")
        return video_ids
        
    except Exception as e:
        print(f"❌ Error communicating with YouTube API: {e}")
        return []

# --- CORE EXTRACTION PIPELINE ---

def get_youtube_transcript(video_id):
    print(f"Fetching transcript for video ID: {video_id}")
    try:
        ytt_api = YouTubeTranscriptApi()
        available_transcripts = ytt_api.list(video_id)
        transcript = available_transcripts.find_transcript(['en', 'hi', 'ur', 'en-IN', 'hi-IN'])
        transcript_data = transcript.fetch()
        
        # Combine all the text blocks into one giant string.
        full_text = " ".join([item.text for item in transcript_data])
        print("✅ Transcript successfully downloaded!")
        return full_text
    except Exception as e:
        print(f"⚠️ Error fetching transcript (might not have subtitles): {e}")
        return None

def extract_hidden_gems_with_gemini(transcript_text):
    print("🧠 Sending transcript to Gemini for analysis (Using Gemini 3.5 Flash-Lite)...")
    
    system_instruction = """
    You are an expert data extraction AI for a travel application. 
    Your job is to read the provided video transcript and extract any "Hidden Gems" or offbeat travel locations mentioned, specifically focusing on Jammu & Kashmir if applicable.
    
    CRITICAL INSTRUCTION: The transcript provided may be in Hindi, English, or a mix of both (Hinglish). 
    You must comprehend the local language, but translate all your extracted answers into English before formatting them into the JSON schema.
    
    You must extract the data and format it exactly according to the following JSON schema. 
    If a specific piece of information (like food or places to stay) is not mentioned, use "Not mentioned in video".
    If no locations are mentioned at all, return an empty array [].
    
    Required JSON Array format:
    [
      {
        "name": "Name of the location/gem",
        "location": "General region or district",
        "description": "A 1-2 sentence summary of why it's special based on the transcript",
        "tags": "2-3 relevant tags (e.g., Offbeat, Trekking, Viewpoint)",
        "placesToStay": "Any hotels, homestays, or camps mentioned",
        "food": "Any specific local food mentioned",
        "mustVisit": "Any specific spots or landmarks mentioned nearby"
      }
    ]
    """

    try:
        chat = client.chats.create(
            model='gemini-3.5-flash-lite',
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        response = chat.send_message(transcript_text)
        return response.text
        
    except Exception as e:
        print(f"❌ Error calling Gemini API: {e}")
        return None

def push_to_google_sheets(extracted_data):
    """Connects to our custom Google Apps Script Webhook"""
    if not extracted_data:
        print("ℹ️ No gems found in this video to push.")
        return True # Return true so we still mark the video as processed
        
    print("\n--- Connecting to Google Sheets Webhook ---")
    webhook_url = "https://script.google.com/macros/s/AKfycbwNYOeXSmLCgOG4QqZvg_niNAU9TITPTZbVNRYA2uXsFzyz7BuY25BeMuvBPmF5du9o/exec"
    
    try:
        response = requests.post(webhook_url, json=extracted_data)
        if response.text == "Success":
            print("🎉 SUCCESS: Data pushed to Google Sheets instantly!")
            return True
        else:
            print(f"⚠ Google Sheets responded with: {response.text}")
            return False
    except Exception as e:
        print(f"❌ ERROR pushing to Sheets: {e}")
        return False

# --- MAIN ORCHESTRATION LOOP ---

def main():
    print("==================================================")
    print("🚀 Project Sentinel: Autonomous Web Scraper Booting")
    print("==================================================")
    
    # 1. See what we've already done
    processed_videos = get_processed_videos()
    print(f"📚 Database Memory: {len(processed_videos)} videos already processed.")
    
    # 2. Get fresh videos from YouTube
    new_video_ids = search_new_youtube_videos(SEARCH_QUERY, MAX_VIDEOS_TO_CHECK)
    
    if not new_video_ids:
        print("No videos found to process. Exiting.")
        return

    videos_processed_this_run = 0

    # 3. Process them one by one
    for video_id in new_video_ids:
        if video_id in processed_videos:
            print(f"⏭️ Skipping video {video_id} - Already processed.")
            continue
            
        print(f"\n--------------------------------------------------")
        print(f"🎥 Processing New Video: https://youtube.com/watch?v={video_id}")
        
        transcript = get_youtube_transcript(video_id)
        if not transcript:
            # Mark it as processed anyway so we don't keep trying and failing on a video with no subtitles
            mark_video_processed(video_id) 
            continue
            
        json_result = extract_hidden_gems_with_gemini(transcript)
        
        if json_result:
            try:
                parsed_json = json.loads(json_result)
                print(f"💡 Gemini extracted {len(parsed_json)} potential gems.")
                
                # Push to sheets
                success = push_to_google_sheets(parsed_json)
                
                # If everything worked, save it to our tracker so we never process it again
                if success:
                    mark_video_processed(video_id)
                    videos_processed_this_run += 1
                    
            except json.JSONDecodeError:
                print("❌ Failed to parse Gemini output as JSON.")
        else:
            print("❌ Failed to extract data.")

    print(f"\n==================================================")
    print(f"✅ Scraping Run Complete. Processed {videos_processed_this_run} new videos.")
    print("==================================================")

if __name__ == "__main__":
    main()