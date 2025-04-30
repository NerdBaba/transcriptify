import json
from youtube_transcript_api import YouTubeTranscriptApi

def handler(event, context):
    """
    Netlify function handler. Takes a YouTube video ID and returns the transcript.
    """
    try:
        # Get the video ID from the query parameters
        video_id = event.get("queryStringParameters", {}).get("id")
        if not video_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing 'id' query parameter."}),
            }

        # Fetch the transcript
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript(['en'])  # Or handle multiple languages
        transcript_data = transcript.fetch()

        # Return the transcript as JSON
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(transcript_data),
        }

    except Exception as e:
        print(f"Transcript fetch error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Failed to fetch transcript: {e}"}),
        }
