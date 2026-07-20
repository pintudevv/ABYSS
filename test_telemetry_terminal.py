import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ARTIFACTS_DIR = Path(r"C:\Users\Piyush\.gemini\antigravity\brain\980a12ce-f101-46d1-ad36-1694511b6a92")

async def test_telemetry():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 950})
        
        print("Navigating to http://localhost:3000/...")
        await page.goto("http://localhost:3000/", wait_until="networkidle")
        await asyncio.sleep(1)
        
        print("Scrolling to #upload section...")
        await page.evaluate("document.querySelector('#upload').scrollIntoView()")
        await asyncio.sleep(1)
        
        file_input = page.locator("input[type='file']")
        test_file = Path(r"C:\Users\Piyush\Desktop\ABYSS\training\test_suspicious.exe")
        print(f"Uploading file: {test_file.name}...")
        await file_input.set_input_files(str(test_file))
        
        await asyncio.sleep(1)
        print("Capturing live telemetry terminal stream screenshot...")
        await page.screenshot(path=str(ARTIFACTS_DIR / "telemetry_terminal_live.png"))
        
        # Wait a bit for progress
        await asyncio.sleep(2)
        await page.screenshot(path=str(ARTIFACTS_DIR / "telemetry_terminal_progress.png"))
        
        await browser.close()
        print("Telemetry terminal automation test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_telemetry())
