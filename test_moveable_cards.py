import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ARTIFACTS_DIR = Path(r"C:\Users\Piyush\.gemini\antigravity\brain\980a12ce-f101-46d1-ad36-1694511b6a92")

async def test_cards():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        
        print("Navigating to http://localhost:3000/...")
        await page.goto("http://localhost:3000/", wait_until="networkidle")
        await asyncio.sleep(1)
        
        print("Scrolling to #report section...")
        await page.evaluate("document.getElementById('report')?.scrollIntoView()")
        await asyncio.sleep(1.5)
        
        print("Capturing forensic report section with floating moveable cards...")
        await page.screenshot(path=str(ARTIFACTS_DIR / "moveable_cards_report.png"))
        
        # Test dragging the first card
        print("Dragging card 01 interactively...")
        card = page.locator("text=Executive Verdict").first
        box = await card.bounding_box()
        if box:
            start_x = box["x"] + box["width"] / 2
            start_y = box["y"] + box["height"] / 2
            
            await page.mouse.move(start_x, start_y)
            await page.mouse.down()
            await page.mouse.move(start_x + 80, start_y + 60, steps=10)
            await asyncio.sleep(0.5)
            
            print("Capturing card while dragging...")
            await page.screenshot(path=str(ARTIFACTS_DIR / "card_dragging.png"))
            
            await page.mouse.up()
            await asyncio.sleep(1)
            
        print("Capturing final position after drag release...")
        await page.screenshot(path=str(ARTIFACTS_DIR / "card_dragged_final.png"))
        
        await browser.close()
        print("Playwright moveable cards test complete!")

if __name__ == "__main__":
    asyncio.run(test_cards())
