"""Quick diagnostic: reproduce the login 500 error locally."""
import sys, os, traceback
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("DATABASE_URL", "sqlite:///meeting.db")

try:
    from app.core.database import engine, SessionLocal
    from app.models.user import User
    from app.core.security import authenticate_user

    print(f"[INFO] Engine URL: {engine.url}")
    db = SessionLocal()

    # Check if users table exists and has data
    from sqlalchemy import text
    result = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
    print(f"[INFO] Users count: {result}")

    # Try to query admin user
    user = db.query(User).filter(User.username == "admin").first()
    if user:
        print(f"[OK] Found user: {user.username}, role={user.role}, active={user.is_active}")
        # Try authenticate
        try:
            auth_user = authenticate_user(db, "admin", "123456")
            print(f"[OK] Auth success: {auth_user.username}")
        except Exception as e:
            print(f"[ERROR] Auth failed: {e}")
            traceback.print_exc()
    else:
        print("[ERROR] Admin user not found!")
        # Show all users
        users = db.execute(text("SELECT id, username, role FROM users")).fetchall()
        for u in users:
            print(f"  User: id={u[0]}, username={u[1]}, role={u[2]}")

    db.close()
except Exception as e:
    print(f"[FATAL] {e}")
    traceback.print_exc()
