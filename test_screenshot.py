import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://areasegura.uniasselvi.com.br/identificacao")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path="login_debug.png")
        print("Screenshot saved to login_debug.png")
        await browser.close()

asyncio.run(main())
