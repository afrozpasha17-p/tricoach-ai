import asyncio
import os
import shutil
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright

RECORDING_DIR = Path("/config/.gemini/antigravity/scratch/tricoach-ai/demo_recordings")
FINAL_VIDEO_PATH = Path("/config/.gemini/antigravity/scratch/tricoach-ai/demo_video.mp4")

async def record_demo():
    if RECORDING_DIR.exists():
        shutil.rmtree(RECORDING_DIR)
    RECORDING_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        print("Launching Chromium browser with video recording...")
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=str(RECORDING_DIR),
            record_video_size={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        print("Navigating to http://localhost:8080/ ...")
        await page.goto("http://localhost:8080/", wait_until="networkidle")
        await asyncio.sleep(2)

        # --- Prompt 1: Core Capabilities ---
        prompt_1 = "What can you do for my triathlon training?"
        print(f"Sending Prompt 1: '{prompt_1}'")
        await page.fill("#input", prompt_1)
        await asyncio.sleep(1)
        await page.click("button[type='submit']")

        # Wait for agent response 1
        print("Waiting for agent response to Prompt 1...")
        await page.wait_for_function("document.querySelectorAll('.msg.agent').length > 1", timeout=60000)
        await asyncio.sleep(5)

        # --- Prompt 2: Rich prompt with tool calls (Workout logging + Nearby Facilities) ---
        prompt_2 = "Log a 45 min swim workout titled 'Morning Aerobic Intervals' with distance 2.5 km, and find nearby swimming pools in San Francisco!"
        print(f"Sending Prompt 2: '{prompt_2}'")
        await page.fill("#input", prompt_2)
        await asyncio.sleep(1)
        await page.click("button[type='submit']")

        # Wait for agent response 2
        print("Waiting for agent response to Prompt 2...")
        await page.wait_for_function("document.querySelectorAll('.msg.agent').length > 2", timeout=60000)
        await asyncio.sleep(7)

        # Get video path
        video_page = page.video
        video_path = await video_page.path() if video_page else None

        await context.close()
        await browser.close()
        print("Browser closed. Raw recording video path:", video_path)

        if video_path and os.path.exists(video_path):
            print(f"Copying video recording to {FINAL_VIDEO_PATH}...")
            shutil.copy(video_path, FINAL_VIDEO_PATH)
            # Convert to standard mp4 via ffmpeg
            try:
                converted_path = str(FINAL_VIDEO_PATH).replace(".mp4", "_converted.mp4")
                subprocess.run([
                    "ffmpeg", "-y", "-i", str(FINAL_VIDEO_PATH),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    converted_path
                ], check=True)
                shutil.move(converted_path, FINAL_VIDEO_PATH)
                print("FFmpeg encoding completed successfully!")
            except Exception as e:
                print(f"FFmpeg conversion notice ({e}), raw video file preserved.")

            print(f"Demo video recording complete: {FINAL_VIDEO_PATH}")

if __name__ == "__main__":
    asyncio.run(record_demo())
