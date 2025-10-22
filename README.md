# Seedr Kodi Repository

A Kodi addon that allows you to access and stream your Seedr.cc cloud storage content directly through Kodi.

This repository contains Kodi addons for enhancing your entertainment experience.

## What is Kodi?

Kodi is a free and open-source media player software application developed by the XBMC Foundation. It's a powerful entertainment hub that allows you to:

- Play and view most videos, music, podcasts, and other digital media files
- Organize and manage your media library
- Stream content from the internet
- Customize your experience with addons and skins
- Run on multiple platforms including Windows, macOS, Linux, Android, and iOS

Kodi is particularly popular among home theater enthusiasts and cord-cutters as it provides a unified interface for accessing various media sources, including local storage, network drives, and online services like Seedr.cc.

## Requirements

- Kodi media center
- Seedr.cc account
- Internet connection

## Available Addons

### Seedr Addon

Stream videos, music, and images from your Seedr cloud storage directly to Kodi.

**Features:**

- Stream video files from your Seedr account
- Listen to audio files
- View image files
- Support for SRT subtitles
- Automatic subtitle matching for videos

## Installation

## First-time Setup

1. Launch the addon from Kodi
2. You will be presented with a verification URL and code
3. Visit the provided URL in your web browser
4. Enter the verification code
5. The addon will automatically complete the authentication process
6. Authorize the application to access the files.

### Repository Installation

## Method 1: Direct Download and Install

1. Download the plugin.video zip file ([plugin.video.seedr-1.2.0.zip](plugin.video.seedr-1.2.0.zip))
2. In Kodi, go to Add-ons > Install from zip file
3. Select the downloaded zip file
4. The addon will be installed directly

**Note:** If you have issues with paths containing spaces, copy the ZIP file to a simple path like `D:\kodi-addons-install\` before installing.

## Method 2: Install Repository First, Then Addon

1. Download the repository zip file ([repository.seedr-1.0.2.zip](repository.seedr-1.0.2.zip))
2. In Kodi, go to Add-ons > Install from zip file
3. Select the downloaded repository.seedr-1.0.2.zip
4. Wait for the "Add-on installed" notification
5. Go to Add-ons > Install from repository
6. Select "Seedr Repository"
7. Navigate to Video Add-ons
8. Select and install the Seedr addon

## Method 3: Install via File Source (Online)

1. In Kodi, go to Settings > File Manager
2. Select "Add source"
3. Enter `https://jose987654.github.io/kodi-addons/` as the path
4. Name it "Seedr Repository" (or any name you prefer)
5. Go to Add-ons > Install from zip file
6. Select "Seedr Repository" (or the name you chose)
7. Select repository.seedr-1.0.2.zip
8. Wait for the "Add-on installed" notification
9. Go to Add-ons > Install from repository
10. Select "Seedr Repository"
11. Navigate to Video Add-ons
12. Select and install the Seedr addon

### Addon Installation

Once the repository is installed:

1. Go to Add-ons > Install from repository
2. Select the "Seedr Repository"
3. Navigate to the addon you want to install
4. Click "Install"

## Quick Downloads

👉 **[DOWNLOAD REPOSITORY.SEEDR-1.0.2.ZIP](repository.seedr-1.0.2.zip)** - Install this first!  
👉 **[DOWNLOAD PLUGIN.VIDEO.SEEDR-1.2.0.ZIP](plugin.video.seedr-1.2.0.zip)** - Seedr addon

## Repository Navigation

<pre>
<img src="icons/folder.gif" alt="[DIR]"> <a href="repository.seedr/">repository.seedr/</a>
<img src="icons/folder.gif" alt="[DIR]"> <a href="plugin.video.seedr/">plugin.video.seedr/</a>

</pre>

## Downloads

### Repository

- [repository.seedr-1.0.2.zip](repository.seedr-1.0.2.zip) - Repository ZIP file

### Addon

- [plugin.video.seedr-1.2.0.zip](plugin.video.seedr-1.2.0.zip) - Seedr Addon ZIP file

## Usage

- Navigate through your Seedr.cc folders using the Kodi interface
- Video files will be automatically playable
- Audio files will be available for streaming
- Use the context menu to refresh the current view or go back to parent directory

## Technical Details

The addon uses the Seedr.cc API to:

- Authenticate users through device code flow
- List folders and files
- Stream media content
- Display thumbnails and metadata

## Development Dependencies

- Python 2.7 or 3.x
- Kodi addon development environment with Python API (`xbmc`, `xbmcaddon`, `xbmcgui`, `xbmcplugin`)
- `script.module.routing` (Kodi addon dependency)

## Building the Repository

To build/update the repository:

1. Make changes to the addons
2. Update version numbers in the respective addon.xml files
3. Run the `update_repo.py` script to update addons.xml and MD5 files
4. Commit and push changes to GitHub

**What's New in v1.2.0:**

- Fixed critical indentation errors in main.py
- Improved code stability and reliability
- Better error handling for authentication flow
- Enhanced compatibility with Kodi installation process
- Resolved Python syntax errors preventing addon from loading

**What's New in v1.1.1:**

- Updated to standard semantic versioning
- Updated fanart images with new Seedr design
- Improved audio playlist support
- Enhanced user interface

**What's New in v1.0.6:**

- Simplified audio playback with InfoTagMusic
- Direct media API for reliable audio streaming
- Combined best approaches from previous versions

**What's New in v1.0.5:**

- Simplified audio playback to most basic form
- Streamlined approach with direct audio playback
- Removed excess code for better reliability

## Support

For issues or questions, please check the project's issue tracker or contact the maintainers.

## License

This project is licensed under the [GPL-3.0 License](LICENSE).
