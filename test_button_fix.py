import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ARTIFACTS_DIR = Path(r"C:\Users\Piyush\.gemini\antigravity\brain\980a12ce-f101-46d1-ad36-1694511b6a92")

async def test_cta():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        
        print("Navigating to http://localhost:3000/...")
        await page.goto("http://localhost:3000/", wait_until="networkidle")
        await asyncio.sleep(1)
        
        print("Scrolling to bottom CTA section...")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1)
        
        print("Capturing CTA button screenshot...")
        await page.screenshot(path=str(ARTIFACTS_DIR / "cta_button_fixed.png"))
        
        await browser.close()
        print("CTA button test complete!")

if __name__ == "__main__":
    asyncio.run(test_cta())
