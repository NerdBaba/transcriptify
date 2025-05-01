# app.py
import os
from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled, VideoUnavailable
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

# --- Proxy Configuration ---
# Read the proxy URL from environment variables
# Render will inject this value if you set it in the service's Environment settings.
PROXY_URL = os.environ.get('YOUTUBE_API_PROXY') # Use None if not set

def get_proxy_config():
    """Returns the proxy dictionary if PROXY_URL is set, otherwise None."""
    if PROXY_URL:
        # The youtube-transcript-api expects a dictionary like {'https': 'proxy_url'}
        # IMPORTANT: This specific proxy structure "https://.../?destination=https://"
        # is unusual for standard proxy settings. It might work if the underlying
        # library (likely 'requests') handles it, or if the proxy server is designed
        # to interpret the full URL passed this way. Test thoroughly.
        app.logger.info(f"Using proxy for YouTube API: {PROXY_URL}")
        return {"https": PROXY_URL}
    return None
# --- End Proxy Configuration ---


def extract_video_id(video_input):
    """Extracts YouTube video ID from URL or returns string if it's likely already an ID."""
    if not video_input:
        return None

    # Check if it looks like a valid video ID (11 characters, alphanumeric + '-' + '_')
    # This is a basic check, could be more robust.
    is_potential_id = len(video_input) == 11 and all(c.isalnum() or c in '-_' for c in video_input)

    try:
        parsed_url = urlparse(video_input)
        # Handle standard youtube.com watch URLs
        if parsed_url.netloc in ('www.youtube.com', 'youtube.com', 'm.youtube.com') and parsed_url.path == '/watch':
            query_params = parse_qs(parsed_url.query)
            if 'v' in query_params and len(query_params['v'][0]) == 11:
                return query_params['v'][0]
        # Handle short youtu.be URLs
        elif parsed_url.netloc == 'youtu.be':
            video_id = parsed_url.path[1:]
            if len(video_id) == 11:
                return video_id
        # Handle youtube.com/embed URLs
        elif parsed_url.netloc in ('www.youtube.com', 'youtube.com') and parsed_url.path.startswith('/embed/'):
             video_id = parsed_url.path.split('/')[2]
             if len(video_id) == 11:
                 return video_id
        # Handle youtube.com/shorts URLs
        elif parsed_url.netloc in ('www.youtube.com', 'youtube.com') and parsed_url.path.startswith('/shorts/'):
             video_id = parsed_url.path.split('/')[2]
             if len(video_id) == 11:
                 return video_id

    except Exception as e:
        app.logger.warning(f"URL parsing failed for {video_input}: {e}")
        # If parsing fails, it might still be a raw ID if it matches the format
        if is_potential_id:
            return video_input
        return None # Parsing failed and it doesn't look like an ID

    # If it wasn't a recognized URL structure, return it only if it looks like an ID
    if is_potential_id:
        return video_input

    return None # Return None if no ID could be reasonably extracted


# Define endpoint: e.g., /transcript?video_id=VIDEO_ID or /transcript?video_url=YOUTUBE_URL
@app.route('/transcript', methods=['GET'])
def get_transcript():
    video_id_or_url = request.args.get('video_id') or request.args.get('video_url')

    if not video_id_or_url:
        return jsonify({"error": "Missing 'video_id' or 'video_url' query parameter"}), 400

    video_id = extract_video_id(video_id_or_url)

    if not video_id:
         return jsonify({"error": f"Could not extract a valid video ID from '{video_id_or_url}'"}), 400

    # Get proxy configuration
    proxies = get_proxy_config()

    try:
        # Fetch the transcript, passing the proxies if configured
        app.logger.info(f"Fetching transcript for video ID: {video_id}")
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, proxies=proxies)

        # transcript_list is a list of dictionaries: [{'text': '...', 'start': ..., 'duration': ...}, ...]
        return jsonify({
            "video_id": video_id,
            "transcript": transcript_list
        })

    except TranscriptsDisabled:
        app.logger.warning(f"Transcripts disabled for video ID: {video_id}")
        return jsonify({"error": f"Transcripts are disabled for video ID: {video_id}"}), 404
    except NoTranscriptFound as e:
        app.logger.warning(f"No transcript found for {video_id}: {e}")
        return jsonify({"error": f"No suitable transcript found for video ID: {video_id}. Details: {str(e)}"}), 404
    except VideoUnavailable:
         app.logger.warning(f"Video unavailable: {video_id}")
         return jsonify({"error": f"Video {video_id} is unavailable."}), 404
    except Exception as e:
        # Catch other potential errors (including proxy connection errors)
        app.logger.error(f"An unexpected error occurred for video ID {video_id}: {e}", exc_info=True) # Log traceback
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200

# Optional: Run for local testing
if __name__ == '__main__':
    # Set proxy locally for testing if needed (won't affect Render)
    # os.environ['YOUTUBE_API_PROXY'] = "https://simple-proxy.mda2233.workers.dev/?destination=https://"
    # PROXY_URL = os.environ.get('YOUTUBE_API_PROXY') # Re-read after setting for local run

    # Use 0.0.0.0 to be accessible on your local network
    # Render uses gunicorn, so this part isn't used in production there
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=True)
