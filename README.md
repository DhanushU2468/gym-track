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

## Deployment to Railway

### Prerequisites

1. A [Railway](https://railway.app/) account
2. A GitHub account with your code pushed to a repository

### Deployment Steps

1. Log in to [Railway](https://railway.app/)
2. Click "New Project" and select "Deploy from GitHub repo"
3. Select your repository
4. Add a PostgreSQL database:
   - Click "New" and select "Database" > "PostgreSQL"
   - Railway will automatically add the `DATABASE_URL` environment variable to your project
5. Set up environment variables:
   - Go to the "Variables" tab
   - Add the following variables:
     ```
     SECRET_KEY=your_secret_key
     FLASK_ENV=production
     TWILIO_ACCOUNT_SID=your_twilio_account_sid
     TWILIO_AUTH_TOKEN=your_twilio_auth_token
     TWILIO_PHONE_NUMBER=your_twilio_phone
     ADMIN_PHONE_NUMBER=your_admin_phone
     ```
6. Deploy your application:
   - Railway will automatically detect your `Procfile` and deploy your application
   - The application will be available at the URL provided by Railway

### Database Migrations

After deployment, you need to run database migrations:

1. Connect to your Railway project via the Railway CLI:
   ```
   railway login
   railway link
   ```
2. Run migrations:
   ```
   railway run flask db upgrade
   ```

## First Time Setup

1. After deployment, visit your application URL
2. You'll be prompted to create an admin account
3. Use these credentials to log in and start managing the gym

## License

This project is licensed under the MIT License.