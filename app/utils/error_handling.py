import logging
import os
from logging.handlers import RotatingFileHandler
import traceback
from functools import wraps
from flask import flash, redirect, url_for

# Configure logging format
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.INFO
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'app.log')

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(name):
    """
    Set up a logger with file and console handlers
    
    Args:
        name (str): Logger name
        
    Returns:
        logging.Logger: Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    
    # Clear existing handlers
    if logger.handlers:
        logger.handlers = []
    
    # Create file handler with rotation
    file_handler = RotatingFileHandler(
        LOG_FILE, 
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def handle_errors(func):
    """
    Decorator to handle errors in route functions
    
    Args:
        func: The route function to wrap
        
    Returns:
        function: Wrapped function with error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log the error
            logger = logging.getLogger('app.error')
            logger.error(f"Error in {func.__name__}: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Flash error message to user
            flash(f"An error occurred: {str(e)}", "danger")
            
            # Redirect to appropriate page
            if 'source' in func.__name__:
                return redirect(url_for('sources'))
            elif 'keyword' in func.__name__:
                return redirect(url_for('keywords'))
            elif 'match' in func.__name__:
                return redirect(url_for('matches'))
            elif 'setting' in func.__name__:
                return redirect(url_for('settings'))
            else:
                return redirect(url_for('index'))
    
    return wrapper

def log_scraper_activity(source_name, source_type, action, result):
    """
    Log scraper activity
    
    Args:
        source_name (str): Name of the source
        source_type (str): Type of the source (facebook/nextdoor)
        action (str): Action performed
        result (str): Result of the action
    """
    logger = logging.getLogger('app.scraper')
    logger.info(f"{source_type.upper()} - {source_name} - {action} - {result}")

def log_alert_activity(match_id, alert_type, status):
    """
    Log alert activity
    
    Args:
        match_id (int): ID of the match
        alert_type (str): Type of alert (slack/email)
        status (str): Status of the alert
    """
    logger = logging.getLogger('app.alert')
    logger.info(f"Match ID {match_id} - {alert_type.upper()} alert - {status}")

def log_user_activity(action, details):
    """
    Log user activity
    
    Args:
        action (str): Action performed
        details (str): Details of the action
    """
    logger = logging.getLogger('app.user')
    logger.info(f"USER ACTION - {action} - {details}")

def handle_captcha_error(source_name, source_type):
    """
    Handle captcha errors
    
    Args:
        source_name (str): Name of the source
        source_type (str): Type of the source (facebook/nextdoor)
    """
    logger = logging.getLogger('app.error')
    logger.error(f"CAPTCHA detected for {source_type} source: {source_name}")
    
    # Log to a specific captcha error file
    captcha_log = os.path.join(LOG_DIR, 'captcha_errors.log')
    with open(captcha_log, 'a') as f:
        f.write(f"{logging.Formatter(LOG_FORMAT).format(logging.LogRecord('app.error', logging.ERROR, '', 0, f'CAPTCHA detected for {source_type} source: {source_name}', None, None))}\n")

def handle_auth_failure(source_name, source_type, error_details):
    """
    Handle authentication failures
    
    Args:
        source_name (str): Name of the source
        source_type (str): Type of the source (facebook/nextdoor)
        error_details (str): Details of the error
    """
    logger = logging.getLogger('app.error')
    logger.error(f"Authentication failure for {source_type} source: {source_name} - {error_details}")
    
    # Log to a specific auth error file
    auth_log = os.path.join(LOG_DIR, 'auth_errors.log')
    with open(auth_log, 'a') as f:
        f.write(f"{logging.Formatter(LOG_FORMAT).format(logging.LogRecord('app.error', logging.ERROR, '', 0, f'Authentication failure for {source_type} source: {source_name} - {error_details}', None, None))}\n")

# Initialize loggers
app_logger = setup_logger('app')
scraper_logger = setup_logger('app.scraper')
alert_logger = setup_logger('app.alert')
error_logger = setup_logger('app.error')
user_logger = setup_logger('app.user')
