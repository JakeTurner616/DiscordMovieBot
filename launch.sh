#!/bin/bash

# Define the path to qBittorrent executable
QB_PATH="/usr/bin/qbittorrent"

# Function to check if qBittorrent is running
check_qbittorrent() {
    echo "Checking if qBittorrent is running..."
    if pgrep -x "qbittorrent" > /dev/null; then
        echo "qBittorrent is running."
    else
        echo "qBittorrent is not running. Starting qBittorrent..."
        nohup "$QB_PATH" &
        sleep 5
        check_qbittorrent
    fi
}

# Start the qBittorrent check
check_qbittorrent

# Activate the virtual environment
echo "Activating the virtual environment and starting the bot..."
source discordmoviebot/bin/activate

# Run the Python bot script
python bot.py
echo "Bot script execution has ended."

# Keep the shell open until user presses a key
read -p "Press any key to continue..." -n1 -s
