import os
import logging
import requests
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import User

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create scheduler
scheduler = BlockingScheduler()

# Database setup
DATABASE_URL = os.environ.get('DATABASE_URL')
engine = create_engine(DATABASE_URL)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

def get_post_data(token, post_id):
    """Get post data from Facebook API
    
    Args:
        token (str): Facebook access token
        post_id (str): Facebook post id
        
    Returns:
        dict: Post data with engagement metrics
    """
    try:
        url = f"https://graph.facebook.com/v14.0/{post_id}"
        params = {
            "fields": "reactions.summary(total_count),comments.summary(total_count),shares",
            "access_token": token
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'error' in data:
            logger.error(f"Error fetching post data: {data['error'].get('message', 'Unknown error')}")
            return None
            
        return data
    except Exception as e:
        logger.error(f"Exception in get_post_data: {str(e)}")
        return None

def update_post(token, post_id, message):
    """Update a Facebook post with new content
    
    Args:
        token (str): Facebook access token
        post_id (str): Facebook post id
        message (str): New post content
    """
    try:
        url = f"https://graph.facebook.com/v14.0/{post_id}"
        params = {
            "message": message,
            "access_token": token
        }
        response = requests.post(url, params=params)
        data = response.json()
        
        if 'error' in data:
            logger.error(f"Error updating post: {data['error'].get('message', 'Unknown error')}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Exception in update_post: {str(e)}")
        return False

@scheduler.scheduled_job('interval', minutes=5)
def process_auto_posts():
    """Main job to process all auto posts"""
    logger.info("Running auto post update job")
    
    session = Session()
    try:
        # Get all users with auto post enabled
        users = session.query(User).filter_by(auto_post_enabled=True).all()
        logger.info(f"Found {len(users)} users with auto post enabled")
        
        for user in users:
            if not user.post_id or not user.post_message:
                logger.warning(f"User {user.fb_id} has auto post enabled but missing post_id or message")
                continue
                
            # Get post data
            post_data = get_post_data(user.fb_token, user.post_id)
            if not post_data:
                continue
                
            # Extract metrics
            reactions = post_data.get('reactions', {}).get('summary', {}).get('total_count', 0)
            comments = post_data.get('comments', {}).get('summary', {}).get('total_count', 0)
            shares = post_data.get('shares', {}).get('count', 0)
            
            # Format message with metrics
            message = user.post_message + f"\n\n👍 {reactions} REACTIONS | 💬 {comments} COMMENTS | 🔄 {shares} SHARES"
            message += "\n\nThis post automatically updates with the latest engagement metrics!"
            
            # Update the post
            if update_post(user.fb_token, user.post_id, message):
                logger.info(f"Successfully updated post for user {user.fb_id}")
                user.last_update = datetime.utcnow()
                session.commit()
            else:
                logger.error(f"Failed to update post for user {user.fb_id}")
                
    except Exception as e:
        logger.error(f"Error in process_auto_posts: {str(e)}")
    finally:
        session.close()
        Session.remove()

if __name__ == "__main__":
    logger.info("Starting Auto Post Scheduler")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")