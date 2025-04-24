import requests
import json
import logging
import subprocess

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
        
def create_post(token, message):
    """Create a new Facebook post
    
    Args:
        token (str): Facebook access token
        message (str): Post content
        
    Returns:
        dict: Success status and response data including post ID
    """
    try:
        url = "https://graph.facebook.com/v14.0/me/feed"
        params = {
            "message": message,
            "access_token": token
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
