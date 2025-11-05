import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from app.config import settings

def main():
    url = settings.DATABASE_URL
    masked = url
    if settings.POSTGRES_PASSWORD and settings.POSTGRES_PASSWORD in masked:
        masked = masked.replace(settings.POSTGRES_PASSWORD, '***')
    print(f"Testing DB URL (masked): {masked}")
    try:
        import psycopg
        dsn = url.replace("postgresql+psycopg://", "postgresql://", 1)
        conn = psycopg.connect(dsn, connect_timeout=5)
        with conn.cursor() as cur:
            cur.execute("SELECT current_user, current_database();")
            print("Connected as:", cur.fetchone())
        conn.close()
        print("OK: psycopg can connect with provided credentials")
        return 0
    except Exception as e:
        print("ERROR:", repr(e))
        return 1

if __name__ == "__main__":
    sys.exit(main())
