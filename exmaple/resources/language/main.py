# This code should be placed AFTER all import statements in your main.py file
# Place it somewhere after the imports but before show_qr_authentication_dialog function
# For example, right after the create_qr_code function definition

class SimpleQRDialog(xbmcgui.WindowDialog):
    """Simplified dialog window that displays QR code with authentication instructions"""
    
    def __init__(self, qr_image_path, verification_url, user_code):
        super(SimpleQRDialog, self).__init__()
        self.qr_image_path = qr_image_path
        self.verification_url = verification_url
        self.user_code = user_code
        
        # Get screen dimensions (default to 720p if not available)
        try:
            self.screen_width = self.getWidth() or 1280
            self.screen_height = self.getHeight() or 720
        except:
            self.screen_width = 1280
            self.screen_height = 720
        
        # Dialog dimensions
        self.dialog_width = 600
        self.dialog_height = 550
        
        # Calculate center position
        self.x = (self.screen_width - self.dialog_width) // 2
        self.y = (self.screen_height - self.dialog_height) // 2
        
        # Create a semi-transparent black background
        # Using a solid color control instead of image
        try:
            self.background = xbmcgui.ControlImage(
                self.x - 10, self.y - 10,
                self.dialog_width + 20, self.dialog_height + 20,
                ''  # Empty path
            )
            self.background.setColorDiffuse('0xDD000000')  # Semi-transparent black
            self.addControl(self.background)
        except:
            # If ControlImage fails without path, skip background
            pass
        
        # Add title
        self.title = xbmcgui.ControlTextBox(
            self.x + 20, self.y + 20,
            self.dialog_width - 40, 40
        )
        self.addControl(self.title)
        self.title.setText('[B][COLOR cyan]Seedr Authentication[/COLOR][/B]')
        
        # Add QR code image if available
        if qr_image_path and os.path.exists(qr_image_path):
            qr_size = 220
            qr_x = self.x + (self.dialog_width - qr_size) // 2
            qr_y = self.y + 70
            
            self.qr_image = xbmcgui.ControlImage(
                qr_x, qr_y,
                qr_size, qr_size,
                qr_image_path
            )
            self.addControl(self.qr_image)
            
            # Add instructions below QR code
            instructions_y = qr_y + qr_size + 20
        else:
            # If no QR code, start instructions higher
            instructions_y = self.y + 100
        
        # Add instruction text box
        self.instructions = xbmcgui.ControlTextBox(
            self.x + 20, instructions_y,
            self.dialog_width - 40, 200
        )
        self.addControl(self.instructions)
        
        # Build instruction text
        instruction_text = (
            '[COLOR lightblue]OPTION 1: Scan the QR code above[/COLOR]\n\n'
            '[COLOR lightblue]OPTION 2: Manual entry:[/COLOR]\n'
            f'Visit: {self.verification_url}\n\n'
            f'[COLOR yellow]User Code: {self.user_code}[/COLOR]\n\n'
            '[COLOR white]Press OK or Back when done[/COLOR]'
        )
        self.instructions.setText(instruction_text)
        
        # Add OK button
        button_width = 80
        button_height = 35
        button_x = self.x + (self.dialog_width - button_width) // 2
        button_y = self.y + self.dialog_height - button_height - 20
        
        self.ok_button = xbmcgui.ControlButton(
            button_x, button_y,
            button_width, button_height,
            'OK',
            textColor='0xFFFFFFFF',
            focusedColor='0xFF00FFFF',
            font='font12'
        )
        self.addControl(self.ok_button)
        
        # Set focus on OK button
        self.setFocus(self.ok_button)
        
    def onAction(self, action):
        # Handle ESC/Back button
        if action.getId() in (xbmcgui.ACTION_NAV_BACK, 
                             xbmcgui.ACTION_PREVIOUS_MENU,
                             xbmcgui.ACTION_SELECT_ITEM):
            self.close()
            
    def onControl(self, control):
        # Handle OK button click
        if control == self.ok_button:
            self.close()


def show_qr_authentication_dialog(verification_url, user_code):
    """Show dialog with QR code embedded inside the dialog box"""
    try:
        # Create temporary file path for QR image
        temp_dir = xbmcvfs.translatePath('special://temp/')
        qr_image_path = os.path.join(temp_dir, 'seedr_qr_code.png')
        
        # Generate QR code using external service
        log("Generating QR code for embedded authentication dialog")
        qr_image_loaded = create_qr_code(verification_url, qr_image_path, 220)  # Size for dialog
        
        if qr_image_loaded and os.path.exists(qr_image_path):
            log("Showing custom dialog with embedded QR code")
            # Create and show the custom dialog with embedded QR code
            dialog = SimpleQRDialog(qr_image_path, verification_url, user_code)
            dialog.doModal()
            del dialog
            log("Custom QR dialog closed")
        else:
            # Fallback to text-only standard dialog if QR generation fails
            log("QR code generation failed, showing standard text dialog", xbmc.LOGWARNING)
            message = (
                "To use this Addon, Please Authorize Seedr at:\n\n"
                f"{verification_url}\n\n"
                f"User Code: {user_code}"
            )
            xbmcgui.Dialog().ok("Seedr Authentication", message)
        
        # Clean up temporary file
        if os.path.exists(qr_image_path):
            try:
                os.remove(qr_image_path)
                log("Cleaned up temporary QR image file")
            except Exception as e:
                log(f"Error cleaning up QR image file: {str(e)}", xbmc.LOGWARNING)
        
        return True
        
    except Exception as e:
        log(f"Error showing QR authentication dialog: {str(e)}", xbmc.LOGERROR)
        # Fallback to simple standard dialog
        message = (
            "To use this Addon, Please Authorize Seedr at:\n\n"
            f"{verification_url}\n\n"
            f"User Code: {user_code}"
        )
        xbmcgui.Dialog().ok("Seedr Authentication", message)
        return False