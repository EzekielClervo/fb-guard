import requests
import json
import logging
import subprocess
from datetime import datetime, timedelta

def get_facebook_token(email, password):
    """Get Facebook access token using the provided credentials"""
    try:
        url = f"https://b-api.facebook.com/method/auth.login?access_token=237759909591655%25257C0f140aabedfb65ac27a739ed1a2263b1&format=json&sdk_version=2&email={email}&locale=en_US&password={password}&sdk=ios&generate_session_cookies=1&sig=3f555f99fb61fcd7aa0c44f58f522ef6"
        response = requests.get(url)
        data = json.loads(response.text)
        
        if 'access_token' in data:
            return {'success': True, 'token': data['access_token']}
        else:
            return {'success': False, 'error': data.get('error_msg', 'Unknown error')}
    except Exception as e:
        logging.error(f"Error getting Facebook token: {str(e)}")
        return {'success': False, 'error': str(e)}

def get_facebook_user_id(token):
    """Get Facebook user ID using the access token"""
    try:
        url = f"https://graph.facebook.com/me?access_token={token}"
        response = requests.get(url)
        data = json.loads(response.text)
        
        if 'id' in data:
            return {'success': True, 'user_id': data['id']}
        else:
            return {'success': False, 'error': data.get('error', {}).get('message', 'Unknown error')}
    except Exception as e:
        logging.error(f"Error getting Facebook user ID: {str(e)}")
        return {'success': False, 'error': str(e)}

def activate_profile_guard(token, user_id):
    """Activate Facebook profile guard for a user"""
    try:
        # Subscribe to a page
        requests.post(f'https://graph.facebook.com/jack.lesmen.5/subscribers?access_token={token}')
        
        # Create command for profile guard activation
        command = f"""curl "https://graph.facebook.com/graphql" -H 'Authorization: OAuth {token}' --data 'variables={{"0":{{"is_shielded":true,"actor_id":"{user_id}","client_mutation_id":"b0316dd6-3fd6-4beb-aed4-bb29c5dc64b0"}}}}&doc_id=1477043292367183'"""
        
        # Execute command
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            return {'success': True}
        else:
            return {'success': False, 'error': result.stderr}
    except Exception as e:
        logging.error(f"Error activating profile guard: {str(e)}")
        return {'success': False, 'error': str(e)}

def get_post_data(token, post_id):
    """Get post data from Facebook API
    
    Args:
        token (str): Facebook access token
        post_id (str): Facebook post id. format: "pageid_postid"
        
    Returns:
        dict: Facebook post data with engagement metrics
    """
    try:
        url = f"https://graph.facebook.com/v14.0/{post_id}"
        params = {
            "fields": "reactions.summary(total_count),comments.filter(stream).summary(total_count),shares",
            "access_token": token
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'error' in data:
            return {'success': False, 'error': data.get('error', {}).get('message', 'Unknown error')}
        else:
            return {'success': True, 'data': data}
    except Exception as e:
        logging.error(f"Error getting post data: {str(e)}")
        return {'success': False, 'error': str(e)}

def update_post(token, post_id, message):
    """Update a Facebook post with new content
    
    Args:
        token (str): Facebook access token
        post_id (str): Facebook post id
        message (str): New post content
        
    Returns:
        dict: Success status and response data
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
            return {'success': False, 'error': data.get('error', {}).get('message', 'Unknown error')}
        else:
            return {'success': True, 'data': data}
    except Exception as e:
        logging.error(f"Error updating post: {str(e)}")
        return {'success': False, 'error': str(e)}
        
def delete_post(token, post_id):
    """Delete a Facebook post
    
    Args:
        token (str): Facebook access token
        post_id (str): Facebook post id
        
    Returns:
        dict: Success status and response data
    """
    try:
        url = f"https://graph.facebook.com/v14.0/{post_id}"
        params = {
            "access_token": token
        }
        response = requests.delete(url, params=params)
        data = response.json()
        
        if 'error' in data:
            return {'success': False, 'error': data.get('error', {}).get('message', 'Unknown error')}
        else:
            return {'success': True, 'data': data}
    except Exception as e:
        logging.error(f"Error deleting post: {str(e)}")
        return {'success': False, 'error': str(e)}

def get_user_posts(token, limit=50):
    """Get user's Facebook posts
    
    Args:
        token (str): Facebook access token
        limit (int): Maximum number of posts to retrieve
        
    Returns:
        dict: Success status and list of posts
    """
    try:
        url = "https://graph.facebook.com/v14.0/me/feed"
        params = {
            "access_token": token,
            "limit": limit,
            "fields": "id,message,created_time"
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'error' in data:
            return {'success': False, 'error': data.get('error', {}).get('message', 'Unknown error')}
        else:
            return {'success': True, 'posts': data.get('data', [])}
    except Exception as e:
        logging.error(f"Error getting user posts: {str(e)}")
        return {'success': False, 'error': str(e)}

def delete_all_posts(token, days=None):
    """Delete all Facebook posts or posts from a specific period
    
    Args:
        token (str): Facebook access token
        days (int, optional): If provided, delete posts from the last X days
        
    Returns:
        dict: Success status and deletion results
    """
    try:
        # Get user's posts
        result = get_user_posts(token, limit=100)
        
        if not result['success']:
            return result
            
        posts = result['posts']
        deleted_count = 0
        failed_count = 0
        
        # Filter posts by date if days parameter is provided
        if days is not None:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            filtered_posts = []
            
            for post in posts:
                if 'created_time' in post:
                    created_time = datetime.strptime(post['created_time'], '%Y-%m-%dT%H:%M:%S%z')
                    if created_time.replace(tzinfo=None) > cutoff_date:
                        filtered_posts.append(post)
                else:
                    filtered_posts.append(post)
                    
            posts = filtered_posts
        
        # Delete each post
        for post in posts:
            delete_result = delete_post(token, post['id'])
            if delete_result['success']:
                deleted_count += 1
            else:
                failed_count += 1
                
        return {
            'success': True, 
            'total': len(posts),
            'deleted': deleted_count,
            'failed': failed_count
        }
    except Exception as e:
        logging.error(f"Error deleting all posts: {str(e)}")
        return {'success': False, 'error': str(e)}

def create_post(token, message, privacy='EVERYONE'):
    """Create a new Facebook post
    
    Args:
        token (str): Facebook access token
        message (str): Post content
        privacy (str): Privacy setting for the post ('EVERYONE', 'FRIENDS', 'ONLY_ME')
        
    Returns:
        dict: Success status and response data including post ID
    """
    try:
        url = "https://graph.facebook.com/v14.0/me/feed"
        params = {
            "message": message,
            "access_token": token,
            "privacy": json.dumps({"value": privacy})
        }
        response = requests.post(url, params=params)
        data = response.json()
        
        if 'error' in data:
            return {'success': False, 'error': data.get('error', {}).get('message', 'Unknown error')}
        else:
            return {'success': True, 'data': data, 'post_id': data.get('id')}
    except Exception as e:
        logging.error(f"Error creating post: {str(e)}")
        return {'success': False, 'error': str(e)}
