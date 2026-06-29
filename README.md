Microsoft Store / Game Pass Version

The Microsoft Store / Game Pass version is now partially supported.

Option 1 - HidHide (Experimental)

Some users have reported that HidHide can work with the Microsoft Store version by adding GameLaunchHelper.exe to the HidHide application allowlist instead of the Forza executable.
Note: This method is community-discovered and has not been thoroughly tested. Results may vary.

Option 2 - Special K (Recommended)

If HidHide does not work, you can use Special K instead.
Launch Forza through Special K.
Open the Special K overlay.
Go to Input Management → Gamepad.
Disable Controller Slot 0.
Enable Controller Slot 1.

This prevents Forza from reading your physical controller while still allowing the assist tool to function correctly.

To ensure the proper functioning of our Forza gamepad assist tool, please install and configure the following software requirements:

vJoy: A driver used to create a virtual game controller, allowing the script to send inputs to the game.

HidHide: A utility used to hide physical controllers from the system, which prevents "double-input" conflicts between your real and virtual controllers.

DS4Windows: Required for DualShock gamepad users to emulate an Xbox 360 controller, ensuring proper input recognition.

Setup Instructions for Forza Gamepad Assist
Please follow these steps to configure your environment:

DualShock Users: Configure DS4Windows to emulate an Xbox 360 controller.

#1 Install vJoy: Download and install the latest version of vJoy.

#2 vJoy Configuration:
Open "Configure vJoy".
Select "Device 1".
Enable all checkboxes (axes) and set the Number of buttons to 14.
Important: Restart your computer after configuring vJoy to ensure the changes take effect.

#3 Hide Controllers: Configure HidHide and Steam Input settings as shown in the provided screenshots to prevent double-input issues.

#4 In-Game Settings: Launch Forza, navigate to the Controls menu, and configure your gamepad settings within the Steering Wheel tab.

#5 Telemetry Setup: For the assist script to function, configure the telemetry settings in the game's options as follows:
IP Address: 127.0.0.1
Port: 20777

Known Limitation:
Because the assist tool emulates a steering wheel, you may lose the ability to control certain menu elements or move the camera with the right stick while driving. 
This is a limitation of wheel emulation and not a bug in the assist tool.

![Image alt](https://github.com/kimonowka/forza-assist/blob/main/0.jpg)
![Image alt](https://github.com/kimonowka/forza-assist/blob/main/1.jpg)
![Image alt](https://github.com/kimonowka/forza-assist/blob/main/2.jpg)
![Image alt](https://github.com/kimonowka/forza-assist/blob/main/3.jpg)
![Image alt](https://github.com/kimonowka/forza-assist/blob/main/4.jpg)
![Image alt](https://github.com/kimonowka/forza-assist/blob/main/5.jpg)
