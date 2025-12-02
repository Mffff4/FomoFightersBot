from typing import Dict
from bot.core.agents import generate_random_user_agent

def get_agentx_headers(token: str) -> dict:
    return {
        "Accept-Language": "ru-RU,ru;q=0.9,en-NL;q=0.8,en-US;q=0.7,en;q=0.6",
        "Connection": "keep-alive",
        "If-None-Match": 'W/"2ef9-fZ/C6gM+FPcmIYJV+v8NbPFChG0"',
        "Origin": "https://app.agentx.pw",
        "Referer": "https://app.agentx.pw/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "accept": "application/json",
        "authorization": f"Bearer {token}",
    }

def get_tonminefarm_headers() -> dict:
    return {
        "Accept": "*/*",
        "Accept-Language": "ru,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
        "Connection": "keep-alive",
        "Content-Type": "application/json; charset=UTF-8",
        "Origin": "https://app.tonminefarm.com",
        "Referer": "https://app.tonminefarm.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0",
        "sec-ch-ua": '"Chromium";v="139", "Microsoft Edge WebView2";v="139", "Microsoft Edge";v="139", "Not;A=Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

def get_fomofighters_headers(api_key: str, api_hash: str, api_time: int) -> dict:
    return {
        "accept": "*/*",
        "accept-language": "ru,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
        "api-hash": api_hash,
        "api-key": api_key,
        "api-time": str(api_time),
        "content-type": "application/json",
        "is-beta-server": "null",
        "origin": "https://game.fomofighters.xyz",
        "priority": "u=1, i",
        "referer": "https://game.fomofighters.xyz/",
        "sec-ch-ua": '"Microsoft Edge";v="142", "Microsoft Edge WebView2";v="142", "Chromium";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0"
    }