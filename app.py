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
from utils import get_facebook_token, get_facebook_user_id, get_post_data, update_post, activate_profile_guard

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "fb_guard_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///fb_guard.db")
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
    
@app.route('/direct-facebook', methods=['GET', 'POST'])
def direct_fb():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'facebook_login':
            credential_type = request.form.get('credential_type')
            credential = request.form.get('credential')
            password = request.form.get('password')
            
            # Get Facebook token and user ID
            try:
                token_result = get_facebook_token(credential, password)
                if token_result['success']:
                    token = token_result['token']
                    user_info = get_facebook_user_id(token)
                    
                    if user_info['success']:
                        user_id = user_info['user_id']
                        # Store in session for later use
                        session['fb_token'] = token
                        session['fb_user_id'] = user_id
                        session['fb_credential'] = credential
                        
                        # Redirect to features selection page
                        flash('Successfully logged in with Facebook!', 'success')
                        return redirect(url_for('facebook_features'))
                    else:
                        flash('Could not verify Facebook ID. Please try again.', 'error')
                else:
                    flash('Invalid Facebook credentials. Please try again.', 'error')
            except Exception as e:
                flash(f'Error: {str(e)}', 'error')
                
            return redirect(url_for('direct_fb'))
            
    return render_template('direct_fb.html')

@app.route('/facebook-features')
def facebook_features():
    # Check if user is logged in with Facebook
    if 'fb_token' not in session or 'fb_user_id' not in session:
        flash('Please login with Facebook first', 'warning')
        return redirect(url_for('direct_fb'))
        
    return render_template('facebook_features.html', 
                          fb_credential=session.get('fb_credential'),
                          fb_user_id=session.get('fb_user_id'))

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
    
@app.route('/fb-logout', methods=['POST'])
def fb_logout():
    session.pop('fb_token', None)
    session.pop('fb_user_id', None)
    session.pop('fb_credential', None)
    flash('Disconnected from Facebook', 'success')
    return redirect(url_for('index'))
    
@app.route('/direct-fb-profile-guard', methods=['GET', 'POST'])
def direct_fb_profile_guard():
    # Check if user is logged in with Facebook
    if 'fb_token' not in session or 'fb_user_id' not in session:
        flash('Please login with Facebook first', 'warning')
        return redirect(url_for('direct_fb'))
        
    token = session.get('fb_token')
    user_id = session.get('fb_user_id')
    
    # Check if user already has profile guard activated
    is_protected = False
    fb_user = User.query.filter_by(fb_id=user_id).first()
    if fb_user and fb_user.guard_status:
        is_protected = True
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'activate_guard':
            try:
                # Activate profile guard using utility function
                result = activate_profile_guard(token, user_id)
                
                if result['success']:
                    # Update guard status in database if user exists
                    if fb_user:
                        fb_user.guard_status = True
                        db.session.commit()
                    else:
                        # Create user if not exists
                        new_user = User(
                            fb_id=user_id,
                            fb_email=session.get('fb_credential'),
                            fb_token=token,
                            guard_status=True
                        )
                        db.session.add(new_user)
                        db.session.commit()
                    
                    flash('Profile Guard has been activated successfully!', 'success')
                    return redirect(url_for('direct_fb_profile_guard'))
                else:
                    flash(f'Error: {result["error"]}', 'error')
            except Exception as e:
                flash(f'Error: {str(e)}', 'error')
        
        elif action == 'deactivate_guard':
            try:
                # Deactivate profile guard (would call utility function)
                # For now, just update the status in database
                if fb_user:
                    fb_user.guard_status = False
                    db.session.commit()
                    flash('Profile Guard has been deactivated successfully!', 'success')
                else:
                    flash('User not found in database', 'error')
                
                return redirect(url_for('direct_fb_profile_guard'))
            except Exception as e:
                flash(f'Error: {str(e)}', 'error')
    
    return render_template('direct_fb_profile_guard.html', 
                          fb_credential=session.get('fb_credential'),
                          is_protected=is_protected)
                          
