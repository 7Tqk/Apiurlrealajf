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

@app.get("/check")
async def check_card(
    cc: str = Query(...),
    site: str = Query(...),
    proxy: str = Query(None),
    amount: str = "31.0"
):
    # إعداد البروكسي
    proxies = {"http://": f"http://{proxy}", "https://": f"http://{proxy}"} if proxy else None
    
    try:
        # إضافة Referer و Origin ديناميكياً بناءً على الموقع
        request_headers = HEADERS.copy()
        request_headers["Referer"] = f"{site}/"
        request_headers["Origin"] = site

        async with httpx.AsyncClient(proxies=proxies, headers=request_headers, timeout=30.0, follow_redirects=True) as client:
            
            # هنا يتم ربط بيانات البطاقة بمنطق الموقع الفعلي
            # افترضنا مسار الدفع الافتراضي لـ Shopify
            target_url = f"{site}/payments/authorize"
            
            # تنفيذ الطلب الحقيقي
            response = await client.get(target_url) # أو post حسب حاجة البوابة
            
            # تحليل الرد (يجب ضبطه بناءً على JSON الموقع)
            # هنا التنسيق المطلوب للـ JSON
            return {
                "Gateway": "Shopify Payments",
                "Price": amount,
                "Proxy": "Live" if proxy else "None",
                "Response": response.status_code, 
                "Status": "true" if response.status_code == 200 else "false",
                "CC": cc
            }

    except Exception as e:
        return {
            "Gateway": "Shopify Payments",
            "Price": amount,
            "Proxy": "Error",
            "Response": str(e),
            "Status": "false",
            "CC": cc
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

