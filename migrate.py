from app import app, db, User, Customer, Fee
from flask_login import LoginManager
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
    """Run database migrations"""
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        print("Database tables created successfully")
        
        # Check if admin exists
        from app import admin_exists
        if not admin_exists():
            print("No admin user found. Please create an admin account.")
        else:
            print("Admin account exists.")

if __name__ == "__main__":
    migrate() 