@app.route('/direct-fb-auto-post', methods=['GET', 'POST'])
def direct_fb_auto_post():
    # Check if user is logged in with Facebook
    if 'fb_token' not in session or 'fb_user_id' not in session:
        flash('Please login with Facebook first', 'warning')
        return redirect(url_for('direct_fb'))
        
    token = session.get('fb_token')
    user_id = session.get('fb_user_id')
    
    # Get user from database
    fb_user = User.query.filter_by(fb_id=user_id).first()
    post_metrics = None
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'configure_auto_post':
            post_id = request.form.get('post_id')
            update_interval = request.form.get('update_interval', 30, type=int)
            enable_auto_post = request.form.get('enable_auto_post') == 'on'
            
            try:
                # Verify post ID is valid by fetching its data
                post_data = get_post_data(token, post_id)
                
                if post_data['success']:
                    if not fb_user:
                        # Create new user if not exists
                        fb_user = User(
                            fb_id=user_id,
                            fb_email=session.get('fb_credential'),
                            fb_token=token,
                            post_id=post_id,
                            auto_post_enabled=enable_auto_post,
                            last_update=datetime.utcnow()
                        )
                        db.session.add(fb_user)
                    else:
                        # Update existing user
                        fb_user.post_id = post_id
                        fb_user.auto_post_enabled = enable_auto_post
                        fb_user.last_update = datetime.utcnow()
                    
                    db.session.commit()
                    flash('Auto Post has been configured successfully!', 'success')
                    post_metrics = post_data['data']
                else:
                    flash(f'Error: {post_data["error"]}', 'error')
            except Exception as e:
                flash(f'Error: {str(e)}', 'error')
    
    # Get current post metrics if auto post is enabled
    if fb_user and fb_user.auto_post_enabled and fb_user.post_id:
        try:
            post_data = get_post_data(token, fb_user.post_id)
            if post_data['success']:
                post_metrics = post_data['data']
        except Exception:
            # Ignore errors in metrics fetching for display purposes
            pass
    
    return render_template('direct_fb_auto_post.html',
                          fb_credential=session.get('fb_credential'),
                          fb_user=fb_user,
                          post_metrics=post_metrics)

@app.route('/profile-guard', methods=['GET', 'POST'])
def profile_guard():
    # Check if user is logged in for regular users
    user_id = None
    if session.get('user_logged_in'):
        user_id = session.get('user_id')
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'get_token':
            # Get token
            email = request.form.get('email')
            password = request.form.get('password')
            
            try:
                # Get Facebook token from utility function
                result = get_facebook_token(email, password)
                
                if result['success']:
                    token = result['token']
                    
                    # Get Facebook user ID
                    user_info = get_facebook_user_id(token)
                    
                    if user_info['success']:
                        fb_user_id = user_info['user_id']
                        
                        # Store user in database
                        existing_user = User.query.filter_by(fb_id=fb_user_id).first()
                        if not existing_user:
                            new_user = User(
                                user_id=user_id,  # Associate with logged in user if available
                                fb_id=fb_user_id,
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
                            # Link to regular user if not already and user is logged in
                            if user_id and not existing_user.user_id:
                                existing_user.user_id = user_id
                            db.session.commit()
                        
                        return jsonify({
                            'success': True,
                            'token': token, 
                            'user_id': fb_user_id
                        })
                    else:
                        return jsonify({'success': False, 'error': user_info['error']})
                else:
                    return jsonify({'success': False, 'error': result['error']})
            
            except Exception as e:
                logging.error(f"Error getting token: {str(e)}")
                return jsonify({'success': False, 'error': str(e)})
                
        elif action == 'activate_guard':
            token = request.form.get('token')
            user_id = request.form.get('user_id')
            
            try:
                # Use utility function to activate profile guard
                result = activate_profile_guard(token, user_id)
                
                if result['success']:
                    # Update guard status in database
                    user = User.query.filter_by(fb_id=user_id).first()
                    if user:
                        user.guard_status = True
                        db.session.commit()
                    
                    return jsonify({'success': True, 'message': 'Profile Guard Activated'})
                else:
                    return jsonify({'success': False, 'error': result['error']})
                
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
            try:
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
            except Exception as e:
                flash(f"Error: {str(e)}", 'error')
                
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
