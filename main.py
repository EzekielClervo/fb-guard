import os
from app import app  # noqa: F401
import sqlite3

# For the free tier, let's set up the app with SQLite
if not os.environ.get("DATABASE_URL"):
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fb_guard.db"
    
    with app.app_context():
        from app import db
        import models  # noqa: F401
        db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
