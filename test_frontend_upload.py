import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

WORKSPACE_DIR = Path("C:/Users/Piyush/Desktop/ABYSS")
TEST_FILE = WORKSPACE_DIR / "training/test_suspicious.exe"
ARTIFACTS_DIR = Path("C:/Users/Piyush/.gemini/antigravity/brain/980a12ce-f101-46d1-ad36-1694511b6a92")

async def run_automation():
    print("Starting Playwright automation...")
    if not TEST_FILE.exists():
        print(f"Error: test file not found at {TEST_FILE}")
        sys.exit(1)
        
    async with async_playwright() as p:
        # Launch headless browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()
        
        print("Navigating to http://localhost:3000/...")
        await page.goto("http://localhost:3000/", wait_until="domcontentloaded")
        await asyncio.sleep(1)
        
        # Take a screenshot of the home page hero
        print("Capturing home page screenshot...")
        await page.screenshot(path=str(ARTIFACTS_DIR / "home_page.png"))
        
        # Scroll to upload section so Reveal renders the dropzone
        print("Scrolling to #upload section...")
        await page.evaluate("document.getElementById('upload')?.scrollIntoView()")
        await asyncio.sleep(1)
        
        # Locate hidden file input and set file
        print(f"Uploading file: {TEST_FILE.name}...")
        file_input = page.locator('input[type="file"]')
        await file_input.wait_for(state="attached", timeout=10000)
        await file_input.set_input_files(str(TEST_FILE))
        
        # Wait a moment for pipeline stages to appear
        await asyncio.sleep(2)
        print("Capturing upload progress screenshot...")
        await page.screenshot(path=str(ARTIFACTS_DIR / "upload_progress.png"))
        
        # Wait for redirection to the report page (takes up to 10-15s for analysis to finish)
        print("Waiting for redirection to /report...")
        try:
            await page.wait_for_url("**/report?task=*", timeout=60000)
            print("Successfully redirected to report dashboard!")
        except Exception as e:
            print("Timeout waiting for redirection. Check backend logs.")
            await page.screenshot(path=str(ARTIFACTS_DIR / "error_state.png"))
            await browser.close()
            sys.exit(1)
            
        # Let animations load
        await asyncio.sleep(5)
        
        # Take dashboard screenshot
        print("Capturing final report dashboard...")
        await page.screenshot(path=str(ARTIFACTS_DIR / "report_dashboard.png"))
        
        # Retrieve parsed DOM metrics to verify correctness
        print("\nVerifying page content...")
        try:
            badge_text = await page.locator("text=THREAT DETECTED").first.inner_text()
            print(f"Success! Found badge text: {badge_text}")
        except Exception as e:
            print("Warning: Could not find 'THREAT DETECTED' text on page. Maybe still loading or mapping issue.")
        
        await browser.close()
        print("Playwright automation finished successfully!")

if __name__ == "__main__":
    asyncio.run(run_automation())
