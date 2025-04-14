from app import app, db, init_db
import os

def initialize_railway_db():
    """Initialize the database on Railway"""
    print("Initializing Railway database...")
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully")
        
        # Check if admin exists
        from app import admin_exists
        if not admin_exists():
            print("No admin user found. Please create an admin account after deployment.")
        else:
            print("Admin user exists.")

if __name__ == "__main__":
    initialize_railway_db()
    print("Railway database initialization complete.") 