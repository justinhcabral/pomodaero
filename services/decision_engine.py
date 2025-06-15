import time
import logging
from camera_service import capture_image
from sensors import read_tds, read_ph
from fuzzy_logic_controller import compute_fuzzy_commands
from actuator import execute_pump_commands, set_misting_interval
from firebase_sync import sync_data, get_current_stage, run_growth_stage_detection, wait_for_stage_confirmation
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def is_in_target_range(ph_value, ec_value):
    """Check if pH and EC are in normal range."""
    return config.PH_MIN <= ph_value <= config.PH_MAX and config.EC_MIN <= ec_value <= config.EC_MAX

def pump_initial_nutrients():
    """Pump 25mL from each nutrient pump (50mL total, 25s at 1mL/s)."""
    commands = {'pH_up': 0.0, 'pH_down': 0.0, 'nutrients': 25.0, 'water': 0.0}
    logger.info("Pumping initial 25mL from each nutrient pump")
    execute_pump_commands(commands)
    return commands

def calibrate_solution(ph_value, ec_value, max_attempts=5):
    """Run fuzzy logic until pH and EC are in target range or max attempts reached."""
    for attempt in range(max_attempts):
        if is_in_target_range(ph_value, ec_value):
            logger.info(f"Calibration complete: pH {ph_value:.2f}, EC {ec_value:.2f}")
            return True
        commands, _ = compute_fuzzy_commands()
        if any(duration > 0 for duration in commands.values()):
            execute_pump_commands(commands)
            logger.info(f"Calibration attempt {attempt + 1}: {commands}")
        time.sleep(60)  # Wait for solution to stabilize
        tds_data = read_tds()
        ph_data = read_ph()
        ec_value = tds_data['ec'] if isinstance(tds_data, dict) else tds_data
        ph_value = ph_data['ph'] if isinstance(ph_data, dict) else ph_data
    logger.warning(f"Calibration failed after {max_attempts} attempts")
    return False

def run_decision_engine():
    """Main control loop for hydroponic and tomato monitoring system."""
    cycle_duration = 60 * 60 * 8  # 3 times a day (24 hours / 3)
    last_yolo_run = 0
    current_stage = get_current_stage()
    logger.info(f"Starting with stage: {current_stage}")

    while True:
        try:
            start_time = time.time()
            # Read sensors
            tds_data = read_tds()
            ph_data = read_ph()
            ec_value = tds_data['ec'] if isinstance(tds_data, dict) else tds_data
            ph_value = ph_data['ph'] if isinstance(ph_data, dict) else ph_data
            logger.info(f"Sensor Readings - EC: {ec_value:.2f} mS/cm, pH: {ph_value:.2f}")

            # Run YOLO inference once a day
            if time.time() - last_yolo_run >= 60 * 60 * 24:
                capture_image(save_dir=config.TOMATO_IMAGE_PATH.rsplit('/', 1)[0], base_name="snapshot")
                tomato_stage = run_growth_stage_detection()
                tomato_data = {'stage': tomato_stage} if tomato_stage else {'stage': current_stage}
                logger.info(f"Tomato Detection: {tomato_data}")
                last_yolo_run = time.time()
                if tomato_data.get('stage') != current_stage and tomato_data.get('stage') in [2, 3]:
                    sync_data({
                        'stage_change': True,
                        'new_stage': tomato_data['stage'],
                        'image': config.TOMATO_IMAGE_PATH
                    })
                    confirmed_stage = wait_for_stage_confirmation(current_stage)
                    if confirmed_stage == tomato_data['stage']:
                        current_stage = confirmed_stage
                        logger.info(f"Stage transitioned to: {current_stage}")
                        pump_initial_nutrients()
                        calibrate_solution(ph_value, ec_value)

            # Calibrate solution if needed
            if not is_in_target_range(ph_value, ec_value):
                calibrate_solution(ph_value, ec_value)

            # Set misting intervals based on stage (pause during calibration)
            misting_config = config.MISTING_INTERVALS.get(current_stage, {'on_time': 30, 'off_time': 300})
            set_misting_interval('diaphragm_misting', 0, 0)  # Pause misting
            time.sleep(1)  # Ensure misting stops
            set_misting_interval('diaphragm_misting', misting_config['on_time'], misting_config['off_time'])

            elapsed = time.time() - start_time
            time.sleep(max(0, cycle_duration - elapsed))

        except Exception as e:
            logger.error(f"Decision engine error: {e}")
            time.sleep(cycle_duration)