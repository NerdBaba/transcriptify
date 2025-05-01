# app.py
import os
from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled, VideoUnavailable
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

def extract_video_id(video_input):
    """Extracts YouTube video ID from URL or returns string if it's likely already an ID."""
    if not video_input:
        return None

    # Check if it looks like a valid video ID (11 characters, alphanumeric + '-' + '_')
    if len(video_input) == 11 and video_input.isalnum() or '-' in video_input or '_' in video_input:
         # Basic check, could be more robust but often sufficient
         # Re-check if it's part of a common URL structure even if it looks like an ID
         pass # Fall through to URL parsing just in case
    
    try:
        parsed_url = urlparse(video_input)
        if parsed_url.netloc in ['www.youtube.com', 'youtube.com'] and parsed_url.path == '/watch':
            query_params = parse_qs(parsed_url.query)
            if 'v' in query_params:
                return query_params['v'][0]
        elif parsed_url.netloc == 'youtu.be':
            # Path is like '/VIDEO_ID'
            return parsed_url.path[1:]
    except Exception:
        # If parsing fails, it might still be a raw ID
        pass
        
    # If it wasn't a recognizable URL, assume it might be a raw ID after all
    if len(video_input) == 11: # Re-check length for potential raw IDs
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

    try:
        # Fetch the transcript
        # You can specify languages if needed: transcript_list = YouTubeTranscriptApi.list_transcripts(video_id).find_generated_transcript(['en', 'es']).fetch()
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

        # transcript_list is a list of dictionaries: [{'text': '...', 'start': ..., 'duration': ...}, ...]
        return jsonify({
            "video_id": video_id,
            "transcript": transcript_list
        })

    except TranscriptsDisabled:
        return jsonify({"error": f"Transcripts are disabled for video ID: {video_id}"}), 404
    except NoTranscriptFound as e:
        # This exception includes details about available languages if needed
        app.logger.error(f"No transcript found for {video_id}: {e}")
        return jsonify({"error": f"No suitable transcript found for video ID: {video_id}. Details: {str(e)}"}), 404
    except VideoUnavailable:
         return jsonify({"error": f"Video {video_id} is unavailable."}), 404
    except Exception as e:
        # Catch other potential errors from the library or network issues
        app.logger.error(f"An unexpected error occurred for video ID {video_id}: {e}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200

# Optional: Run for local testing
if __name__ == '__main__':
    # Use 0.0.0.0 to be accessible on your local network
    # Render uses gunicorn, so this part isn't used in production there
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=True)
    # Using PORT env variable like Render does, defaulting to 8080 locally if not set
