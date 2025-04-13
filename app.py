from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from twilio.rest import Client
import os
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///gym.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Print database URL for debugging (without sensitive information)
if DATABASE_URL:
    masked_url = DATABASE_URL.split('@')[0] + '@*****' if '@' in DATABASE_URL else '*****'
    print(f"Using database: {masked_url}")
else:
    print("Using SQLite database: gym.db")

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

# Print Twilio configuration for debugging
print(f"Twilio Account SID: {TWILIO_ACCOUNT_SID}")
print(f"Twilio Auth Token: {'*' * len(TWILIO_AUTH_TOKEN) if TWILIO_AUTH_TOKEN else 'Not set'}")
print(f"Twilio Phone Number: {TWILIO_PHONE_NUMBER}")
print(f"Admin Phone Number: {ADMIN_PHONE_NUMBER}")

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else None
if twilio_client:
    print("Twilio client initialized successfully")
else:
    print("Failed to initialize Twilio client. Check your credentials.")

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
    email = db.Column(db.String(120), unique=True, nullable=True)
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
    fees = db.relationship('Fee', backref='customer', lazy=True, cascade="all, delete-orphan")
    pending_amount = db.Column(db.Float, default=0.0)

class Fee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_type = db.Column(db.String(50), nullable=False)  # registration, monthly, additional
    description = db.Column(db.String(200))
    collected_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

def send_sms(to_number, message):
    """Send SMS using Twilio"""
    with app.app_context():
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
            print("Twilio credentials not configured. Skipping SMS.")
            return False

        try:
            # Format the phone number
            if not to_number.startswith('+'):
                # If it's an Indian number without country code
                if len(to_number) == 10:
                    to_number = '+91' + to_number
                else:
                    to_number = '+' + to_number

            print(f"Attempting to send SMS to {to_number}")
            
            # Initialize Twilio client
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            
            # Send message
            message = client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=to_number
            )
            print(f"SMS sent successfully. SID: {message.sid}")
            return True
        except Exception as e:
            print(f"Error sending SMS: {str(e)}")
            if hasattr(e, 'code'):
                print(f"Twilio error code: {e.code}")
            if hasattr(e, 'msg'):
                print(f"Twilio error message: {e.msg}")
            return False

def check_expiring_memberships():
    """Check for memberships that are expiring soon and send notifications"""
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
            print(f"Attempting to send expiration reminder to customer: {customer.phone}")
            customer_sms_sent = send_sms(customer.phone, customer_message)
            if customer_sms_sent:
                print(f"Expiration reminder sent successfully to {customer.phone}")
            else:
                print(f"Failed to send expiration reminder to {customer.phone}")

            # Send notification to admin
            admin_message = (
                f"ALERT: Customer {customer.name}'s {customer.package_type} membership at The Fitness Zone "
                f"will expire in {days_left} days. Contact: {customer.phone}"
            )
            if ADMIN_PHONE_NUMBER:
                print(f"Attempting to send admin notification to: {ADMIN_PHONE_NUMBER}")
                admin_sms_sent = send_sms(ADMIN_PHONE_NUMBER, admin_message)
                if admin_sms_sent:
                    print(f"Admin notification sent successfully to {ADMIN_PHONE_NUMBER}")
                else:
                    print(f"Failed to send admin notification to {ADMIN_PHONE_NUMBER}")

            # Mark notification as sent
            customer.notification_sent = True
            db.session.commit()
            
        # Reset notification_sent flag for expired memberships to allow re-notification
        expired = Customer.query.filter(
            Customer.membership_end < datetime.utcnow(),
            Customer.notification_sent == True
        ).all()
        
        for customer in expired:
            customer.notification_sent = False
            db.session.commit()

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_expiring_memberships, trigger="interval", hours=24)
scheduler.start()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_exists():
    """Check if an admin user exists in the database"""
    with app.app_context():
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
        email = request.form.get('email')  # This will be None if not provided
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
            email=email,  # This can be None
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
        
        # Add initial payment record
        initial_payment = float(request.form.get('initial_payment', 0))
        customer.pending_amount = total_amount - initial_payment
        
        db.session.add(customer)
        db.session.commit()

        if initial_payment > 0:
            fee = Fee(
                customer_id=customer.id,
                amount=initial_payment,
                payment_type='registration',
                description='Initial registration payment',
                collected_by=current_user.id
            )
            db.session.add(fee)
            db.session.commit()

        # Send welcome SMS to customer
        welcome_message = (
            f"Welcome to The Fitness Zone, {customer.name}! Your {customer.package_type} membership "
            f"has been activated. Your membership will expire on {customer.membership_end.strftime('%d-%m-%Y')}. "
            f"Thank you for choosing us!"
        )
        print(f"Attempting to send welcome SMS to customer: {customer.phone}")
        customer_sms_sent = send_sms(customer.phone, welcome_message)
        if customer_sms_sent:
            print(f"Welcome SMS sent successfully to {customer.phone}")
        else:
            print(f"Failed to send welcome SMS to {customer.phone}")

        # Send notification to admin
        admin_notification = (
            f"New customer registered: {customer.name}, {customer.package_type} package, "
            f"Phone: {customer.phone}, Expiry: {customer.membership_end.strftime('%d-%m-%Y')}"
        )
        if ADMIN_PHONE_NUMBER:
            print(f"Attempting to send admin notification to: {ADMIN_PHONE_NUMBER}")
            admin_sms_sent = send_sms(ADMIN_PHONE_NUMBER, admin_notification)
            if admin_sms_sent:
                print(f"Admin notification sent successfully to {ADMIN_PHONE_NUMBER}")
            else:
                print(f"Failed to send admin notification to {ADMIN_PHONE_NUMBER}")

        flash('Customer registered successfully!', 'success')
        return redirect(url_for('view_customers'))
    
    return render_template('register_customer.html', packages=PACKAGES, personal_training=PERSONAL_TRAINING)

