# Kodi Addons Repository

This repository contains Kodi addons for enhancing your entertainment experience.

## Quick Downloads

👉 **[DOWNLOAD REPOSITORY.SEEDR-1.0.0.ZIP](repository.seedr/repository.seedr-1.0.0.zip)** - Install this first!  
👉 **[DOWNLOAD PLUGIN.VIDEO.SEEDR-1.0.5.ZIP](plugin.video.seedr/plugin.video.seedr-1.0.5.zip)** - Seedr addon

## Repository Navigation

<pre>
<img src="icons/folder.gif" alt="[DIR]"> <a href="repository.seedr/">repository.seedr/</a>
<img src="icons/folder.gif" alt="[DIR]"> <a href="plugin.video.seedr/">plugin.video.seedr/</a>
<img src="icons/compressed.gif" alt="[ZIP]"> <a href="repository.seedr/repository.seedr-1.0.0.zip">repository.seedr-1.0.0.zip</a>
<img src="icons/compressed.gif" alt="[ZIP]"> <a href="plugin.video.seedr/plugin.video.seedr-1.0.5.zip">plugin.video.seedr-1.0.5.zip</a>
</pre>

## Downloads

### Repository

- [repository.seedr-1.0.0.zip](repository.seedr/repository.seedr-1.0.0.zip) - Repository ZIP file
- [repository.seedr-1.0.0.zip.md5](repository.seedr/repository.seedr-1.0.0.zip.md5) - MD5 Checksum: `c4fca73fff5939decf1ca3651c98c3b5`

### Addon

- [plugin.video.seedr-1.0.5.zip](plugin.video.seedr/plugin.video.seedr-1.0.5.zip) - Seedr Addon ZIP file
- [plugin.video.seedr-1.0.5.zip.md5](plugin.video.seedr/plugin.video.seedr-1.0.5.zip.md5) - MD5 Checksum: `e916deecc28cade4dd6563ec090f615b`

## Available Addons

### Seedr Addon

Stream videos, music, and images from your Seedr cloud storage directly to Kodi.

**Features:**

- Stream video files from your Seedr account
- Listen to audio files
- View image files
- Support for SRT subtitles
- Automatic subtitle matching for videos

**What's New in v1.0.5:**

- Simplified audio playback to most basic form
- Streamlined approach with direct audio playback
- Removed excess code for better reliability

**What's New in v1.0.4:**

- Simplified audio playback for better reliability
- Removed playlist functionality for more stable audio playback
- Retained direct URL playback and InfoTagMusic approach

**What's New in v1.0.3:**

- Enhanced audio playback with improved playlist handling
- Fixed Kodi API deprecation warnings for audio files
- Implemented direct URL playback for audio playlists
- Added fallback to direct download URLs for audio files
- Updated InfoTagMusic approach for newer Kodi versions

**What's New in v1.0.2:**

- Fixed audio playback issues with direct files
- Improved audio playlist handling
- Better handling of audio formats
- Fixed issue with audio files not playing via plugin URL

## Installation

### Repository Installation

1. Download the repository zip file ([repository.seedr-1.0.0.zip](repository.seedr/repository.seedr-1.0.0.zip))
2. In Kodi, go to Add-ons > Install from zip file
3. Select the downloaded zip file
4. The repository will be installed

### Addon Installation

Once the repository is installed:

1. Go to Add-ons > Install from repository
2. Select the "Seedr Repository"
3. Navigate to the addon you want to install
4. Click "Install"

## Building the Repository

To build/update the repository:

1. Make changes to the addons
2. Update version numbers in the respective addon.xml files
3. Run the `update_repo.py` script to update addons.xml and MD5 files
4. Commit and push changes to GitHub

## License

This project is licensed under the GPL-3.0 License - see the LICENSE file for details.
