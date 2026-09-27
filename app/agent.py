# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

import json
from pathlib import Path

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

# Load Agent Engine resource name from deployment_metadata.json if present
deployment_metadata_file = Path(__file__).parent.parent / "deployment_metadata.json"
agent_engine_resource_name = None
agent_engine_id = "6613953317456314368"
if deployment_metadata_file.exists():
    try:
        with open(deployment_metadata_file, "r") as f:
            metadata = json.load(f)
            agent_engine_resource_name = metadata.get("remote_agent_runtime_id")
            if agent_engine_resource_name:
                agent_engine_id = agent_engine_resource_name.split("/")[-1]
    except Exception:
        pass

code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_resource_name
)


# WRITE: Callback to send session events to Memory Bank after each turn
async def generate_memories_callback(callback_context: CallbackContext):
    try:
        await callback_context.add_session_to_memory()
    except Exception:
        pass
    return None


# Memory service builder for deployment
def memory_bank_service_builder():
    return VertexAiMemoryBankService(
        project="qwiklabs-gcp-03-89266242dbeb",
        location="us-central1",
        agent_engine_id=agent_engine_id,
    )


from app.firestore_tools import (
    calculate_ftp_power_zones,
    calculate_training_zones,
    calculate_weekly_tss_and_recovery,
    find_nearby_training_places,
    geocode_address,
    get_outdoor_training_weather,
    get_recent_workouts,
    log_workout,
)

def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from app.a2ui_utils import a2ui_callback

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are TriCoach AI, an intelligent personal fitness and triathlon coach. "
        "You remember and track all user allergies, dietary restrictions, health conditions, training preferences, and goals across conversations. "
        "Always check recalled memories for user allergies or dietary restrictions before suggesting race nutrition plans, pre-workout meals, or recovery snacks, "
        "and proactively acknowledge and respect any known allergies in your recommendations. "
        "Use your tools to check real-time outdoor weather, locate nearby gyms/parks/pools, geocode addresses, check workout history, "
        "calculate training stress & recovery, compute heart rate & power zones, log workout sessions in Firestore, generate short training videos, and execute Python code in your sandbox for complex data analysis."
    ),
    workflow_description="Analyze the request, use tools as needed, and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


from .video_tools import generate_workout_video

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
    tools=[
        PreloadMemoryTool(),
        get_current_time,
        get_outdoor_training_weather,
        get_recent_workouts,
        log_workout,
        calculate_training_zones,
        calculate_weekly_tss_and_recovery,
        calculate_ftp_power_zones,
        geocode_address,
        find_nearby_training_places,
        generate_workout_video,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
