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
        'scope': SCOPES  # Use the SCOPES constant that includes media.read
    }
    response = fetch_json_dictionary(DEVICE_CODE_URL, params)
    log(f"Device code response: {response}")
    
    if 'device_code' not in response:
        log("Error: No device_code in response", xbmc.LOGERROR)
        raise Exception("Failed to get device code from Seedr API")
    
    log(f"Device Code: {response['device_code']}")
    log(f"User Code: {response['user_code']}")
    log(f"Verification URI: {response['verification_uri']}")
    log(f"Expires In: {response['expires_in']}s")
    log(f"Interval: {response['interval']}s")
    log(f"Scopes: {response.get('scope', 'No scopes returned')}")
    
    return response

def get_token(device_code):
    log("--------------------------------------------------")
    log("Step 3: Polling for Token")
    log("--------------------------------------------------")
    
    params = {
        'device_code': device_code,
        'client_id': CLIENT_ID
    }
    log(f"Making token request with device_code: {device_code}")
    return fetch_json_dictionary(TOKEN_URL, params)

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
        device_code_dict = get_device_code()
        if not device_code_dict:
            if xbmcgui.Dialog().yesno(addonname, "Failed to get device code. Would you like to try again?"):
                continue
            return None
            
        settings['device_code'] = device_code_dict['device_code']

        # Construct full verification URL
        verification_url = API_URL + device_code_dict['verification_uri']
        if 'user_code' in device_code_dict:
            verification_url += '?code=' + device_code_dict['user_code']

        log("--------------------------------------------------")
        log("Step 2: User Interaction Required")
        log("--------------------------------------------------")
        log(f"Verification URL: {verification_url}")
        log(f"User Code: {device_code_dict['user_code']}")

        message = "To use this Addon, Please Authorize Seedr at:\n\n" + verification_url 
        xbmcgui.Dialog().ok(addonname, message)

        token_dict = None
        access_token = None
        refresh_token = None
        interval = device_code_dict.get('interval', 5)
        attempts = 0
        max_attempts = 30
        
        while access_token is None and attempts < max_attempts:
            attempts += 1
            log(f"Polling attempt {attempts}")
            token_dict = get_token(settings['device_code'])
            
            if 'error' in token_dict:
                if token_dict['error'] == 'authorization_pending':
                    log("Authorization still pending, waiting...")
                    time.sleep(interval)
                else:
                    log(f"Authentication error: {token_dict['error']}", xbmc.LOGERROR)
                    if xbmcgui.Dialog().yesno(addonname, f"Error: {token_dict['error']}\nWould you like to try again?"):
                        break  # Break inner loop to restart the process
                    return None
            else:
                access_token = token_dict.get('access_token')
                refresh_token = token_dict.get('refresh_token')
                if access_token:
                    log("Authentication successful!")
                    log(f"Access token obtained: {access_token[:10]}...")
                    if refresh_token:
                        log("Refresh token obtained")
                        settings['refresh_token'] = refresh_token
                    break

        if access_token:
            settings['access_token'] = access_token
            save_dict(settings, data_file)
            return access_token
            
        if attempts >= max_attempts:
            if xbmcgui.Dialog().yesno(addonname, "Authorization timed out. Would you like to try again?"):
                continue
            return None
            
        # If we get here, user chose to retry after an error
        continue

