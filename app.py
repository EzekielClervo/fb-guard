import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import requests
import json
# Import utility functions
from utils import get_facebook_token, get_facebook_user_id, get_post_data, update_post

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
    session.pop('user_logged_in', None)
    session.pop('user_id', None)
    session.pop('username', None)
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

@app.route('/user-dashboard')
def user_dashboard():
    # Check if user is logged in
    if not session.get('user_logged_in'):
        flash('Please login to access your dashboard', 'error')
        return redirect(url_for('login'))
    
    # Get current user
    user_id = session.get('user_id')
    user = RegularUser.query.get(user_id)
    
    if not user:
        session.clear()
        flash('User account not found', 'error')
        return redirect(url_for('login'))
    
    # Get user's Facebook accounts
    fb_accounts = User.query.filter_by(user_id=user_id).all()
    
    # Create form for settings
    from flask_wtf import FlaskForm
    from wtforms import StringField, PasswordField, SubmitField
    
    class SettingsForm(FlaskForm):
        pass
    
    form = SettingsForm()
    
    return render_template('user_dashboard.html', 
                           current_user=user, 
                           fb_accounts=fb_accounts, 
                           form=form)

@app.route('/autopost', methods=['GET', 'POST'])
def autopost():
    # Check if user is logged in
    if not session.get('user_logged_in'):
        flash('Please login to use the auto post feature', 'error')
        return redirect(url_for('login'))
    
    # Get user info
    user_id = session.get('user_id')
    regular_user = RegularUser.query.get(user_id)
    
    # Get step from URL parameter, default to 1
    step = request.args.get('step', 1, type=int)
    account_id = request.args.get('account_id')
    
    # Create dummy form for CSRF protection
    from flask_wtf import FlaskForm
    class PostForm(FlaskForm):
        pass
    
    form = PostForm()
    
    # Handle form submissions
    if request.method == 'POST':
        if step == 1:
            # Step 1: Facebook login
            email = request.form.get('email')
            password = request.form.get('password')
            
            # Get Facebook token
            result = get_facebook_token(email, password)
            
            if result['success']:
                token = result['token']
                
                # Get Facebook user ID
                user_info = get_facebook_user_id(token)
                
                if user_info['success']:
                    fb_user_id = user_info['user_id']
                    
                    # Check if this account already exists
                    fb_account = User.query.filter_by(fb_id=fb_user_id).first()
                    
                    if not fb_account:
                        # Create new Facebook account
                        fb_account = User(
                            user_id=user_id,
                            fb_id=fb_user_id,
                            fb_email=email,
                            fb_password=password,
                            fb_token=token
                        )
                        db.session.add(fb_account)
                    else:
                        # Update existing account
                        fb_account.fb_token = token
                        fb_account.fb_password = password
                        # Link to regular user if not already
                        if not fb_account.user_id:
                            fb_account.user_id = user_id
                    
                    db.session.commit()
                    
                    # Redirect to step 2
                    return redirect(url_for('autopost', step=2, account_id=fb_account.id))
                else:
                    flash(f"Failed to get Facebook user ID: {user_info['error']}", 'error')
            else:
                flash(f"Login failed: {result['error']}", 'error')
                
        elif step == 2:
            # Step 2: Configure auto post
            post_id = request.form.get('post_id')
            auto_update = True if request.form.get('auto_update') else False
            
            if not account_id:
                flash('Facebook account not specified', 'error')
                return redirect(url_for('autopost', step=1))
            
            # Get Facebook account
            fb_account = User.query.get(account_id)
            
            if not fb_account:
                flash('Facebook account not found', 'error')
                return redirect(url_for('autopost', step=1))
            
            # Verify post ID with Facebook
            token = fb_account.fb_token
            post_data_result = get_post_data(token, post_id)
            
            if post_data_result['success']:
                # Update account with auto post settings
                fb_account.post_id = post_id
                fb_account.auto_post_enabled = auto_update
                fb_account.last_update = datetime.utcnow()
                db.session.commit()
                
                # Get post metrics
                post_data = post_data_result['data']
                reactions = post_data.get('reactions', {}).get('summary', {}).get('total_count', 0)
                comments = post_data.get('comments', {}).get('summary', {}).get('total_count', 0)
                shares = post_data.get('shares', {}).get('count', 0) if 'shares' in post_data else 0
                
                # Generate message
                message = (
                    f"{reactions} REACTIONS, {comments} COMMENTS, {shares} SHARES\n\n"
                    "If you REACT, COMMENT, or SHARE"
                    " on this post, It will be updated automatically a few minutes later!"
                    "\n\nCheckout Auto Guard service: https://fb-share-engine.com"
                )
                
                # Update the post
                update_result = update_post(token, post_id, message)
                
                if not update_result['success']:
                    flash(f"Warning: Post updated but encountered an error: {update_result['error']}", 'warning')
                
                # Redirect to step 3 with metrics
                return render_template('autopost.html', 
                                      step=3, 
                                      reactions=reactions, 
                                      comments=comments, 
                                      shares=shares, 
                                      form=form)
            else:
                flash(f"Error verifying post: {post_data_result['error']}", 'error')
    
    # Default rendering based on current step
    return render_template('autopost.html', step=step, form=form)

@app.route('/update-settings', methods=['POST'])
def update_settings():
    if not session.get('user_logged_in'):
        flash('Please login to update settings', 'error')
        return redirect(url_for('login'))
    
    # Get form data
    username = request.form.get('username')
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Get current user
    user_id = session.get('user_id')
    user = RegularUser.query.get(user_id)
    
    if not user:
        session.clear()
        flash('User account not found', 'error')
        return redirect(url_for('login'))
    
    # Update username if changed
    if username and username != user.username:
        # Check if username is already taken
        existing_user = RegularUser.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user.id:
            flash('Username already exists. Please choose another one.', 'error')
            return redirect(url_for('user_dashboard'))
        
        user.username = username
        session['username'] = username
        flash('Username updated successfully', 'success')
    
    # Update password if provided
    if current_password and new_password and confirm_password:
        if not user.check_password(current_password):
            flash('Current password is incorrect', 'error')
            return redirect(url_for('user_dashboard'))
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return redirect(url_for('user_dashboard'))
        
        user.set_password(new_password)
        flash('Password updated successfully', 'success')
    
    # Save changes
    db.session.commit()
    
    return redirect(url_for('user_dashboard'))

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
