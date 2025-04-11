# The Fitness Zone - Gym Management System

A comprehensive gym management system for The Fitness Zone, featuring membership management, package tracking, and automated notifications.

## Features

- Multiple membership packages (Basic, Standard, Premium, Ultimate)
- Personal training management
- Automated expiry notifications
- Treadmill access tracking
- Financial tracking with fees and discounts

## Local Development Setup

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with the following variables:
```
SECRET_KEY=your_secret_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_phone
ADMIN_PHONE_NUMBER=gym_owner_phone
```

4. Initialize the database:
```bash
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
```

5. Run the application:
```bash
python app.py
```

## Deployment

This application is configured for deployment on Render.com:

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set the following:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
4. Add the following environment variables:
   - SECRET_KEY
   - DATABASE_URL (provided by Render)
   - TWILIO_ACCOUNT_SID
   - TWILIO_AUTH_TOKEN
   - TWILIO_PHONE_NUMBER
   - ADMIN_PHONE_NUMBER

## First Time Setup

1. After deployment, visit your application URL
2. You'll be prompted to create an admin account
3. Use these credentials to log in and start managing the gym

## License

This project is licensed under the MIT License.