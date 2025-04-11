from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gym.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

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
    membership_type = db.Column(db.String(20), nullable=False)  # monthly, quarterly, yearly
    membership_end = db.Column(db.DateTime, nullable=False)
    has_cardio = db.Column(db.Boolean, default=False)
    has_personal_training = db.Column(db.Boolean, default=False)
    trainer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

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
        membership_type = request.form.get('membership_type')
        has_cardio = 'has_cardio' in request.form
        has_personal_training = 'has_personal_training' in request.form
        
        # Calculate membership end date
        if membership_type == 'monthly':
            end_date = datetime.utcnow() + timedelta(days=30)
        elif membership_type == 'quarterly':
            end_date = datetime.utcnow() + timedelta(days=90)
        else:  # yearly
            end_date = datetime.utcnow() + timedelta(days=365)
        
        customer = Customer(
            name=name,
            email=email,
            phone=phone,
            membership_type=membership_type,
            membership_end=end_date,
            has_cardio=has_cardio,
            has_personal_training=has_personal_training,
            trainer_id=current_user.id if has_personal_training else None
        )
        
        db.session.add(customer)
        db.session.commit()
        flash('Customer registered successfully!', 'success')
        return redirect(url_for('view_customers'))
    
    return render_template('register_customer.html')

@app.route('/view_customers')
@login_required
def view_customers():
    customers = Customer.query.all()
    return render_template('view_customers.html', customers=customers)

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