def show_auto_close_notification(heading, message, duration=5):
    dialog = xbmcgui.DialogProgress()
    dialog.create(heading, message)
    for i in range(duration):
        if dialog.iscanceled():
            break
        xbmc.sleep(1000)  # Sleep for 1 second
    dialog.close()

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
    For thumbnails: 720 > 220 > 64 > 48
    For icons: 48 > 64 > 220 > 720"""
    if is_icon:
        sizes = ['48', '64', '220', '720']
    else:
        sizes = ['720', '220', '64', '48']
    for size in sizes:
        if size in image_urls:
            return image_urls[size]
    return 'DefaultVideo.png'

def handle_playback(mode, args, settings, addon_handle):
    if mode and mode[0] == 'file':
        file_id = args['file_id'][0]
        log(f"Fetching file details with ID: {file_id}")
        
        data = call_api(f'/api/v0.1/p/fs/file/{file_id}', settings['access_token'])
        log(f"File details response: {data}")
        
        if data and not data.get('error'):
            if data.get('is_video', False):
                # Get the video streaming URL
                log("Fetching video streaming URL")
                video_data = call_api(f'/api/v0.1/p/media/fs/item/{file_id}/video/url', settings['access_token'])
                log(f"Video URL response: {video_data}")
                
                if video_data and not video_data.get('error'):
                    url = video_data.get('url')
                    if url:
                        log(f"Playing video URL: {url}")
                        # Create ListItem with all required properties
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
                                thumbnail = get_best_image_url(image_urls, is_icon=False)
                                icon = get_best_image_url(image_urls, is_icon=True)
                                li.setArt({
                                    'icon': icon,
                                    'thumb': thumbnail
                                })
                        
                        # Set required properties for HLS playback
                        li.setProperty('inputstream', 'inputstream.adaptive')
                        li.setProperty('inputstream.adaptive.manifest_type', 'hls')
                        li.setMimeType('application/x-mpegURL')
                        li.setContentLookup(False)
                        
                        # Resolve the URL first
                        xbmcplugin.setResolvedUrl(addon_handle, True, li)
                        return
                    else:
                        # Handle failure case
                        li = xbmcgui.ListItem()
                        xbmcplugin.setResolvedUrl(addon_handle, False, li)
                        log("No video URL returned", xbmc.LOGERROR)
                        show_auto_close_notification(addonname, "Failed to get video URL. Please try again.")
                else:
                    # Handle failure case
                    li = xbmcgui.ListItem()
                    xbmcplugin.setResolvedUrl(addon_handle, False, li)
                    log("Failed to get video URL", xbmc.LOGERROR)
                    show_auto_close_notification(addonname, "Failed to get video URL. Please try again.")
            elif data.get('is_audio', False):
                # Get the audio streaming URL
                log("Fetching audio streaming URL")
                audio_data = call_api(f'/api/v0.1/p/media/fs/item/{file_id}/video/url', settings['access_token'])
                log(f"Audio URL response: {audio_data}")
                
                if audio_data and not audio_data.get('error'):
                    url = audio_data.get('url')
                    if url:
                        log(f"Playing audio URL: {url}")
                        li = xbmcgui.ListItem(path=url)
                        li.setInfo('audio', {'title': data.get('name', 'Unknown Audio')})
                        xbmcplugin.setResolvedUrl(addon_handle, True, li)
                        return
                    else:
                        li = xbmcgui.ListItem()
                        xbmcplugin.setResolvedUrl(addon_handle, False, li)
                        log("No audio URL returned", xbmc.LOGERROR)
                        show_auto_close_notification(addonname, "Failed to get audio URL. Please try again.")
                else:
                    li = xbmcgui.ListItem()
                    xbmcplugin.setResolvedUrl(addon_handle, False, li)
                    log("Failed to get audio URL", xbmc.LOGERROR)
                    show_auto_close_notification(addonname, "Failed to get audio URL. Please try again.")
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
                    
                    # Check if it's a media file or has presentation URLs
                    is_media = f.get('is_video', False) or f.get('is_audio', False)
                    presentation_urls = f.get('presentation_urls', {})
                    has_presentation = isinstance(presentation_urls, dict) and bool(presentation_urls.get('image'))
                    
                    if is_media or has_presentation:
                        file_id = f.get('id')
                        if not file_id:
                            log("Skipping file without ID")
                            continue
                            
                        url = build_url({'mode': 'file', 'file_id': file_id})
                        li = xbmcgui.ListItem(f.get('name', 'Unknown File'))
                        
                        # Add file size if available
                        if f.get('size', 0) > 0:
                            size_str = f" ({f['size'] / (1024*1024):.1f} MB)"
                            li.setLabel(f.get('name', 'Unknown File') + size_str)
                        
                        # Set appropriate icon and info
                        if f.get('is_video', False):
                            li.setInfo('video', infoLabels={'title': f.get('name', 'Unknown Video')})
                            if f.get('presentation_urls', {}).get('image', {}):
                                presentation_urls = f['presentation_urls']
                                image_urls = presentation_urls.get('image', {})
                                if isinstance(image_urls, dict):
                                    thumbnail = get_best_image_url(image_urls, is_icon=False)
                                    icon = get_best_image_url(image_urls, is_icon=True)
                                    li.setArt({
                                        'icon': icon,
                                        'thumb': thumbnail
                                    })
                        elif f.get('is_audio', False):
                            li.setInfo('music', infoLabels={'title': f.get('name', 'Unknown Audio')})
                            li.setArt({
                                'icon': 'DefaultAudio.png',
                                'thumb': 'DefaultAudio.png'
                            })
                        else:
                            # Handle image files
                            li.setInfo('picture', infoLabels={'title': f.get('name', 'Unknown Image')})
                            if f.get('presentation_urls', {}).get('image', {}):
                                presentation_urls = f['presentation_urls']
                                image_urls = presentation_urls.get('image', {})
                                if isinstance(image_urls, dict):
                                    thumbnail = get_best_image_url(image_urls, is_icon=False)
                                    icon = get_best_image_url(image_urls, is_icon=True)
                                    li.setArt({
                                        'icon': icon,
                                        'thumb': thumbnail
                                    })
                            else:
                                li.setArt({
                                    'icon': 'DefaultPicture.png',
                                    'thumb': 'DefaultPicture.png'
                                })

                        li.setProperty('IsPlayable', 'True')
                        li.addContextMenuItems([(__language__(id=32006), 'Container.Refresh'),
                                              (__language__(id=32007), 'Action(ParentDir)')])
                        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)
                except Exception as e:
                    log(f"Error processing file: {str(e)}", xbmc.LOGERROR)
                    continue

    if success:
        xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_FILE)
        xbmcplugin.endOfDirectory(addon_handle)
    else:
        xbmcgui.Dialog().ok(addonname, "Failed to load content. Please try again.")

