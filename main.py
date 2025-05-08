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
                # Get the video streaming URL
                log("Fetching video streaming URL")
                video_data = call_api(f'/api/v0.1/p/media/fs/item/{file_id}/video/url', settings['access_token'])
                log(f"Video URL response: {video_data}")
                
                if video_data and not video_data.get('error'):
                    url = video_data.get('url')
                    if url:
                        log(f"Playing video URL: {url}")
                        
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
                        li.setProperty('inputstream', 'inputstream.adaptive')
                        li.setProperty('inputstream.adaptive.manifest_type', 'hls')
                        li.setMimeType('application/x-mpegURL')
                        li.setContentLookup(False)
                        
                        # Add subtitle if found
                        if subtitle_url:
                            log(f"Adding subtitle to video: {subtitle_url}", xbmc.LOGINFO)
                            li.setSubtitles([subtitle_url])
                        
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
                        
                        # Get folder data to find other audio files for playlist
                        folder_id = data.get('folder_id')
                        
                        # Create a playlist for audio files
                        playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
                        playlist.clear()  # Clear any existing playlist
                        
                        # Add the current file to the playlist first
                        current_li = xbmcgui.ListItem(path=url)
                        current_li.setInfo('music', {'title': data.get('name', 'Unknown Audio')})
                        current_li.setArt({
                            'icon': 'DefaultAudio.png',
                            'thumb': 'DefaultAudio.png'
                        })
                        playlist.add(url, current_li)
                        
                        # If we have a folder ID, get all audio files in the folder
                        if folder_id:
                            log(f"Getting all audio files from folder ID: {folder_id}", xbmc.LOGINFO)
                            folder_data = call_api(f'/api/v0.1/p/fs/folder/{folder_id}/contents', settings['access_token'])
                            
                            if folder_data and 'files' in folder_data:
                                # Sort the files by name
                                folder_files = sorted(folder_data['files'], key=lambda x: x.get('name', ''))
                                
                                # Find the index of the current file to adjust playlist order
                                current_index = -1
                                for i, file_item in enumerate(folder_files):
                                    if file_item.get('id') == int(file_id):
                                        current_index = i
                                        break
                                
                                # Process all audio files in the folder
                                added_files = 0
                                
                                # First add files after the current one
                                for i in range(current_index + 1, len(folder_files)):
                                    file_item = folder_files[i]
                                    if file_item.get('is_audio', False):
                                        # For each audio file, get the stream URL and add to playlist
                                        next_file_id = file_item.get('id')
                                        next_name = file_item.get('name', 'Unknown Audio')
                                        
                                        log(f"Adding next audio file to playlist: {next_name}", xbmc.LOGINFO)
                                        
                                        # Get streaming URL for this file
                                        next_audio_data = call_api(f'/api/v0.1/p/media/fs/item/{next_file_id}/video/url', settings['access_token'])
                                        if next_audio_data and 'url' in next_audio_data:
                                            next_url = next_audio_data['url']
                                            next_li = xbmcgui.ListItem(next_name)
                                            next_li.setInfo('music', {'title': next_name})
                                            next_li.setArt({
                                                'icon': 'DefaultAudio.png',
                                                'thumb': 'DefaultAudio.png'
                                            })
                                            playlist.add(next_url, next_li)
                                            added_files += 1
                                
                                # Then add files before the current one (to loop back)
                                for i in range(0, current_index):
                                    file_item = folder_files[i]
                                    if file_item.get('is_audio', False):
                                        # For each audio file, get the stream URL and add to playlist
                                        next_file_id = file_item.get('id')
                                        next_name = file_item.get('name', 'Unknown Audio')
                                        
                                        log(f"Adding previous audio file to playlist: {next_name}", xbmc.LOGINFO)
                                        
                                        # Get streaming URL for this file
                                        next_audio_data = call_api(f'/api/v0.1/p/media/fs/item/{next_file_id}/video/url', settings['access_token'])
                                        if next_audio_data and 'url' in next_audio_data:
                                            next_url = next_audio_data['url']
                                            next_li = xbmcgui.ListItem(next_name)
                                            next_li.setInfo('music', {'title': next_name})
                                            next_li.setArt({
                                                'icon': 'DefaultAudio.png',
                                                'thumb': 'DefaultAudio.png'
                                            })
                                            playlist.add(next_url, next_li)
                                            added_files += 1
                                
                                log(f"Added {added_files} audio files to playlist", xbmc.LOGINFO)
                        
                        # Start playing the playlist from the first item (current file)
                        log("Starting playlist playback", xbmc.LOGINFO)
                        xbmc.Player().play(playlist)
                        return
                    else:
                        li = xbmcgui.ListItem()
                        xbmcplugin.setResolvedUrl(addon_handle, False, li)
                        log("No audio URL returned", xbmc.LOGERROR)
                        show_auto_close_notification(addonname, "Failed to get audio URL. Please try again.")
                else:
                    li = xbmcgui.ListItem()
                    xbmcplugin.setResolvedUrl(addon_handle, False, li)
                    # log("Failed to get audio URL", xbmc.LOGERROR)
                    show_auto_close_notification(addonname, "Failed to get audio URL. Please try again.")
            else:
                # Handle image files - directly use ShowPicture
                log("Handling image file", xbmc.LOGINFO)
                log(f"File ID: {file_id}", xbmc.LOGINFO)
                log(f"File name: {data.get('name', 'Unknown')}", xbmc.LOGINFO)
                
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
                    
                    if is_image:
                        log(f"File is an image: {file_name}", xbmc.LOGINFO)
                    elif is_video:
                        log(f"File is a video: {file_name}", xbmc.LOGINFO)
                    elif is_audio:
                        log(f"File is audio: {file_name}", xbmc.LOGINFO)
                    elif is_subtitle:
                        log(f"File is a subtitle: {file_name}", xbmc.LOGINFO)
                    
                    # Check for presentation URLs
                    presentation_urls = f.get('presentation_urls', {})
                    has_presentation = isinstance(presentation_urls, dict) and 'image' in presentation_urls
                    has_thumb = 'thumb' in f and f['thumb']
                    
                    if has_presentation:
                        log(f"File has presentation URLs: {file_name}", xbmc.LOGINFO)
                    if has_thumb:
                        log(f"File has thumb URL: {file_name}", xbmc.LOGINFO)
                    
                    if is_video or is_audio or is_image or has_presentation or has_thumb or is_subtitle:
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

