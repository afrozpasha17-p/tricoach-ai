import asyncio
from dotenv import load_dotenv
load_dotenv()

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from app.agent import app

async def main():
    session_service = InMemorySessionService()
    runner = Runner(app=app, session_service=session_service)
    session = await session_service.create_session(app_name="app", user_id="user1")
    
    prompt = "Can you calculate my training stress score (TSS) and check my recovery status based on my recent Firestore workouts for user1?"
    print(f"User: {prompt}\n")
    print("Agent: ", end="")
    
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)]
    )
    
    async for event in runner.run_async(user_id="user1", session_id=session.id, new_message=content):
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(part.text, end="", flush=True)
    print("\n")

if __name__ == "__main__":
    asyncio.run(main())
