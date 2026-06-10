To ensure the proper functioning of our Forza gamepad assist tool, please install and configure the following software requirements:

vJoy: A driver used to create a virtual game controller, allowing the script to send inputs to the game.

DS4Windows: Required for DualShock gamepad users to emulate an Xbox 360 controller, ensuring proper input recognition.

HidHide: A utility used to hide physical controllers from the system, which prevents "double-input" conflicts between your real and virtual controllers.

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
**Game Pass / Microsoft Store Users:**
The Steam Input configuration step is not required. It exists only to prevent conflicts between Steam and HidHide. 
Instead, add the Microsoft Store version of Forza to HidHide and ensure your physical controller is hidden correctly. 
Also make sure that Forza does not receive any direct gamepad inputs, otherwise double-input issues may occur.

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
