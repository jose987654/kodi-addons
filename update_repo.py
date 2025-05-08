#!/usr/bin/env python3
"""
    Repository updater script
    This script will scan the repository directories and generate:
    - addons.xml
    - addons.xml.md5
    - ZIP files for each addon
"""

import os
import sys
import xml.etree.ElementTree as ET
import hashlib
import zipfile
import shutil
from datetime import datetime

def cleanup_pyc_files(addon_dir):
    """Remove *.pyc files to reduce ZIP size"""
    for root, dirs, files in os.walk(addon_dir):
        for filename in files:
            if filename.endswith(".pyc"):
                os.remove(os.path.join(root, filename))

def read_addon_xml(addon_dir):
    """Read the addon.xml file"""
    addon_xml_path = os.path.join(addon_dir, "addon.xml")
    if not os.path.exists(addon_xml_path):
        return None
    
    try:
        tree = ET.parse(addon_xml_path)
        return tree.getroot()
    except Exception as e:
        print(f"Error parsing {addon_xml_path}: {e}")
        return None

def generate_addons_xml():
    """Generate addons.xml from the repository contents"""
    print("Generating addons.xml file")
    addons_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'
    
    # Get all addon directories (excluding hidden and non-directory items)
    addon_dirs = [d for d in os.listdir('.') if os.path.isdir(d) and not d.startswith('.')]
    
    # Filter for valid addon directories (those with addon.xml)
    valid_addon_dirs = []
    for addon_dir in addon_dirs:
        if os.path.exists(os.path.join(addon_dir, "addon.xml")):
            valid_addon_dirs.append(addon_dir)
    
    # Sort the addon directories
    valid_addon_dirs.sort()
    
    # Process each addon
    for addon_dir in valid_addon_dirs:
        addon_xml_root = read_addon_xml(addon_dir)
        if addon_xml_root is not None:
            addon_xml_str = ET.tostring(addon_xml_root, encoding='utf-8').decode('utf-8')
            # Format the XML string
            indent = "    "
            lines = addon_xml_str.split('\n')
            formatted_lines = []
            for line in lines:
                formatted_lines.append(indent + line)
            formatted_xml = '\n'.join(formatted_lines)
            addons_xml += formatted_xml + "\n"
    
    addons_xml += "</addons>\n"
    
    # Write the addons.xml file
    with open("addons.xml", "w", encoding='utf-8') as f:
        f.write(addons_xml)
    print("addons.xml generated successfully")
    
    # Generate MD5 hash
    generate_md5_file("addons.xml")

def generate_md5_file(file_path):
    """Generate MD5 hash for the given file"""
    print(f"Generating MD5 hash for {file_path}")
    md5_hash = hashlib.md5()
    
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    
    with open(f"{file_path}.md5", "w") as f:
        f.write(md5_hash.hexdigest())
    
    print(f"{file_path}.md5 generated successfully")

def create_zipfile(addon_dir):
    """Create ZIP file for the addon"""
    addon_xml_root = read_addon_xml(addon_dir)
    if addon_xml_root is None:
        print(f"Skipping {addon_dir}: No valid addon.xml found")
        return
    
    addon_id = addon_xml_root.get("id")
    addon_version = addon_xml_root.get("version")
    zipfile_name = f"{addon_id}-{addon_version}.zip"
    
    print(f"Creating ZIP file for {addon_id} version {addon_version}")
    
    # Create a temporary directory to store files
    temp_dir = f"{addon_id}_temp"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    # Copy addon files to temp directory
    shutil.copytree(addon_dir, os.path.join(temp_dir, addon_id))
    
    # Remove any .pyc files
    cleanup_pyc_files(os.path.join(temp_dir, addon_id))
    
    # Create ZIP file
    with zipfile.ZipFile(zipfile_name, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zip_path = os.path.relpath(file_path, temp_dir)
                zip_ref.write(file_path, zip_path)
    
    # Clean up temporary directory
    shutil.rmtree(temp_dir)
    print(f"ZIP file created: {zipfile_name}")

def main():
    """Main function"""
    print("Starting repository update process...")
    
    # Generate addons.xml and addons.xml.md5
    generate_addons_xml()
    
    # Create ZIP files for each addon
    addon_dirs = [d for d in os.listdir('.') if os.path.isdir(d) and not d.startswith('.')]
    for addon_dir in addon_dirs:
        if os.path.exists(os.path.join(addon_dir, "addon.xml")):
            create_zipfile(addon_dir)
    
    print("Repository update completed successfully!")

if __name__ == "__main__":
    main() 