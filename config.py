# Configuration settings for the hydroponic system
PH_MIN = 5.8
PH_MAX = 6.2
EC_MIN = 2.0
EC_MAX = 2.3
PH_DEFAULT = 6.0
EC_DEFAULT = 1.8
TOMATO_IMAGE_PATH = "/home/cabs/Thesis/raspberrypi-app/data/images/snapshot/snapshot_latest.jpg"
PAUSE_DURATION = 600  # Seconds to pause when in target range
MISTING_INTERVALS = {
    1: {'on_time': 3, 'off_time': 300},  # Stage 1: 30s on, 5min off
    2: {'on_time': 3, 'off_time': 240},  # Stage 2: 45s on, 4min off
    3: {'on_time': 3, 'off_time': 180}   # Stage 3: 60s on, 3min off
}