from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))
# Use SQLite locally, but PostgreSQL in production
if os.getenv('DATABASE_URL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gym.db'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@app.cli.command("reset-db")
def reset_db():
    """Drops and Creates fresh database tables"""
    with app.app_context():
        # Drop all tables
        db.drop_all()
        # Create all tables
        db.create_all()
        print("Database has been reset!")

# Package Prices and Details
PACKAGES = {
    'basic': {
        'name': 'BASIC PACKAGE',
        'duration': 1,  # months
        'admission_fee': 250,
        'fees': 750,
        'total': 1000,
        'discount': 0
    },
    'standard': {
        'name': 'STANDARD PACKAGE',
        'duration': 3,  # months
        'fees': 2500,
        'discount': 300,
        'total': 2200
    },
    'premium': {
        'name': 'PREMIUM PACKAGE',
        'duration': 6,  # months
        'fees': 4750,
        'discount': 550,
        'total': 4200
    },
    'ultimate': {
        'name': 'ULTIMATE PACKAGE',
        'duration': 12,  # months
        'fees': 9250,
        'discount': 1050,
        'total': 8200
    }
}

PERSONAL_TRAINING = {
    'monthly': {
        'duration': 1,
        'fees': 4000,
        'discount': 0
    },
    'quarterly': {
        'duration': 3,
        'fees': 12000,
        'discount': 2000
    }
}

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
ADMIN_PHONE_NUMBER = os.getenv('ADMIN_PHONE_NUMBER')

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else None

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    customers = db.relationship('Customer', backref='trainer', lazy=True)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    package_type = db.Column(db.String(20), nullable=False)  # basic, standard, premium, ultimate
    membership_end = db.Column(db.DateTime, nullable=False)
    has_cardio = db.Column(db.Boolean, default=False)
    has_personal_training = db.Column(db.Boolean, default=False)
    personal_training_type = db.Column(db.String(20), nullable=True)  # monthly, quarterly
    trainer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    notification_sent = db.Column(db.Boolean, default=False)
    admission_fee = db.Column(db.Float, nullable=True)
    package_fee = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, nullable=True)
    total_amount = db.Column(db.Float, nullable=False)
    treadmill_access = db.Column(db.Boolean, default=False)

def send_sms(to_number, message):
    if twilio_client and TWILIO_PHONE_NUMBER:
        try:
            twilio_client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=to_number
            )
            return True
        except Exception as e:
            print(f"Error sending SMS: {str(e)}")
    return False

def check_expiring_memberships():
    with app.app_context():
        # Get memberships expiring in the next 7 days
        expiring_soon = Customer.query.filter(
            Customer.membership_end <= datetime.utcnow() + timedelta(days=7),
            Customer.membership_end > datetime.utcnow(),
            Customer.notification_sent == False
        ).all()

        for customer in expiring_soon:
            # Calculate days until expiration
            days_left = (customer.membership_end - datetime.utcnow()).days
            
            # Send notification to customer
            customer_message = (
                f"Dear {customer.name}, your {customer.package_type} membership at The Fitness Zone "
                f"will expire in {days_left} days. Please renew to continue enjoying our services!"
            )
            send_sms(customer.phone, customer_message)

            # Send notification to admin
            admin_message = (
                f"ALERT: Customer {customer.name}'s {customer.package_type} membership at The Fitness Zone "
                f"will expire in {days_left} days. Contact: {customer.phone}"
            )
            if ADMIN_PHONE_NUMBER:
                send_sms(ADMIN_PHONE_NUMBER, admin_message)

            # Mark notification as sent
            customer.notification_sent = True
            db.session.commit()

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_expiring_memberships, trigger="interval", hours=24)
scheduler.start()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_exists():
    return User.query.filter_by(is_admin=True).first() is not None

# Routes
@app.route('/')
def index():
    if not admin_exists():
        return redirect(url_for('create_admin'))
    return render_template('index.html')

@app.route('/create_admin', methods=['GET', 'POST'])
def create_admin():
    if admin_exists():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('create_admin'))
        
        admin = User(username=username, password=password, is_admin=True)
        db.session.add(admin)
        db.session.commit()
        
        flash('Admin account created successfully!', 'success')
        return redirect(url_for('login'))
    
    return render_template('create_admin.html')

@app.route('/register_customer', methods=['GET', 'POST'])
@login_required
def register_customer():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        package_type = request.form.get('package_type')
        has_cardio = 'has_cardio' in request.form
        has_personal_training = 'has_personal_training' in request.form
        personal_training_type = request.form.get('personal_training_type')
        treadmill_access = 'treadmill_access' in request.form
        
        # Get package details
        package = PACKAGES[package_type]
        duration_months = package['duration']
        end_date = datetime.utcnow() + timedelta(days=duration_months * 30)
        
        # Calculate total amount
        total_amount = package['total']
        discount = package['discount']
        
        # Add personal training fees if selected
        if has_personal_training and personal_training_type:
            pt_package = PERSONAL_TRAINING[personal_training_type]
            total_amount += pt_package['fees'] - pt_package['discount']
            
        # Add treadmill fee if selected (₹500 per month)
        if treadmill_access:
            total_amount += 500 * duration_months
        
        customer = Customer(
            name=name,
            email=email,
            phone=phone,
            package_type=package_type,
            membership_end=end_date,
            has_cardio=has_cardio,
            has_personal_training=has_personal_training,
            personal_training_type=personal_training_type if has_personal_training else None,
            trainer_id=current_user.id if has_personal_training else None,
            admission_fee=package.get('admission_fee', 0),
            package_fee=package['fees'],
            discount=discount,
            total_amount=total_amount,
            treadmill_access=treadmill_access
        )
        
        db.session.add(customer)
        db.session.commit()
        flash('Customer registered successfully!', 'success')
        return redirect(url_for('view_customers'))
    
    return render_template('register_customer.html', packages=PACKAGES, personal_training=PERSONAL_TRAINING)

@app.route('/view_customers')
@login_required
def view_customers():
    customers = Customer.query.all()
    return render_template('view_customers.html', customers=customers, now=datetime.utcnow())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.password == password:  # In production, use proper password hashing
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 