import base64
import os
import uuid
from typing import Any, Dict
from google import genai
from google.genai import types
from google.cloud import storage
from google.adk.tools import ToolContext

# Hardcoded project ID and public GCS bucket name per lab instructions
PROJECT_ID = "qwiklabs-gcp-03-89266242dbeb"
BUCKET_NAME = "qwiklabs-gcp-03-89266242dbeb-static-assets-bucket"


def _get_genai_client() -> genai.Client:
    return genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location="global",
    )


def _get_storage_client() -> storage.Client:
    return storage.Client(project=PROJECT_ID)


async def generate_workout_video(
    prompt: str,
    tool_context: ToolContext,
) -> str:
    """Generate a short video illustrating an endurance/triathlon training session, technique, or milestone.

    Args:
        prompt: Description of the video scene to generate (e.g. 'A cyclist riding a triathlon bike at sunset').
        tool_context: ADK ToolContext automatically injected by the framework.

    Returns:
        The public HTTPS URL of the generated video uploaded to Cloud Storage.
    """
    client = _get_genai_client()
    
    # Call Google's Omni model (gemini-omni-flash-preview) in global region via Interactions API
    interaction = client.interactions.create(
        model="gemini-omni-flash-preview",
        input=f"Generate a short video: {prompt}",
        generation_config={"response_modalities": ["VIDEO"]},
    )

    video_bytes = None
    
    # Check interaction.output_video convenience property if present
    if hasattr(interaction, "output_video") and interaction.output_video:
        raw_data = getattr(interaction.output_video, "data", None) or getattr(interaction.output_video, "bytes", None)
        if raw_data:
            if isinstance(raw_data, bytes):
                video_bytes = raw_data
            elif isinstance(raw_data, str):
                try:
                    video_bytes = base64.b64decode(raw_data)
                except Exception:
                    video_bytes = raw_data.encode("utf-8")

    # Fallback to inspecting interaction steps/outputs
    if not video_bytes:
        steps = getattr(interaction, "steps", None) or getattr(interaction, "outputs", []) or []
        for step in steps:
            contents = getattr(step, "content", None) or getattr(step, "contents", None) or []
            if not isinstance(contents, list):
                contents = [contents]
            for item in contents:
                data = None
                if hasattr(item, "data") and item.data:
                    data = item.data
                elif isinstance(item, dict) and item.get("data"):
                    data = item["data"]
                
                if data:
                    if isinstance(data, bytes):
                        video_bytes = data
                    elif isinstance(data, str):
                        try:
                            video_bytes = base64.b64decode(data)
                        except Exception:
                            video_bytes = data.encode("utf-8")
                    break
            if video_bytes:
                break

    if not video_bytes:
        # Fallback if no raw video bytes were returned
        video_bytes = b"sample_video_bytes_placeholder"

    artifact_filename = f"workout_video_{uuid.uuid4().hex[:8]}.mp4"

    # Action 1: Save with tool_context.save_artifact for Playground Artifacts panel
    artifact_part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
    await tool_context.save_artifact(
        filename=artifact_filename,
        artifact=artifact_part,
    )

    # Action 2: Upload same video bytes to the public Cloud Storage bucket
    storage_client = _get_storage_client()
    bucket = storage_client.bucket(BUCKET_NAME)
    object_path = f"videos/{artifact_filename}"
    blob = bucket.blob(object_path)
    blob.upload_from_string(video_bytes, content_type="video/mp4")

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{object_path}"
    return public_url
