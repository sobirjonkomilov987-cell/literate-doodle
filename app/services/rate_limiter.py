import time
from collections import defaultdict
from typing import Tuple, Dict, List
from fastapi import HTTPException, status

# 1. SLIDING WINDOW RATE LIMITER (DDoS & Abuse Prevention)
RATE_LIMIT_WINDOWS: Dict[str, List[float]] = defaultdict(list)
WINDOW_SECONDS = 60 # 1 daqiqa

# Cheklov qoidalari (Bir daqiqada ruxsat etilgan so'rovlar soni)
ROUTE_LIMITS = {
    "/api/auth": 20,         # Autentifikatsiya (Brute-force / Credential stuffing oldini olish)
    "/api/reservations": 40, # Joy band qilish (Botlar orqali spam rezervatsiyani oldini olish)
    "/api/payments": 40,     # To'lov amallari
    "/api": 120              # Boshqa barcha API so'rovlari
}

def get_route_limit(path: str) -> int:
    for prefix, limit in ROUTE_LIMITS.items():
        if path.startswith(prefix):
            return limit
    return 120

def check_ip_rate_limit(client_ip: str, path: str) -> Tuple[bool, int, int, int]:
    """
    Sliding window algoritmi bo'yicha IP manzilini tekshirish.
    Qaytaradi: (is_limited, current_count, max_limit, retry_after_seconds)
    """
    now = time.time()
    limit = get_route_limit(path)
    if client_ip in ["testclient", "test"]:
        limit = 1000 # Avtomatlashtirilgan testlar uchun kengroq limit

    key = f"{client_ip}:{path.split('/')[2] if len(path.split('/')) > 2 else 'general'}"
    
    # 60 soniyadan eski yozuvlarni tozalash
    RATE_LIMIT_WINDOWS[key] = [t for t in RATE_LIMIT_WINDOWS[key] if now - t < WINDOW_SECONDS]
    
    current_count = len(RATE_LIMIT_WINDOWS[key])
    if current_count >= limit:
        oldest_req = RATE_LIMIT_WINDOWS[key][0]
        retry_after = max(1, int(WINDOW_SECONDS - (now - oldest_req)))
        return True, current_count, limit, retry_after
        
    RATE_LIMIT_WINDOWS[key].append(now)
    return False, current_count + 1, limit, 0

def reset_rate_limits():
    """Testlar yoki tizim tozalash uchun oynalarni tozalash"""
    RATE_LIMIT_WINDOWS.clear()
    LOGIN_ATTEMPTS.clear()
    BLACKLISTED_TOKENS.clear()


# 2. BRUTE-FORCE LOCKOUT (Hisob va IP darajasida bloklash)
LOGIN_ATTEMPTS: Dict[str, List[float]] = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 300 # 5 daqiqa bloklash

def check_brute_force(key: str):
    """5 marta xato urinishdan so'ng 5 daqiqaga bloklash"""
    now = time.time()
    LOGIN_ATTEMPTS[key] = [t for t in LOGIN_ATTEMPTS[key] if now - t < LOCKOUT_DURATION]
    if len(LOGIN_ATTEMPTS[key]) >= MAX_LOGIN_ATTEMPTS:
        remaining = int(LOCKOUT_DURATION - (now - LOGIN_ATTEMPTS[key][0]))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Xavfsizlik: Ketma-ket 5 marta noto'g'ri urinish amalga oshirildi (Brute-force himoyasi). Qayta urinish uchun {remaining} soniya kuting."
        )

def record_failed_attempt(key: str):
    LOGIN_ATTEMPTS[key].append(time.time())

def clear_failed_attempts(key: str):
    LOGIN_ATTEMPTS.pop(key, None)


# 3. JWT TOKEN BLACKLIST (Chiqib ketilganda tokenni bekor qilish)
BLACKLISTED_TOKENS = set()

def blacklist_token(token: str):
    """Foydalanuvchi tizimdan chiqqanda tokenni qora ro'yxatga kiritish"""
    if token:
        BLACKLISTED_TOKENS.add(token.strip())

def is_token_blacklisted(token: str) -> bool:
    """Token bekor qilinganligini tekshirish"""
    if not token:
        return True
    return token.strip() in BLACKLISTED_TOKENS