@app.route('/view_customers')
@login_required
def view_customers():
    search_query = request.args.get('search', '')
    
    if search_query:
        # Search in name, email, and phone
        customers = Customer.query.filter(
            db.or_(
                Customer.name.ilike(f'%{search_query}%'),
                Customer.email.ilike(f'%{search_query}%'),
                Customer.phone.ilike(f'%{search_query}%')
            )
        ).all()
    else:
        customers = Customer.query.all()
    
    total_fees = db.session.query(db.func.sum(Fee.amount)).scalar() or 0
    today_fees = db.session.query(db.func.sum(Fee.amount)).filter(
        db.func.date(Fee.payment_date) == datetime.utcnow().date()
    ).scalar() or 0
    
    return render_template('view_customers.html', 
                         customers=customers, 
                         now=datetime.utcnow(),
                         total_fees=total_fees,
                         today_fees=today_fees,
                         search_query=search_query)

@app.route('/send_reminder/<int:customer_id>', methods=['POST'])
@login_required
def send_reminder(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    
    # Calculate days until expiration
    days_left = (customer.membership_end - datetime.utcnow()).days
    
    # Send notification to customer
    customer_message = (
        f"Dear {customer.name}, your {customer.package_type} membership at The Fitness Zone "
        f"will expire in {days_left} days. Please renew to continue enjoying our services!"
    )
    print(f"Attempting to send reminder SMS to customer: {customer.phone}")
    customer_sms_sent = send_sms(customer.phone, customer_message)
    if customer_sms_sent:
        print(f"Reminder SMS sent successfully to {customer.phone}")
    else:
        print(f"Failed to send reminder SMS to {customer.phone}")

    # Send notification to admin
    admin_message = (
        f"ALERT: Customer {customer.name}'s {customer.package_type} membership at The Fitness Zone "
        f"will expire in {days_left} days. Contact: {customer.phone}"
    )
    admin_sms_sent = False
    if ADMIN_PHONE_NUMBER:
        print(f"Attempting to send admin notification to: {ADMIN_PHONE_NUMBER}")
        admin_sms_sent = send_sms(ADMIN_PHONE_NUMBER, admin_message)
        if admin_sms_sent:
            print(f"Admin notification sent successfully to {ADMIN_PHONE_NUMBER}")
        else:
            print(f"Failed to send admin notification to {ADMIN_PHONE_NUMBER}")
    
    if customer_sms_sent:
        flash(f'Reminder sent to {customer.name}.', 'success')
    else:
        flash(f'Failed to send reminder to {customer.name}.', 'error')
        
    return redirect(url_for('view_customers'))

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

@app.route('/delete_customer/<int:customer_id>', methods=['POST'])
@login_required
def delete_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    customer_name = customer.name
    
    try:
        # Delete the customer (related fees will be deleted automatically due to cascade)
        db.session.delete(customer)
        db.session.commit()
        flash(f'Customer {customer_name} has been successfully removed.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the customer.', 'error')
        print(f"Error deleting customer: {str(e)}")
    
    return redirect(url_for('view_customers'))

@app.route('/add_fee/<int:customer_id>', methods=['POST'])
@login_required
def add_fee(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    amount = float(request.form.get('amount', 0))
    payment_type = request.form.get('payment_type')
    description = request.form.get('description', '')

    if amount <= 0:
        flash('Please enter a valid amount.', 'error')
        return redirect(url_for('view_customers'))

    fee = Fee(
        customer_id=customer_id,
        amount=amount,
        payment_type=payment_type,
        description=description,
        collected_by=current_user.id
    )

    # Update pending amount
    if customer.pending_amount >= amount:
        customer.pending_amount -= amount
    
    try:
        db.session.add(fee)
        db.session.commit()
        flash(f'Payment of ₹{amount} has been recorded successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while recording the payment.', 'error')
        print(f"Error recording payment: {str(e)}")

    return redirect(url_for('view_customers'))

@app.route('/test_sms')
@login_required
def test_sms():
    if not current_user.is_admin:
        flash('Only admins can access this page.', 'error')
        return redirect(url_for('index'))
    
    test_message = "This is a test SMS from The Fitness Zone gym management system."
    test_number = ADMIN_PHONE_NUMBER
    
    if test_number:
        result = send_sms(test_number, test_message)
        if result:
            flash('Test SMS sent successfully!', 'success')
        else:
            flash('Failed to send test SMS. Check the console for details.', 'error')
    else:
        flash('Admin phone number not configured. Please set ADMIN_PHONE_NUMBER in your .env file.', 'error')
    
    return redirect(url_for('index'))

@app.route('/extend_membership/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def extend_membership(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    
    if request.method == 'POST':
        extension_period = int(request.form.get('extension_period', 0))
        cardio_access = request.form.get('cardio_access') == 'on'
        personal_training = request.form.get('personal_training') == 'on'
        treadmill_access = request.form.get('treadmill_access') == 'on'
        personal_training_type = request.form.get('personal_training_type')
        initial_payment = float(request.form.get('initial_payment', 0))
        
        # Calculate new expiry date
        current_expiry = customer.membership_end or datetime.now()
        new_expiry = current_expiry + timedelta(days=30 * extension_period)
        
        # Update customer details
        customer.membership_end = new_expiry
        customer.has_cardio = cardio_access
        customer.has_personal_training = personal_training
        customer.treadmill_access = treadmill_access
        customer.personal_training_type = personal_training_type if personal_training else None
        
        # Create payment record
        payment = Fee(
            customer_id=customer.id,
            amount=initial_payment,
            payment_date=datetime.now(),
            payment_type='Membership Extension',
            collected_by=current_user.id
        )
        
        db.session.add(payment)
        db.session.commit()
        
        flash('Membership extended successfully!', 'success')
        return redirect(url_for('view_customers'))
    
    return render_template('extend_membership.html', customer=customer)

@app.route('/view_customer/<int:customer_id>')
@login_required
def view_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    fees = Fee.query.filter_by(customer_id=customer_id).order_by(Fee.payment_date.desc()).all()
    return render_template('view_customer.html', customer=customer, fees=fees)

@app.route('/edit_customer/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    
    if request.method == 'POST':
        # Update customer details
        customer.name = request.form.get('name')
        customer.email = request.form.get('email')
        customer.phone = request.form.get('phone')
        customer.has_cardio = 'has_cardio' in request.form
        customer.has_personal_training = 'has_personal_training' in request.form
        customer.personal_training_type = request.form.get('personal_training_type') if 'has_personal_training' in request.form else None
        customer.treadmill_access = 'treadmill_access' in request.form
        
        db.session.commit()
        flash('Customer details updated successfully!', 'success')
        return redirect(url_for('view_customer', customer_id=customer.id))
    
    return render_template('edit_customer.html', customer=customer)

def init_db():
    """Initialize the database and create tables if they don't exist"""
    with app.app_context():
        try:
            # Check if tables exist
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if not existing_tables:
                # Create all tables only if they don't exist
                db.create_all()
                print("Database tables created successfully")
            else:
                print("Database tables already exist")
            
            # Check if admin exists, if not, redirect to create admin page
            if not admin_exists():
                print("No admin user found. Please create an admin account.")
        except Exception as e:
            print(f"Error initializing database: {str(e)}")

if __name__ == '__main__':
    init_db()
    app.run(debug=True) 