import requests
import json
import logging

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
        import subprocess
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            return {'success': True}
        else:
            return {'success': False, 'error': result.stderr}
    except Exception as e:
        logging.error(f"Error activating profile guard: {str(e)}")
        return {'success': False, 'error': str(e)}
