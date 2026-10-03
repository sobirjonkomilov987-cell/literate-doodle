import sys
import uvicorn
import os

# Windows konsolida UTF-8 xatoliklarini oldini olish
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

if __name__ == "__main__":
    print("=" * 60)
    print("TADBIR CHIPTALARI - FASTAPI & VEBSAYT TIZIMI")
    print("=" * 60)
    print("Vebsayt manzili:  http://127.0.0.1:8000")
    print("OpenAPI Swagger:  http://127.0.0.1:8000/docs")
    print("Maxfiy Admin:     http://127.0.0.1:8000/secure-admin-portal-xyz")
    print("Bosh Admin login: sobirjon@admin / sobirjon@")
    print("=" * 60)
    
    # Uvicorn serverini ishga tushirish
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
