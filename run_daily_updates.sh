#!/bin/bash

# Log file path
LOGFILE="/home/benholding/repos/ds_daily_updates/dailyupdates/logs/daily_updates_$(date +'%Y%m%d').log"

# Navigate to the project directory
cd /home/benholding/repos/ds_daily_updates/dailyupdates || {
    echo "Failed to navigate to project directory" >> "$LOGFILE" 2>&1
    exit 1
}

# Activate the virtual environment
source .venv/bin/activate >> "$LOGFILE" 2>&1 || {
    echo "Failed to activate virtual environment" >> "$LOGFILE" 2>&1
    exit 1
}

# Run the Python script
python lambda_function.py >> "$LOGFILE" 2>&1 || {
    echo "Python script execution failed" >> "$LOGFILE" 2>&1
    exit 1
}

echo "Script executed successfully on $(date)" >> "$LOGFILE"
