import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ARTIFACTS_DIR = Path(r"C:\Users\Piyush\.gemini\antigravity\brain\980a12ce-f101-46d1-ad36-1694511b6a92")

async def test_bg():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        
        print("Navigating to http://localhost:3000/...")
        await page.goto("http://localhost:3000/", wait_until="networkidle")
        await asyncio.sleep(1)
        
        print("Capturing Hero section background animation...")
        await page.screenshot(path=str(ARTIFACTS_DIR / "bg_animation_hero.png"))
        
        print("Scrolling to #how-it-works section...")
        await page.evaluate("document.getElementById('how-it-works')?.scrollIntoView()")
        await asyncio.sleep(1)
        await page.screenshot(path=str(ARTIFACTS_DIR / "bg_animation_howitworks.png"))
        
        print("Scrolling to #architecture section...")
        await page.evaluate("document.getElementById('architecture')?.scrollIntoView()")
        await asyncio.sleep(1)
        await page.screenshot(path=str(ARTIFACTS_DIR / "bg_animation_mlstack.png"))
        
        print("Scrolling to #report section...")
        await page.evaluate("document.getElementById('report')?.scrollIntoView()")
        await asyncio.sleep(1)
        await page.screenshot(path=str(ARTIFACTS_DIR / "bg_animation_report.png"))
        
        await browser.close()
        print("Global background animation test complete!")

if __name__ == "__main__":
    asyncio.run(test_bg())
