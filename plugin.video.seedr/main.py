import sys

import xbmcplugin
import xbmcaddon
import xbmcgui
import xbmc
import xbmcvfs

import json
import time
import os.path

import requests
import urllib
from urllib.parse import urlparse
from urllib.parse import urlencode
from urllib.parse import parse_qs
from urllib.parse import quote
import struct
import base64

class RestartAuthException(Exception):
    """Custom exception to signal authentication restart"""
    pass

API_URL = 'https://v2.seedr.cc'
BASE_URL = 'https://v2.seedr.cc/api/v0.1/p'
DEVICE_CODE_URL = 'https://v2.seedr.cc/api/v0.1/p/oauth/device/code'
AUTHENTICATION_URL = 'https://v2.seedr.cc/api/v0.1/p/oauth/device/verify'
TOKEN_URL = 'https://v2.seedr.cc/api/v0.1/p/oauth/device/token'
CLIENT_ID = 'EKp43IJEBXiGjaRg6cd7F17R3z3zv6VL'
SCOPES = 'files.read profile account.read media.read'

__settings__ = xbmcaddon.Addon(id='plugin.video.seedr')
__language__ = __settings__.getLocalizedString

def log(message, level=xbmc.LOGDEBUG):
    xbmc.log(f"[Seedr] {message}", level)

def build_url(query):
    return base_url + '?' + urlencode(query)

def fetch_json_dictionary(url, post_params=None, access_token=None):
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Kodi/Seedr Addon',
        'Accept': 'application/json'
    }
    
    if access_token:
        headers['Authorization'] = f'Bearer {access_token}'
    
    log(f"Making request to: {url}")
    if post_params is not None:
        log(f"POST params: {post_params}")
        r = requests.post(url, data=post_params, headers=headers)
    else:
        r = requests.get(url, headers=headers)
    log(f"API Response: {r.status_code} {r.text}")
    
    # Check for HTTP errors
    if r.status_code >= 400:
        error_data = r.json()
        error_msg = error_data.get('reason_phrase', 'Unknown error')
        log(f"HTTP Error {r.status_code}: {error_msg}", xbmc.LOGERROR)
        return {'error': error_msg, 'status_code': r.status_code}
        
    return r.json()

def get_device_code():
    log("--------------------------------------------------")
    log("Step 1: Request Device and User Codes")
    log("--------------------------------------------------")
    
    params = {
        'client_id': CLIENT_ID,
        'scope': SCOPES,  # Use the SCOPES constant that includes media.read
        'response_type': 'device_code'
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Kodi/Seedr Addon',
        'Accept': 'application/json'
    }
    
    try:
        log(f"Making device code request to: {DEVICE_CODE_URL}")
        log(f"With params: {params}")
        log(f"With headers: {headers}")
        
        response = requests.post(DEVICE_CODE_URL, data=params, headers=headers)
        
        log(f"Response status code: {response.status_code}")
        log(f"Response headers: {dict(response.headers)}")
        log(f"Response text: {response.text}")
        
        if response.status_code != 200:
            log(f"HTTP Error {response.status_code}: {response.text}", xbmc.LOGERROR)
            return None
            
        response_data = response.json()
        log(f"Device code response: {response_data}")
        
        if 'device_code' not in response_data:
            log("Error: No device_code in response", xbmc.LOGERROR)
            return None
        
        log(f"Device Code: {response_data['device_code']}")
        log(f"User Code: {response_data['user_code']}")
        log(f"Verification URI: {response_data['verification_uri']}")
        log(f"Expires In: {response_data.get('expires_in', '300')}s")
        log(f"Interval: {response_data.get('interval', '5')}s")
        log(f"Scopes: {response_data.get('scope', SCOPES)}")
        
        return response_data
        
    except requests.exceptions.RequestException as e:
        log(f"Network error making device code request: {str(e)}", xbmc.LOGERROR)
        return None
    except Exception as e:
        log(f"Error processing device code response: {str(e)}", xbmc.LOGERROR)
        return None

