import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ARTIFACTS_DIR = Path(r"C:\Users\Piyush\.gemini\antigravity\brain\980a12ce-f101-46d1-ad36-1694511b6a92")

async def test_report_telemetry():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 1200})
        
        # Open a sample report page
        url = "http://localhost:3000/report?task=3e0b7a74-1a7c-4bc0-95ed-aa95d47d6629"
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(1.5)
        
        print("Capturing full report dashboard with telemetry stream...")
        await page.screenshot(path=str(ARTIFACTS_DIR / "telemetry_terminal_report_dashboard.png"), full_page=True)
        
        await browser.close()
        print("Report dashboard telemetry test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_report_telemetry())