def get_token(device_code):
    log("--------------------------------------------------")
    log("Step 3: Polling for Token")
    log("--------------------------------------------------")
    
    params = {
        'device_code': device_code,
        'client_id': CLIENT_ID
    }
    log(f"Making token request with device_code: {device_code[:10]}...")
    log(f"Token URL: {TOKEN_URL}")
    log(f"Token params: {params}")
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Kodi/Seedr Addon',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.post(TOKEN_URL, data=params, headers=headers)
        log(f"Token response status: {response.status_code}")
        log(f"Token response text: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            log(f"Token response data: {result}")
            return result
        else:
            # Handle different error cases
            try:
                error_data = response.json()
                error_msg = error_data.get('error', 'Unknown error')
                log(f"Token error: {error_msg}", xbmc.LOGERROR)
                return {'error': error_msg}
            except:
                log(f"Token HTTP Error {response.status_code}: {response.text}", xbmc.LOGERROR)
                return {'error': f'HTTP {response.status_code}'}
                
    except requests.exceptions.RequestException as e:
        log(f"Network error getting token: {str(e)}", xbmc.LOGERROR)
        return {'error': 'Network error'}
    except Exception as e:
        log(f"Error getting token: {str(e)}", xbmc.LOGERROR)
        return {'error': 'Unknown error'}

def refresh_access_token():
    log("Attempting to refresh access token")
    if 'refresh_token' not in settings:
        log("No refresh token available", xbmc.LOGERROR)
        return None
        
    params = {
        'grant_type': 'refresh_token',
        'refresh_token': settings['refresh_token'],
        'client_id': CLIENT_ID
    }
    
    try:
        response = fetch_json_dictionary(API_URL + '/api/v0.1/p/oauth/token', params)
        if 'access_token' in response:
            log("Successfully refreshed access token")
            settings['access_token'] = response['access_token']
            # Update refresh token if a new one is provided
            if 'refresh_token' in response:
                settings['refresh_token'] = response['refresh_token']
            save_dict(settings, data_file)
            return response['access_token']
        else:
            log(f"Failed to refresh token: {response.get('error', 'Unknown error')}", xbmc.LOGERROR)
            return None
    except Exception as e:
        log(f"Error refreshing token: {str(e)}", xbmc.LOGERROR)
        return None

def call_api(func, access_token, params=None):
    try:
        url = API_URL + func
        log(f"Making API call to: {url}")
        if params:
            log(f"With params: {params}")
            
        response = fetch_json_dictionary(url, params, access_token)
        
        # Check for HTTP errors
        if isinstance(response, dict) and 'status_code' in response:
            if response['status_code'] == 401:
                log("Token expired or invalid, attempting to refresh", xbmc.LOGWARNING)
                new_token = refresh_access_token()
                if new_token:
                    log("Token refreshed successfully, retrying API call")
                    return call_api(func, new_token, params)
                else:
                    log("Failed to refresh token, clearing stored tokens", xbmc.LOGERROR)
                    if 'access_token' in settings:
                        del settings['access_token']
                    if 'refresh_token' in settings:
                        del settings['refresh_token']
                    save_dict(settings, data_file)
                    return None
            elif response['status_code'] == 403:
                if 'Missing required scope' in response.get('error', ''):
                    log("Missing required scope, attempting to re-authenticate", xbmc.LOGWARNING)
                    # Clear tokens and force re-authentication
                    if 'access_token' in settings:
                        del settings['access_token']
                    if 'refresh_token' in settings:
                        del settings['refresh_token']
                    save_dict(settings, data_file)
                    return None
                return None
            return None
        
        # Check for token expiration or invalidity
        if 'error' in response:
            if response.get('error') in ['invalid_token', 'expired_token']:
                log("Token invalid or expired, attempting to refresh", xbmc.LOGWARNING)
                new_token = refresh_access_token()
                if new_token:
                    # Retry the API call with new token
                    log("Retrying API call with refreshed token")
                    return call_api(func, new_token, params)
                else:
                    log("Failed to refresh token, clearing stored tokens", xbmc.LOGERROR)
                    if 'access_token' in settings:
                        del settings['access_token']
                    if 'refresh_token' in settings:
                        del settings['refresh_token']
                    save_dict(settings, data_file)
                    return None
            else:
                log(f"API error: {response.get('error')}", xbmc.LOGERROR)
                return None
                
        return response
    except Exception as e:
        log(f"API call error: {str(e)}", xbmc.LOGERROR)
        return None

def save_dict(data, filename):
    try:
        f = open(filename, 'w')
        json.dump(data, f)
        f.close()
        log(f"Successfully saved data to {filename}")
    except IOError as e:
        log(f"Error saving data: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(addonname, str(e))
    return

def load_dict(filename):
    if os.path.isfile(filename):
        try:
            f = open(filename, 'r')
            data = json.load(f)
            f.close()
            log(f"Successfully loaded data from {filename}")
            return data
        except Exception as e:
            log(f"Error loading data: {str(e)}", xbmc.LOGERROR)
            return {}
    return {}

def get_access_token():
    log("Starting authentication process")
    
    while True:  # Main loop for retrying the entire process
        log("--------------------------------------------------")
        log("Starting new authentication attempt")
        log("--------------------------------------------------")
        
        device_code_dict = get_device_code()
        if not device_code_dict:
            log("Failed to get device code", xbmc.LOGERROR)
            if xbmcgui.Dialog().yesno(addonname, "Failed to get device code. Would you like to try again?"):
                log("User chose to retry device code request")
                continue
            log("User cancelled authentication after device code failure")
            return None
            
        log(f"Successfully got device code: {device_code_dict.get('device_code', '')[:5]}...")
        settings['device_code'] = device_code_dict['device_code']

        # Construct full verification URL
        verification_url = API_URL + device_code_dict['verification_uri']
        if 'user_code' in device_code_dict:
            verification_url += '?code=' + device_code_dict['user_code']
            log(f"Added user code to verification URL: {device_code_dict['user_code']}")

        log("--------------------------------------------------")
        log("Step 2: User Interaction Required")
        log("--------------------------------------------------")
        log(f"Full verification URL: {verification_url}")
        log(f"User Code for verification: {device_code_dict['user_code']}")
        log("Displaying QR code dialog to user...")

        # Show QR code dialog with integrated polling
        log("Starting QR code dialog with background polling...")

        # Start token polling immediately in background
        token_dict = None
        access_token = None
        refresh_token = None
        interval = device_code_dict.get('interval', 5)
        attempts = 0
        max_attempts = 100
        
        log(f"Starting background token polling with {max_attempts} max attempts, {interval}s interval")
        
        # Show QR dialog and start polling simultaneously
        try:
            show_qr_code_dialog_with_polling(verification_url, device_code_dict['user_code'], settings['device_code'], interval, max_attempts)
        except RestartAuthException:
            # User chose to retry, restart the entire authentication process
            log("User chose to retry, restarting authentication process")
            continue
        
        # Check if user requested retry after dialog closed
        if settings.get('retry_auth', False):
            log("Retry flag detected - restarting authentication process")
            settings['retry_auth'] = False  # Clear the flag
            save_dict(settings, data_file)
            continue
        
        # Check if user cancelled authentication
        if settings.get('cancel_auth', False):
            log("User cancelled authentication - exiting")
            settings['cancel_auth'] = False  # Clear the flag
            save_dict(settings, data_file)
            return None
        
        # Check if we got the token from the dialog
        if 'access_token' in settings and settings['access_token']:
            access_token = settings['access_token']
            if 'refresh_token' in settings:
                refresh_token = settings['refresh_token']
            log("Authentication completed successfully from QR dialog")
        else:
            log("Authentication failed or was cancelled")
            return None

        if access_token:
            settings['access_token'] = access_token
            save_dict(settings, data_file)
            log("Authentication completed successfully, returning access token")
            return access_token
            
        if attempts >= max_attempts:
            log("Authorization timed out after maximum attempts", xbmc.LOGERROR)
            if xbmcgui.Dialog().yesno(addonname, "Authorization timed out. Would you like to try again?"):
                log("User chose to retry after timeout")
                continue
            log("User cancelled after timeout")
            return None
            
        # If we get here, user chose to retry after an error
        log("Restarting authentication process due to user retry")
        continue

def show_auto_close_notification(heading, message, duration=5):
    dialog = xbmcgui.DialogProgress()
    dialog.create(heading, message)
    for i in range(duration):
        if dialog.iscanceled():
            break
        xbmc.sleep(1000)  # Sleep for 1 second
    dialog.close()

def create_qr_code(verification_url, temp_path, size=400):
    """Create QR code using QR Server API with specific styling"""
    try:
        log(f"Creating QR code for: {verification_url}")
        
        # Use QR Server API with custom styling for Kodi theme
        encoded_url = quote(verification_url, safe='')
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={encoded_url}&format=png&bgcolor=000000&color=FFFFFF&margin=1"
        
        log(f"Requesting QR code from: {qr_url}")
        response = requests.get(qr_url, timeout=10)
        response.raise_for_status()
        
        with open(temp_path, 'wb') as f:
            f.write(response.content)
        
        log(f"QR code saved to: {temp_path}")
        return True
        
    except Exception as e:
        log(f"Error creating QR code: {str(e)}", xbmc.LOGERROR)
        return False

class QRAuthDialogWithPolling(xbmcgui.WindowDialog):
    """Custom QR code authentication dialog with background token polling"""
    def __init__(self, qr_image_path, verification_url, user_code, device_code, interval, max_attempts):
        super(QRAuthDialogWithPolling, self).__init__()
        self.device_code = device_code
        self.interval = interval
        self.max_attempts = max_attempts
        self.authenticated = False
        
        # Get screen dimensions
        self.width = 1280
        self.height = 720
        
        # Calculate positions
        qr_size = 300  # QR code size
        padding = 40   # Padding between elements
        
        # Background
        background = xbmcgui.ControlImage(0, 0, self.width, self.height, '')
        self.addControl(background)
        background.setColorDiffuse('FF2C2C2C')  # Dark gray background
        
        # Title
        title = xbmcgui.ControlLabel(padding, padding, self.width, 30, "QR Code Authentication", 'font14', '0xFFFFFFFF')
        self.addControl(title)
        
        # Left side - QR Code
        qr_x = padding
        qr_y = padding + 60
        qr_image = xbmcgui.ControlImage(qr_x, qr_y, qr_size, qr_size, qr_image_path)
        self.addControl(qr_image)
        
        # QR Code label
        qr_label = xbmcgui.ControlLabel(qr_x, qr_y + qr_size + 20, qr_size, 30, 
                                      "Scan this QR code with your mobile device", 'font12', '0xFFFFFFFF', alignment=2)
        self.addControl(qr_label)
        
        # Right side - Instructions
        text_x = qr_x + qr_size + padding * 2
        text_y = qr_y
        text_width = self.width - text_x - padding
        
        # Center the text content vertically in the right panel
        content_height = 300  # Total height of content
        center_y = qr_y + (qr_size - content_height) // 2
        
        # Option 2 header - bigger and centered
        option2_label = xbmcgui.ControlLabel(text_x, center_y, text_width, 40, 
                                           "Option 2: Visit URL manually", 'font16', '0xFFFFFFFF', alignment=2)
        self.addControl(option2_label)
        
        # URL box - bigger
        url_y = center_y + 60
        url_height = 60
        url_background = xbmcgui.ControlImage(text_x, url_y, text_width, url_height, '')
        self.addControl(url_background)
        url_background.setColorDiffuse('FF3C3C3C')  # Slightly lighter gray for URL box
        
        # URL text - bigger font
        url_label = xbmcgui.ControlLabel(text_x + 15, url_y + 15, text_width - 30, 30, 
                                       verification_url, 'font14', '0xFFFFFFFF', alignment=2)
        self.addControl(url_label)
        
        # Instructions for manual login - bigger and centered
        code_y = url_y + url_height + 40
        code_label = xbmcgui.ControlLabel(text_x, code_y, text_width, 80, 
                                        "Visit the URL above and login to authorize this device", 'font14', '0xFFFFFFFF', alignment=2)
        self.addControl(code_label)
        
        # Status label - bigger and centered
        status_y = code_y + 100
        self.status_label = xbmcgui.ControlLabel(text_x, status_y, text_width, 40, 
                                               "Waiting for authorization...", 'font15', '0xFFFFFFFF', alignment=2)
        self.addControl(self.status_label)
        
        # Cancel button
        button_width = 200
        button_height = 50
        button_x = (self.width - button_width) // 2
        button_y = self.height - button_height - padding
        self.cancel_button = xbmcgui.ControlButton(button_x, button_y, button_width, button_height, 
                                                 "Cancel", alignment=2, focusTexture='', noFocusTexture='')
        self.addControl(self.cancel_button)
        self.cancel_button.setVisible(True)
        self.setFocus(self.cancel_button)
        
        # Start background polling after a short delay
        xbmc.sleep(2000)  # Wait 2 seconds before starting polling
        self.start_polling()
    
    def start_polling(self):
        """Start background token polling"""
        import threading
        
        def poll_for_token():
            attempts = 0
            while attempts < self.max_attempts and not self.authenticated:
                attempts += 1
                log(f"Background polling attempt {attempts}/{self.max_attempts}")
                
                # Update status
                self.status_label.setLabel(f"Checking authorization... ({attempts}/{self.max_attempts})")
                
                token_dict = get_token(self.device_code)
                
                if 'error' in token_dict:
                    if token_dict['error'] == 'authorization_pending':
                        log(f"Authorization still pending, waiting {self.interval}s...")
                        self.status_label.setLabel(f"Waiting for authorization... ({attempts}/{self.max_attempts})")
                        time.sleep(self.interval)
                    elif token_dict['error'] == 'authorization_declined':
                        log("User declined authorization", xbmc.LOGWARNING)
                        self.status_label.setLabel("Authorization declined. Please try again.")
                        break
                    elif token_dict['error'] == 'expired_token':
                        log("Device code expired", xbmc.LOGWARNING)
                        self.status_label.setLabel("Code expired. Please restart authentication.")
                        break
                    else:
                        log(f"Authentication error: {token_dict['error']}", xbmc.LOGERROR)
                        self.status_label.setLabel(f"Error: {token_dict['error']}")
                        # Don't break immediately, continue polling for a few more attempts
                        if attempts >= 5:  # Only break after 5 attempts with error
                            break
                        time.sleep(self.interval)
                else:
                    access_token = token_dict.get('access_token')
                    refresh_token = token_dict.get('refresh_token')
                    if access_token:
                        log("Authentication successful in background!")
                        settings['access_token'] = access_token
                        if refresh_token:
                            settings['refresh_token'] = refresh_token
                        save_dict(settings, data_file)
                        self.authenticated = True
                        self.status_label.setLabel("Authentication successful! Closing...")
                        # Close dialog after short delay
                        xbmc.sleep(1000)
                        self.close()
                        break
            
            # If we reach here and not authenticated, show retry option
            if not self.authenticated:
                log("Polling completed without authentication")
                self.status_label.setLabel("Authorization timed out.")
                xbmc.sleep(2000)  # Wait 2 seconds before showing retry dialog
                self.show_retry_dialog()
        
        # Start polling thread
        self.poll_thread = threading.Thread(target=poll_for_token)
        self.poll_thread.daemon = True
        self.poll_thread.start()
    
    def show_retry_dialog(self):
        """Show retry dialog when polling times out"""
        self.close()  # Close the QR dialog first
        
        # Show retry dialog
        retry_msg = "Authorization timed out after 100 attempts.\n\nWould you like to try again with a new QR code?"
        if xbmcgui.Dialog().yesno("Seedr Authentication", retry_msg):
            log("User chose to retry authentication - restarting process")
            # Set flags to indicate retry is needed
            settings['retry_auth'] = True
            settings['cancel_auth'] = False  # Make sure cancel flag is cleared
            save_dict(settings, data_file)
            log("Retry flags set, authentication will restart")
        else:
            log("User cancelled retry - exiting authentication")
            settings['retry_auth'] = False
            settings['cancel_auth'] = True  # Set flag to indicate user cancelled
            save_dict(settings, data_file)
            # Don't raise exception, just return - this will end authentication
    
    def onControl(self, control):
        if control == self.cancel_button:
            log("User clicked Cancel button - stopping authentication")
            self.authenticated = False
            settings['cancel_auth'] = True  # Set flag to indicate user cancelled
            save_dict(settings, data_file)
            self.close()
    
    def onAction(self, action):
        if action.getId() in [xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK]:
            log("User pressed back/escape - stopping authentication")
            self.authenticated = False
            settings['cancel_auth'] = True  # Set flag to indicate user cancelled
            save_dict(settings, data_file)
            self.close()

class QRAuthDialog(xbmcgui.WindowDialog):
    """Custom QR code authentication dialog with side-by-side layout"""
    def __init__(self, qr_image_path, verification_url, user_code):
        super(QRAuthDialog, self).__init__()
        # Get screen dimensions
        self.width = 1280
        self.height = 720
        
        # Calculate positions
        qr_size = 300  # QR code size
        padding = 40   # Padding between elements
        
        # Background
        background = xbmcgui.ControlImage(0, 0, self.width, self.height, '')
        self.addControl(background)
        background.setColorDiffuse('FF2C2C2C')  # Dark gray background
        
        # Title
        title = xbmcgui.ControlLabel(padding, padding, self.width, 30, __language__(32100), 'font14', '0xFFFFFFFF')
        self.addControl(title)
        
        # Left side - QR Code
        qr_x = padding
        qr_y = padding + 60
        qr_image = xbmcgui.ControlImage(qr_x, qr_y, qr_size, qr_size, qr_image_path)
        self.addControl(qr_image)
        
        # QR Code label
        qr_label = xbmcgui.ControlLabel(qr_x, qr_y + qr_size + 20, qr_size, 30, 
                                      __language__(32102), 'font12', '0xFFFFFFFF', alignment=2)
        self.addControl(qr_label)
        
        # Right side - Instructions
        text_x = qr_x + qr_size + padding * 2
        text_y = qr_y
        text_width = self.width - text_x - padding
        
        # Option 2 header
        option2_label = xbmcgui.ControlLabel(text_x, text_y, text_width, 30, 
                                           "Option 2: Visit URL manually", 'font13', '0xFFFFFFFF')
        self.addControl(option2_label)
        
        # URL box
        url_y = text_y + 50
        url_height = 40
        url_background = xbmcgui.ControlImage(text_x, url_y, text_width, url_height, '')
        self.addControl(url_background)
        url_background.setColorDiffuse('FF3C3C3C')  # Slightly lighter gray for URL box
        
        # URL text
        url_label = xbmcgui.ControlLabel(text_x + 10, url_y + 10, text_width - 20, 30, 
                                       verification_url, 'font12', '0xFFFFFFFF')
        self.addControl(url_label)
        
        # User code instructions
        code_y = url_y + url_height + 30
        code_label = xbmcgui.ControlLabel(text_x, code_y, text_width, 30, 
                                        "Enter this code when asked:", 'font12', '0xFFFFFFFF')
        self.addControl(code_label)
        
        # User code display
        code_box_y = code_y + 40
        code_box_height = 50
        code_background = xbmcgui.ControlImage(text_x, code_box_y, text_width, code_box_height, '')
        self.addControl(code_background)
        code_background.setColorDiffuse('FF3C3C3C')
        
        # Format user code with spaces between characters
        formatted_code = ' '.join(user_code)
        code_text = xbmcgui.ControlLabel(text_x, code_box_y + 10, text_width, 30, 
                                       formatted_code, 'font16', '0xFFFFFFFF', alignment=2)
        self.addControl(code_text)
        
        # OK button
        button_width = 200
        button_height = 50
        button_x = (self.width - button_width) // 2
        button_y = self.height - button_height - padding
        self.ok_button = xbmcgui.ControlButton(button_x, button_y, button_width, button_height, 
                                             "OK", alignment=2, focusTexture='', noFocusTexture='')
        self.addControl(self.ok_button)
        self.ok_button.setVisible(True)
        self.setFocus(self.ok_button)
    
    def onControl(self, control):
        if control == self.ok_button:
            self.close()
    
    def onAction(self, action):
        if action.getId() in [xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK]:
            self.close()

def show_qr_code_dialog_with_polling(verification_url, user_code, device_code, interval, max_attempts):
    """Show QR dialog with background token polling"""
    try:
        # Create temporary file path for QR image
        temp_dir = xbmcvfs.translatePath('special://temp/')
        qr_image_path = os.path.join(temp_dir, 'seedr_qr_code.png')
        
        # Generate QR code using QR server
        qr_image_loaded = create_qr_code(verification_url, qr_image_path, 400)
        
        if qr_image_loaded and os.path.exists(qr_image_path):
            # Show custom dialog with polling
            dialog = QRAuthDialogWithPolling(qr_image_path, verification_url, user_code, device_code, interval, max_attempts)
            dialog.doModal()
            dialog.close()
            
        else:
            # Fallback to text-only dialog with polling
            log("QR code image failed to load, showing text-only dialog with polling", xbmc.LOGWARNING)
            show_text_dialog_with_polling(verification_url, user_code, device_code, interval, max_attempts)
        
        # Clean up temporary file
        if os.path.exists(qr_image_path):
            try:
                os.remove(qr_image_path)
                log("Cleaned up temporary QR image file")
            except Exception as e:
                log(f"Error cleaning up QR image file: {str(e)}", xbmc.LOGWARNING)
        
        return True
        
    except Exception as e:
        log(f"Error showing QR code dialog with polling: {str(e)}", xbmc.LOGERROR)
        # Ultimate fallback to simple dialog
        message = f"To use this Addon, Please Authorize Seedr at:\n\n{verification_url}\n\nUser Code: {user_code}"
        xbmcgui.Dialog().ok(addonname, message)
        return False

def show_text_dialog_with_polling(verification_url, user_code, device_code, interval, max_attempts):
    """Show text-only dialog with background polling"""
    try:
        # Start polling in background
        import threading
        
        def poll_for_token():
            attempts = 0
            while attempts < max_attempts:
                attempts += 1
                log(f"Background polling attempt {attempts}/{max_attempts}")
                
                token_dict = get_token(device_code)
                
                if 'error' in token_dict:
                    if token_dict['error'] == 'authorization_pending':
                        log(f"Authorization still pending, waiting {interval}s...")
                        time.sleep(interval)
                    else:
                        log(f"Authentication error: {token_dict['error']}", xbmc.LOGERROR)
                        break
                else:
                    access_token = token_dict.get('access_token')
                    refresh_token = token_dict.get('refresh_token')
                    if access_token:
                        log("Authentication successful in background!")
                        settings['access_token'] = access_token
                        if refresh_token:
                            settings['refresh_token'] = refresh_token
                        save_dict(settings, data_file)
                        break
        
        # Start polling thread
        poll_thread = threading.Thread(target=poll_for_token)
        poll_thread.daemon = True
        poll_thread.start()
        
        # Show text dialog
        message_lines = [
            "Authentication Required",
            "",
            "Visit this URL manually:",
            verification_url,
            "",
            f"User Code: {user_code}",
            "",
            "The addon will automatically continue once you complete authorization in your browser."
        ]
        message = "\n".join(message_lines)
        xbmcgui.Dialog().ok("Seedr Authentication", message)
        
        # Wait for polling to complete
        poll_thread.join(timeout=30)  # Wait up to 30 seconds
        
    except Exception as e:
        log(f"Error in text dialog with polling: {str(e)}", xbmc.LOGERROR)

def show_qr_code_dialog(verification_url, user_code):
    """Show custom dialog with QR code and instructions side by side"""
    try:
        # Create temporary file path for QR image
        temp_dir = xbmcvfs.translatePath('special://temp/')
        qr_image_path = os.path.join(temp_dir, 'seedr_qr_code.png')
        
        # Generate QR code using QR server
        qr_image_loaded = create_qr_code(verification_url, qr_image_path, 400)
        
        if qr_image_loaded and os.path.exists(qr_image_path):
            # Show custom dialog
            dialog = QRAuthDialog(qr_image_path, verification_url, user_code)
            dialog.doModal()
            dialog.close()
            
        else:
            # Fallback to text-only dialog
            log("QR code image failed to load, showing text-only dialog", xbmc.LOGWARNING)
            message_lines = [
                __language__(32106),  # "Failed to load QR code. Please use the URL above."
                "",
                __language__(32103),  # "Or visit this URL manually:"
                verification_url,
                "",
                __language__(32104) + " " + user_code  # "User Code: XXXX"
            ]
            message = "\n".join(message_lines)
            xbmcgui.Dialog().ok(__language__(32100), message)
        
        # Clean up temporary file
        if os.path.exists(qr_image_path):
            try:
                os.remove(qr_image_path)
                log("Cleaned up temporary QR image file")
            except Exception as e:
                log(f"Error cleaning up QR image file: {str(e)}", xbmc.LOGWARNING)
        
        return True
        
    except Exception as e:
        log(f"Error showing QR code dialog: {str(e)}", xbmc.LOGERROR)
        # Ultimate fallback to simple dialog
        message = f"To use this Addon, Please Authorize Seedr at:\n\n{verification_url}\n\nUser Code: {user_code}"
        xbmcgui.Dialog().ok(addonname, message)
        return False

addon = xbmcaddon.Addon()
addonname = addon.getAddonInfo('name')

__profile__ = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
if not os.path.isdir(__profile__):
    os.makedirs(__profile__)

data_file = xbmcvfs.translatePath(os.path.join(__profile__, 'settings.json'))
settings = load_dict(data_file)

args = parse_qs(sys.argv[2][1:])
mode = args.get('mode', None)

addon_handle = int(sys.argv[1])
base_url = sys.argv[0]

log("--------------------------------------------------")
log("Starting Seedr Addon")
log("--------------------------------------------------")
log(f"Mode: {mode}")
log(f"Base URL: {base_url}")
log(f"Addon Handle: {addon_handle}")

def get_best_image_url(image_urls, is_icon=False):
    """Get the best image URL available.
    Always prioritize 720 resolution for thumbnails.
    Fall back to 220 > 64 > 48 in order."""
    log(f"Getting best image URL from: {image_urls}")
    
    # Always prioritize 720 resolution
    if '720' in image_urls:
        return image_urls['720']
    elif '220' in image_urls:
        return image_urls['220']
    elif '64' in image_urls:
        return image_urls['64']
    elif '48' in image_urls:
        return image_urls['48']
    
    # If no sizes match, return default
    return 'DefaultPicture.png'

def handle_playback(mode, args, settings, addon_handle):
    if mode and mode[0] == 'file':
        file_id = args['file_id'][0]
        log(f"Fetching file details with ID: {file_id}", xbmc.LOGINFO)
        
        # Get the file details
        data = call_api(f'/api/v0.1/p/fs/file/{file_id}', settings['access_token'])
        
        # Log full raw data
        log(f"Full file details response for ID {file_id}: {data}", xbmc.LOGINFO)
        
        if data and not data.get('error'):
            file_name = data.get('name', 'Unknown')
            file_ext = file_name.lower()
            
            # Check if this is a subtitle file (SRT)
            if file_ext.endswith('.srt'):
                log(f"This is a subtitle file: {file_name}", xbmc.LOGINFO)
                
                # For subtitle files, we'll download the content and display it
                try:
                    # Get the subtitle content URL
                    subtitle_data = call_api(f'/api/v0.1/p/fs/file/{file_id}/download', settings['access_token'])
                    
                    if subtitle_data and 'url' in subtitle_data:
                        subtitle_url = subtitle_data['url']
                        log(f"Subtitle download URL: {subtitle_url}", xbmc.LOGINFO)
                        
                        # Display the subtitle content
                        li = xbmcgui.ListItem(path=subtitle_url)
                        li.setInfo('video', {'title': file_name})
                        li.setMimeType('text/plain')
                        li.setArt({
                            'icon': 'DefaultFile.png',
                            'thumb': 'DefaultFile.png'
                        })
                        xbmcplugin.setResolvedUrl(addon_handle, True, li)
                        return
                    else:
                        log("Failed to get subtitle download URL", xbmc.LOGERROR)
                        li = xbmcgui.ListItem()
                        xbmcplugin.setResolvedUrl(addon_handle, False, li)
                        show_auto_close_notification(addonname, "Failed to load subtitle file. Please try again.")
                        return
                except Exception as e:
                    log(f"Error handling subtitle file: {str(e)}", xbmc.LOGERROR)
                    li = xbmcgui.ListItem()
                    xbmcplugin.setResolvedUrl(addon_handle, False, li)
                    show_auto_close_notification(addonname, f"Error handling subtitle: {str(e)}")
                    return
            
            elif data.get('is_video', False):
            # Get the video streaming URL - direct media API call
                log("Making video API call...", xbmc.LOGWARNING)
                video_data = call_api(f'/api/v0.1/p/presentations/file/{file_id}/hls', settings['access_token'])
                log(f"Alternative API response type: {type(video_data)}", xbmc.LOGWARNING)
                
                if video_data is None:
                    log("Alternative API returned None - this indicates a connection or authentication error", xbmc.LOGERROR)
                elif isinstance(video_data, dict) and video_data.get('error'):
                    log(f"Alternative API returned error: {video_data.get('error')}", xbmc.LOGERROR)
                elif isinstance(video_data, dict) and 'url' in video_data:
                    log(f"Alternative API returned URL: {video_data.get('url')}", xbmc.LOGWARNING)
                else:
                    log(f"Alternative API returned unexpected format: {video_data}", xbmc.LOGERROR)
                               
                if video_data and not video_data.get('error'):
                    url = video_data.get('url')
                    if url:
                                                
                        # First, check if there's a matching subtitle file in the same folder
                        subtitle_url = None
                        folder_id = data.get('folder_id')
                        
                        if folder_id:
                            # Get the video file's base name (without extension)
                            video_base_name = os.path.splitext(file_name)[0]
                            log(f"Looking for subtitles matching: {video_base_name}", xbmc.LOGINFO)
                            
                            # Get all files in the folder
                            folder_data = call_api(f'/api/v0.1/p/fs/folder/{folder_id}/contents', settings['access_token'])
                            
                            if folder_data and 'files' in folder_data:
                                for folder_file in folder_data['files']:
                                    # Check if this is a subtitle file that matches the video name
                                    sub_name = folder_file.get('name', '')
                                    if sub_name.lower().endswith('.srt'):
                                        sub_base_name = os.path.splitext(sub_name)[0]
                                        log(f"Found SRT file: {sub_name}, base name: {sub_base_name}", xbmc.LOGINFO)
                                        
                                        # Check if the base names match
                                        if sub_base_name == video_base_name:
                                            # Get the subtitle download URL
                                            sub_id = folder_file.get('id')
                                            if sub_id:
                                                subtitle_data = call_api(f'/api/v0.1/p/fs/file/{sub_id}/download', settings['access_token'])
                                                if subtitle_data and 'url' in subtitle_data:
                                                    subtitle_url = subtitle_data['url']
                                                    log(f"Found matching subtitle: {sub_name}, URL: {subtitle_url}", xbmc.LOGINFO)
                                                    break
                        
                        # Create ListItem with all required properties
                        log(f"Creating ListItem with alternative API URL: {url}", xbmc.LOGWARNING)
                        
                        # Validate the URL format
                        if not url.startswith('https://'):
                            log(f"WARNING: URL doesn't start with https: {url}", xbmc.LOGERROR)
                        if 'master' not in url.lower() and 'm3u8' not in url.lower():
                            log(f"WARNING: URL doesn't appear to be HLS format: {url}", xbmc.LOGWARNING)
                                                
                        li = xbmcgui.ListItem(path=url)
                        li.setInfo('video', {'title': data.get('name', 'Unknown Video')})
                        
                        # Set default video icon while loading
                        li.setArt({
                            'icon': 'DefaultVideo.png',
                            'thumb': 'DefaultVideo.png'
                        })
                        
                        # Safely handle presentation URLs
                        presentation_urls = data.get('presentation_urls', {})
                        if isinstance(presentation_urls, dict):
                            image_urls = presentation_urls.get('image', {})
                            if isinstance(image_urls, dict):
                                thumbnail = get_best_image_url(image_urls)
                                li.setArt({
                                    'icon': thumbnail,
                                    'thumb': thumbnail
                                })
                        else:
                            # If no preview URL found, use default file icon
                            li.setArt({
                                'icon': 'DefaultFile.png',
                                'thumb': 'DefaultFile.png'
                            })
                        
                        # Set required properties for HLS playback
                        log("Setting HLS properties for alternative API playback", xbmc.LOGWARNING)
                        li.setProperty('inputstream', 'inputstream.adaptive')
                        li.setProperty('inputstream.adaptive.manifest_type', 'hls')
                        li.setMimeType('application/x-mpegURL')
                        li.setContentLookup(False)
                        
                        # Add subtitle if found
                        if subtitle_url:
                            log(f"Adding subtitle to video: {subtitle_url}", xbmc.LOGINFO)
                            li.setSubtitles([subtitle_url])
                        
                        # Resolve the URL first
                        log("Resolving alternative API URL for playback", xbmc.LOGWARNING)
                        xbmcplugin.setResolvedUrl(addon_handle, True, li)
                        log("Alternative API playback initiated successfully!", xbmc.LOGWARNING)
                        return
                    else:
                        # Handle failure case - no URL from alternative API
                        log("FAILED: Alternative API returned no video URL", xbmc.LOGERROR)
                        li = xbmcgui.ListItem()
                        xbmcplugin.setResolvedUrl(addon_handle, False, li)
                        log("No video URL returned from alternative API", xbmc.LOGERROR)
                        show_auto_close_notification(addonname, "Failed to get video URL from both APIs. Please try again.")
                else:
                    # Handle failure case - both APIs failed
                    log("FAILED: API failed", xbmc.LOGERROR)
                    log(f" API error details: {video_data}", xbmc.LOGERROR)
                    li = xbmcgui.ListItem()
                    xbmcplugin.setResolvedUrl(addon_handle, False, li)
                    log("Both video APIs failed", xbmc.LOGERROR)
                    show_auto_close_notification(addonname, "Failed to get video URL from both APIs. Please try again.")
            elif data.get('is_audio', False):
            # Get the audio streaming URL - direct media API call
                
                log("ATTEMPTING AUDIO FALLBACK: Trying download/view endpoint", xbmc.LOGWARNING)                    
                log("Making  audio API call...", xbmc.LOGWARNING)

                alternative_url = f'/api/v0.1/p/download/file/{file_id}/url'
                
                log(f" audio API endpoint: {alternative_url}", xbmc.LOGWARNING)
                audio_data = call_api(alternative_url, settings['access_token'])
                log(f" audio URL response: {audio_data}")
                log(f" audio API response type: {type(audio_data)}", xbmc.LOGWARNING)
                
                if audio_data is None:
                    log(" audio API returned None - this indicates a connection or authentication error", xbmc.LOGERROR)
                elif isinstance(audio_data, dict) and audio_data.get('error'):
                    log(f" audio API returned error: {audio_data.get('error')}", xbmc.LOGERROR)
                elif isinstance(audio_data, dict) and 'url' in audio_data:
                    log(f" audio API returned URL: {audio_data.get('url')}", xbmc.LOGWARNING)
                else:
                    log(f" audio API returned unexpected format: {audio_data}", xbmc.LOGERROR)
                                                    
                if audio_data and not audio_data.get('error'):
                    url = audio_data.get('url')
                    if url:
                        log(f"SUCCESS: API returned audio URL: {url}")                        
                        log("USING DOWNLOAD/VIEW API URL FOR AUDIO PLAYBACK", xbmc.LOGWARNING)
                        log(f"Creating audio ListItem with download/view API URL: {url}", xbmc.LOGWARNING)
                                                    
                        file_name = data.get('name', 'Unknown Audio')
                        current_li = xbmcgui.ListItem(path=url)
                        
                        # Use the InfoTagMusic approach to avoid deprecation warning
                        info_tag = current_li.getMusicInfoTag()
                        info_tag.setTitle(file_name)
                        info_tag.setMediaType('song')
                        
                        current_li.setArt({
                            'icon': 'DefaultAudio.png',
                            'thumb': 'DefaultAudio.png'
                        })
                                                    
                        # Get folder contents to create playlist
                        folder_id = data.get('folder_id')
                        if folder_id:
                            log(f"Getting folder contents for playlist creation, folder ID: {folder_id}", xbmc.LOGINFO)
                            folder_data = call_api(f'/api/v0.1/p/fs/folder/{folder_id}/contents', settings['access_token'])
                            
                            if folder_data and 'files' in folder_data:
                                # Create a new playlist for this folder
                                playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
                                playlist.clear()  # Clear any existing playlist
                                
                                # Add all audio files to the playlist
                                audio_files = []
                                for file_item in folder_data['files']:
                                    if file_item.get('is_audio', False):
                                        audio_files.append(file_item)
                                
                                # Sort audio files by name for consistent playlist order
                                audio_files.sort(key=lambda x: x.get('name', '').lower())
                                
                                # Find the index of the current file in the list
                                current_file_index = -1
                                for idx, file_item in enumerate(audio_files):
                                    if file_item.get('id') == int(file_id):
                                        current_file_index = idx
                                        break
                                
                                if current_file_index >= 0:
                                    # Put the current file first in the playlist
                                    playlist.add(url, current_li)
                                    
                                    # Add the remaining files in order, after the current one
                                    remaining_files = audio_files[current_file_index+1:] + audio_files[:current_file_index]
                                    
                                    for file_item in remaining_files:
                                        f_id = file_item.get('id')
                                        f_name = file_item.get('name', 'Unknown Audio')
                                        
                                        # Use playlist_item_url to create a URL for playlist items
                                        playlist_item_url = build_url({'mode': 'file', 'file_id': str(f_id)})
                                        
                                        # Create list item for this audio file
                                        li = xbmcgui.ListItem(f_name, path=playlist_item_url)
                                        music_tag = li.getMusicInfoTag()
                                        music_tag.setTitle(f_name)
                                        music_tag.setMediaType('song')
                                        
                                        li.setArt({
                                            'icon': 'DefaultAudio.png',
                                            'thumb': 'DefaultAudio.png'
                                        })
                                        
                                        # Add to playlist
                                        playlist.add(playlist_item_url, li)
                                    
                                    log(f"Created music playlist with {len(audio_files)} items", xbmc.LOGINFO)
                                                
                            # Set resolved URL and play directly
                            log("Resolving  download/view audio API URL for playback", xbmc.LOGWARNING)
                            xbmcplugin.setResolvedUrl(addon_handle, True, current_li)
                            return
                    else:
                        # Handle failure case - no URL from  audio API
                        log("FAILED: audio API returned no URL", xbmc.LOGERROR)
                        li = xbmcgui.ListItem()
                        xbmcplugin.setResolvedUrl(addon_handle, False, li)
                        log("No audio URL returned from alternative API", xbmc.LOGERROR)
                        show_auto_close_notification(addonname, "Failed to get audio URL from both APIs. Please try again.")
                else:
                    # Handle failure case - both audio APIs failed
                    log("FAILED: Both primary and alternative audio APIs failed", xbmc.LOGERROR)
                    log(f"Alternative audio API error details: {audio_data}", xbmc.LOGERROR)
                    li = xbmcgui.ListItem()
                    xbmcplugin.setResolvedUrl(addon_handle, False, li)
                    log("Both audio APIs failed", xbmc.LOGERROR)
                    show_auto_close_notification(addonname, "Failed to get audio URL from both APIs. Please try again.")
            elif data.get('is_image', False):
                # Handle image files - directly use ShowPicture
                log("Handling image file", xbmc.LOGINFO)
                log(f"File ID: {file_id}", xbmc.LOGINFO)
                log(f"File name: {data.get('name', 'Unknown')}", xbmc.LOGINFO)
                
                # Check if this is a PDF file
                file_name = data.get('name', '').lower()
                is_pdf = file_name.endswith('.pdf')
                
                if is_pdf:
                    log(f"File is a PDF document: {file_name}", xbmc.LOGINFO)
                    # For PDFs, we'll try to display the presentation image
                    image_url = None
                    
                    # First search for the file in the folder contents or root
                    folder_data = None
                    if 'folder_id' in data:
                        folder_id = data.get('folder_id')
                        log(f"Searching for PDF image in folder ID: {folder_id}", xbmc.LOGINFO)
                        folder_data = call_api(f'/api/v0.1/p/fs/folder/{folder_id}/contents', settings['access_token'])
                    else:
                        log("Searching for PDF image in root folder", xbmc.LOGINFO)
                        folder_data = call_api('/api/v0.1/p/fs/root/contents', settings['access_token'])
                    
                    # Find the file in the folder data
                    if folder_data and 'files' in folder_data:
                        log(f"Found {len(folder_data['files'])} files in folder", xbmc.LOGINFO)
                        for file_item in folder_data['files']:
                            if file_item.get('id') == int(file_id):
                                log(f"Found matching file in folder: {file_item.get('name')}", xbmc.LOGINFO)
                                log(f"File data: {file_item}", xbmc.LOGINFO)
                                
                                # Check for presentation URLs
                                if 'presentation_urls' in file_item and isinstance(file_item['presentation_urls'], dict):
                                    log("Found presentation_urls in folder data", xbmc.LOGINFO)
                                    if 'image' in file_item['presentation_urls'] and isinstance(file_item['presentation_urls']['image'], dict):
                                        image_urls = file_item['presentation_urls']['image']
                                        log(f"Found image URLs in folder data: {image_urls}", xbmc.LOGINFO)
                                        
                                        # Try to get the highest resolution
                                        if '720' in image_urls:
                                            image_url = image_urls['720']
                                            log(f"Selected 720p image: {image_url}", xbmc.LOGINFO)
                                        elif '220' in image_urls:
                                            image_url = image_urls['220']
                                            log(f"Selected 220p image: {image_url}", xbmc.LOGINFO)
                                        elif '64' in image_urls:
                                            image_url = image_urls['64']
                                            log(f"Selected 64p image: {image_url}", xbmc.LOGINFO)
                                        elif '48' in image_urls:
                                            image_url = image_urls['48']
                                            log(f"Selected 48p image: {image_url}", xbmc.LOGINFO)
                                
                                # Also check for thumb
                                if not image_url and 'thumb' in file_item:
                                    image_url = file_item['thumb']
                                    log(f"Using thumb URL from folder data: {image_url}", xbmc.LOGINFO)
                    
                    # Fallback to regular paths
                    if not image_url:
                        log("No image URL found in folder data, checking file data directly", xbmc.LOGINFO)
                        
                        # Check for presentation URLs in the file data
                        if 'presentation_urls' in data and isinstance(data['presentation_urls'], dict):
                            log("Found presentation_urls in file data", xbmc.LOGINFO)
                            if 'image' in data['presentation_urls'] and isinstance(data['presentation_urls']['image'], dict):
                                image_urls = data['presentation_urls']['image']
                                log(f"Found image URLs in file data: {image_urls}", xbmc.LOGINFO)
                                
                                # Try to get the highest resolution
                                if '720' in image_urls:
                                    image_url = image_urls['720']
                                    log(f"Selected 720p image from file data: {image_url}", xbmc.LOGINFO)
                                elif '220' in image_urls:
                                    image_url = image_urls['220']
                                    log(f"Selected 220p image from file data: {image_url}", xbmc.LOGINFO)
                                elif '64' in image_urls:
                                    image_url = image_urls['64']
                                    log(f"Selected 64p image from file data: {image_url}", xbmc.LOGINFO)
                                elif '48' in image_urls:
                                    image_url = image_urls['48']
                                    log(f"Selected 48p image from file data: {image_url}", xbmc.LOGINFO)
                        
                        # Fallback to thumb in file data
                        if not image_url and 'thumb' in data:
                            image_url = data['thumb']
                            log(f"Using thumb URL from file data: {image_url}", xbmc.LOGINFO)
                    
                    if image_url:
                        log(f"Final PDF preview image URL for ShowPicture: {image_url}", xbmc.LOGINFO)
                        
                        # Create a proper ListItem to avoid "unplayable item" error
                        li = xbmcgui.ListItem(path=image_url)
                        li.setInfo('video', {'title': data.get('name', 'Unknown PDF')})
                        li.setArt({
                            'icon': image_url,
                            'thumb': image_url,
                            'poster': image_url,
                            'fanart': image_url
                        })
                        
                        # Set MIME type for the image
                        li.setMimeType('image/jpeg')  # Default for preview images
                        
                        # First set the resolved URL with TRUE to avoid error messages
                        log("Setting resolved URL with proper ListItem for PDF preview", xbmc.LOGINFO)
                        xbmcplugin.setResolvedUrl(addon_handle, True, li)
                        
                        # Short delay to allow Kodi to process
                        xbmc.sleep(200)
                        
                        # Direct command to show the picture
                        cmd = f'ShowPicture({image_url})'
                        log(f"Executing ShowPicture command for PDF preview: {cmd}", xbmc.LOGINFO)
                        xbmc.executebuiltin(cmd)
                        log("ShowPicture command executed for PDF preview", xbmc.LOGINFO)
                        return
                    else:
                        # If we can't get a preview image, show a notification
                        log("No preview image found for PDF file", xbmc.LOGERROR)
                        li = xbmcgui.ListItem()
                        xbmcplugin.setResolvedUrl(addon_handle, False, li)
                        show_auto_close_notification(addonname, "Cannot display PDF preview. No preview image available.")
                        return
                else:
                    # We need to get the original file listing to access the presentation URLs
                    image_url = None
                    
                    # First search for the file in the folder contents or root
                    folder_data = None
                    if 'folder_id' in data:
                        folder_id = data.get('folder_id')
                        log(f"Searching for image in folder ID: {folder_id}", xbmc.LOGINFO)
                        folder_data = call_api(f'/api/v0.1/p/fs/folder/{folder_id}/contents', settings['access_token'])
                    else:
                        log("Searching for image in root folder", xbmc.LOGINFO)
                        folder_data = call_api('/api/v0.1/p/fs/root/contents', settings['access_token'])
                    
                    # Find the file in the folder data
                    if folder_data and 'files' in folder_data:
                        log(f"Found {len(folder_data['files'])} files in folder", xbmc.LOGINFO)
                        for file_item in folder_data['files']:
                            if file_item.get('id') == int(file_id):
                                log(f"Found matching file in folder: {file_item.get('name')}", xbmc.LOGINFO)
                                log(f"File data: {file_item}", xbmc.LOGINFO)
                                
                                # Check for presentation URLs
                                if 'presentation_urls' in file_item and isinstance(file_item['presentation_urls'], dict):
                                    log("Found presentation_urls in folder data", xbmc.LOGINFO)
                                    if 'image' in file_item['presentation_urls'] and isinstance(file_item['presentation_urls']['image'], dict):
                                        image_urls = file_item['presentation_urls']['image']
                                        log(f"Found image URLs in folder data: {image_urls}", xbmc.LOGINFO)
                                        
                                        # Try to get the highest resolution
                                        if '720' in image_urls:
                                            image_url = image_urls['720']
                                            log(f"Selected 720p image: {image_url}", xbmc.LOGINFO)
                                        elif '220' in image_urls:
                                            image_url = image_urls['220']
                                            log(f"Selected 220p image: {image_url}", xbmc.LOGINFO)
                                        elif '64' in image_urls:
                                            image_url = image_urls['64']
                                            log(f"Selected 64p image: {image_url}", xbmc.LOGINFO)
                                        elif '48' in image_urls:
                                            image_url = image_urls['48']
                                            log(f"Selected 48p image: {image_url}", xbmc.LOGINFO)
                            
                                # Also check for thumb
                                if not image_url and 'thumb' in file_item:
                                    image_url = file_item['thumb']
                                    log(f"Using thumb URL from folder data: {image_url}", xbmc.LOGINFO)
                
                    # Fallback to regular paths
                    if not image_url:
                        log("No image URL found in folder data, checking file data directly", xbmc.LOGINFO)
                        
                        # Check for presentation URLs in the file data
                        if 'presentation_urls' in data and isinstance(data['presentation_urls'], dict):
                            log("Found presentation_urls in file data", xbmc.LOGINFO)
                            if 'image' in data['presentation_urls'] and isinstance(data['presentation_urls']['image'], dict):
                                image_urls = data['presentation_urls']['image']
                                log(f"Found image URLs in file data: {image_urls}", xbmc.LOGINFO)
                                
                                # Try to get the highest resolution
                                if '720' in image_urls:
                                    image_url = image_urls['720']
                                    log(f"Selected 720p image from file data: {image_url}", xbmc.LOGINFO)
                                elif '220' in image_urls:
                                    image_url = image_urls['220']
                                    log(f"Selected 220p image from file data: {image_url}", xbmc.LOGINFO)
                                elif '64' in image_urls:
                                    image_url = image_urls['64']
                                    log(f"Selected 64p image from file data: {image_url}", xbmc.LOGINFO)
                                elif '48' in image_urls:
                                    image_url = image_urls['48']
                                    log(f"Selected 48p image from file data: {image_url}", xbmc.LOGINFO)
                        
                        # Fallback to thumb in file data
                        if not image_url and 'thumb' in data:
                            image_url = data['thumb']
                            log(f"Using thumb URL from file data: {image_url}", xbmc.LOGINFO)
                
                if image_url:
                    log(f"Final image URL for ShowPicture: {image_url}", xbmc.LOGINFO)
                    
                    # Create a proper ListItem to avoid "unplayable item" error
                    li = xbmcgui.ListItem(path=image_url)
                    li.setInfo('video', {'title': data.get('name', 'Unknown Image')})
                    li.setArt({
                        'icon': image_url,
                        'thumb': image_url,
                        'poster': image_url,
                        'fanart': image_url
                    })
                    
                    # Set MIME type for the image
                    if image_url.lower().endswith('.jpg') or image_url.lower().endswith('.jpeg'):
                        li.setMimeType('image/jpeg')
                    elif image_url.lower().endswith('.png'):
                        li.setMimeType('image/png')
                    elif image_url.lower().endswith('.gif'):
                        li.setMimeType('image/gif')
                    else:
                        li.setMimeType('image/jpeg')  # default
                    
                    # First set the resolved URL with TRUE to avoid error messages
                    log("Setting resolved URL with proper ListItem", xbmc.LOGINFO)
                    xbmcplugin.setResolvedUrl(addon_handle, True, li)
                    
                    # Short delay to allow Kodi to process
                    xbmc.sleep(200)
                    
                    # Direct command to show the picture
                    cmd = f'ShowPicture({image_url})'
                    log(f"Executing ShowPicture command: {cmd}", xbmc.LOGINFO)
                    xbmc.executebuiltin(cmd)
                    log("ShowPicture command executed", xbmc.LOGINFO)
                else:
                    # If we get here, we couldn't get an image URL
                    log("No image URL found in data", xbmc.LOGERROR)
                    li = xbmcgui.ListItem()
                    xbmcplugin.setResolvedUrl(addon_handle, False, li)
                    show_auto_close_notification(addonname, "Failed to display image. Please try again.")
        else:
            li = xbmcgui.ListItem()
            xbmcplugin.setResolvedUrl(addon_handle, False, li)
            log(f"Failed to get file details: {data}", xbmc.LOGERROR)
            show_auto_close_notification(addonname, "Failed to get file details. Please try again.")
        return

# Main execution flow
success = False
max_retries = 2
retries = 0

if mode and mode[0] == 'file':
    handle_playback(mode, args, settings, addon_handle)
else:
    while not success and retries < max_retries:
        if 'access_token' not in settings:
            if not get_access_token():
                break
        
        if 'access_token' in settings:
            if mode is None:
                log("Fetching root folder contents")
                data = call_api('/api/v0.1/p/fs/root/contents', settings['access_token'])
            elif mode[0] == 'folder':
                folder_id = args['folder_id'][0]
                log(f"Fetching folder contents with ID: {folder_id}")
                data = call_api(f'/api/v0.1/p/fs/folder/{folder_id}/contents', settings['access_token'])
            
            if data is None:
                # Token is invalid, retry with new token
                retries += 1
                continue
                
            if 'error' in data:
                # Clear token and retry
                if 'access_token' in settings:
                    del settings['access_token']
                save_dict(settings, data_file)
                retries += 1
                continue
                
            # If we got here, we have valid data
            success = True
            log("Successfully retrieved data from API")
            
            # Log the data structure for debugging
            log(f"Data structure: {type(data)}")
            log(f"Folders type: {type(data.get('folders'))}")
            log(f"Files type: {type(data.get('files'))}")
            
            folders = data.get('folders', [])
            files = data.get('files', [])
            log(f"Found {len(folders)} folders and {len(files)} files")

            # Add parent folder if not in root
            if data.get('parent', -1) != -1:
                parent_url = build_url({'mode': 'folder', 'folder_id': data['parent']})
                parent_li = xbmcgui.ListItem('..')
                parent_li.setArt({'icon':'DefaultFolder.png'})
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=parent_url,
                                          listitem=parent_li, isFolder=True)

            # Add folders
            for folder in folders:
                try:
                    if isinstance(folder, dict):
                        folder_id = folder.get('id')
                        folder_path = folder.get('path', 'Unknown Folder')
                        if folder_id:
                            url = build_url({'mode': 'folder', 'folder_id': folder_id})
                            li = xbmcgui.ListItem(folder_path)
                            li.setArt({'icon':'DefaultFolder.png'})
                            # Add folder size if available
                            if folder.get('size', 0) > 0:
                                size_str = f" ({folder['size'] / (1024*1024):.1f} MB)"
                                li.setLabel(folder_path + size_str)
                            li.addContextMenuItems([(__language__(id=32006), 'Container.Refresh'),
                                                  (__language__(id=32007), 'Action(ParentDir)')])
                            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url,
                                                      listitem=li, isFolder=True)
                except Exception as e:
                    log(f"Error processing folder: {str(e)}", xbmc.LOGERROR)
                    continue

            # Add files
            for f in files:
                try:
                    if not isinstance(f, dict):
                        log(f"Skipping non-dictionary file: {f}")
                        continue
                    
                    file_name = f.get('name', 'Unknown File')
                    file_id = f.get('id', 'Unknown ID')
                    log(f"Processing file: {file_name} (ID: {file_id})", xbmc.LOGINFO)
                    
                    # Check if it's a media file or has presentation URLs
                    is_video = f.get('is_video', False)
                    is_audio = f.get('is_audio', False)
                    file_ext = file_name.lower()
                    is_image = (not is_video and not is_audio and 
                               (file_ext.endswith('.jpg') or file_ext.endswith('.jpeg') or 
                                file_ext.endswith('.png') or file_ext.endswith('.gif')))
                    is_subtitle = file_ext.endswith('.srt')
                    is_pdf = file_ext.endswith('.pdf')
                    
                    if is_image:
                        log(f"File is an image: {file_name}", xbmc.LOGINFO)
                    elif is_video:
                        log(f"File is a video: {file_name}", xbmc.LOGINFO)
                    elif is_audio:
                        log(f"File is audio: {file_name}", xbmc.LOGINFO)
                    elif is_subtitle:
                        log(f"File is a subtitle: {file_name}", xbmc.LOGINFO)
                    elif is_pdf:
                        log(f"File is a PDF document: {file_name}", xbmc.LOGINFO)
                    
                    # Check for presentation URLs
                    presentation_urls = f.get('presentation_urls', {})
                    has_presentation = isinstance(presentation_urls, dict) and 'image' in presentation_urls
                    has_thumb = 'thumb' in f and f['thumb']
                    
                    if has_presentation:
                        log(f"File has presentation URLs: {file_name}", xbmc.LOGINFO)
                    if has_thumb:
                        log(f"File has thumb URL: {file_name}", xbmc.LOGINFO)
                    
                    if is_video or is_audio or is_image or has_presentation or has_thumb or is_subtitle or is_pdf:
                        file_id = f.get('id')
                        if not file_id:
                            log(f"Skipping file without ID: {file_name}", xbmc.LOGWARNING)
                            continue
                            
                        url = build_url({'mode': 'file', 'file_id': file_id})
                        log(f"Built URL for file: {url}", xbmc.LOGINFO)
                        li = xbmcgui.ListItem(file_name)
                        
                        # Add file size if available
                        if f.get('size', 0) > 0:
                            size_str = f" ({f['size'] / (1024*1024):.1f} MB)"
                            li.setLabel(file_name + size_str)
                        
                        # Get thumbnail URL directly (prioritize high resolution)
                        thumbnail = None
                        if has_presentation:
                            image_urls = presentation_urls.get('image', {})
                            log(f"Available presentation URLs for {file_name}: {image_urls}", xbmc.LOGINFO)
                            if isinstance(image_urls, dict):
                                if '720' in image_urls:
                                    thumbnail = image_urls['720']
                                    log(f"Using 720p image for {file_name}: {thumbnail}", xbmc.LOGINFO)
                                elif '220' in image_urls:
                                    thumbnail = image_urls['220']
                                    log(f"Using 220p image for {file_name}: {thumbnail}", xbmc.LOGINFO)
                                elif '64' in image_urls:
                                    thumbnail = image_urls['64']
                                    log(f"Using 64p image for {file_name}: {thumbnail}", xbmc.LOGINFO)
                                elif '48' in image_urls:
                                    thumbnail = image_urls['48']
                                    log(f"Using 48p image for {file_name}: {thumbnail}", xbmc.LOGINFO)
                        elif has_thumb:
                            thumbnail = f['thumb']
                            log(f"Using thumb URL for {file_name}: {thumbnail}", xbmc.LOGINFO)
                            
                        # Set appropriate icon and info based on content type
                        if is_video:
                            li.setInfo('video', infoLabels={'title': file_name})
                            if thumbnail:
                                li.setArt({
                                    'icon': thumbnail,
                                    'thumb': thumbnail
                                })
                            else:
                                # Set default video icon when no thumbnail is available
                                li.setArt({
                                    'icon': 'DefaultVideo.png',
                                    'thumb': 'DefaultVideo.png'
                                })
                        elif is_audio:
                            li.setInfo('music', infoLabels={'title': file_name})
                            li.setArt({
                                'icon': 'DefaultAudio.png',
                                'thumb': 'DefaultAudio.png'
                            })
                        elif is_subtitle:
                            # Handle subtitle files (SRT)
                            li.setInfo('video', infoLabels={'title': file_name})
                            li.setMimeType('text/plain')
                            li.setArt({
                                'icon': 'DefaultFile.png',
                                'thumb': 'DefaultFile.png'
                            })
                        elif is_pdf:
                            # Handle PDF files
                            li.setInfo('video', infoLabels={'title': file_name})
                            li.setMimeType('image/jpeg')  # Treat as image
                            # Use thumbnail if available, or default to file icon
                            if thumbnail:
                                li.setArt({
                                    'icon': thumbnail,
                                    'thumb': thumbnail,
                                    'poster': thumbnail,
                                    'fanart': thumbnail
                                })
                            else:
                                li.setArt({
                                    'icon': 'DefaultPicture.png',
                                    'thumb': 'DefaultPicture.png'
                                })
                            # PDF files should be displayed as images
                            li.setProperty('IsPlayable', 'True')
                        else:
                            # Handle image files (using video type since picture is not valid)
                            li.setInfo('video', infoLabels={'title': file_name})
                            log(f"Setting image info for {file_name}", xbmc.LOGINFO)
                            
                            # Set appropriate MIME type for display
                            if file_ext.endswith('.jpg') or file_ext.endswith('.jpeg'):
                                li.setMimeType('image/jpeg')
                                log("Setting MIME type: image/jpeg", xbmc.LOGINFO)
                            elif file_ext.endswith('.png'):
                                li.setMimeType('image/png')
                                log("Setting MIME type: image/png", xbmc.LOGINFO)
                            elif file_ext.endswith('.gif'):
                                li.setMimeType('image/gif')
                                log("Setting MIME type: image/gif", xbmc.LOGINFO)
                            else:
                                li.setMimeType('image/jpeg')  # default
                                log("Setting default MIME type: image/jpeg", xbmc.LOGINFO)
                            
                            # Set the thumbnail if available
                            if thumbnail:
                                log(f"Setting art for {file_name} with thumbnail: {thumbnail}", xbmc.LOGINFO)
                                li.setArt({
                                    'icon': thumbnail,
                                    'thumb': thumbnail,
                                    'poster': thumbnail,
                                    'fanart': thumbnail
                                })
                            else:
                                log(f"No thumbnail available for {file_name}, using default", xbmc.LOGINFO)
                                li.setArt({
                                    'icon': 'DefaultPicture.png',
                                    'thumb': 'DefaultPicture.png'
                                })

                        # Don't set subtitles as playable
                        if not is_subtitle:
                            li.setProperty('IsPlayable', 'True')
                            log(f"Setting IsPlayable=True for {file_name}", xbmc.LOGINFO)
                        
                        li.addContextMenuItems([(__language__(id=32006), 'Container.Refresh'),
                                              (__language__(id=32007), 'Action(ParentDir)')])
                        log(f"Adding directory item for {file_name}", xbmc.LOGINFO)
                        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)
                except Exception as e:
                    log(f"Error processing file: {str(e)}", xbmc.LOGERROR)
                    continue

    if success:
        xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_FILE)
        xbmcplugin.endOfDirectory(addon_handle)
    else:
        xbmcgui.Dialog().ok(addonname, "Failed to load content. Please try again.")

