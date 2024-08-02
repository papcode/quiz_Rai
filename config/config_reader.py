import configparser
import os

def load_config():
    # Define the path to the config file inside the config directory
    config_file = os.path.join(os.path.dirname(__file__), 'config.ini')
    
    # Initialize the ConfigParser
    config = configparser.ConfigParser()
    
    # Check if the configuration file exists
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"The configuration file {config_file} does not exist.")
    
    # Read the configuration file
    config.read(config_file)
    
    # Verify the necessary sections and options
    if 'mongodb' not in config:
        raise KeyError("The 'mongodb' section is missing in the configuration file.")
    if 'flask' not in config:
        raise KeyError("The 'flask' section is missing in the configuration file.")
    if 'email' not in config:
        raise KeyError("The 'email' section is missing in the configuration file.")
    
    # Extract configuration values
    mongo_uri = config.get('mongodb', 'MONGO_URI', fallback='')
    database_name = config.get('mongodb', 'DATABASE_NAME', fallback='')
    collection_name = config.get('mongodb', 'COLLECTION_NAME', fallback='')
    secret_key = config.get('flask', 'SECRET_KEY', fallback='')
    mail_server = config.get('email', 'MAIL_SERVER', fallback='')
    mail_port = config.getint('email', 'MAIL_PORT', fallback=587)
    mail_username = config.get('email', 'MAIL_USERNAME', fallback='')
    mail_password = config.get('email', 'MAIL_PASSWORD', fallback='')
    mail_use_tls = config.getboolean('email', 'MAIL_USE_TLS', fallback=True)
    mail_use_ssl = config.getboolean('email', 'MAIL_USE_SSL', fallback=False)
    mail_default_sender = config.get('email', 'MAIL_DEFAULT_SENDER', fallback='')

    # Check if any required values are missing
    if not mongo_uri or not database_name or not collection_name:
        raise ValueError("One or more required database configuration values are missing.")
    
    return {
        'MONGO_URI': mongo_uri,
        'DATABASE_NAME': database_name,
        'COLLECTION_NAME': collection_name,
        'SECRET_KEY': secret_key,
        'MAIL_SERVER': mail_server,
        'MAIL_PORT': mail_port,
        'MAIL_USERNAME': mail_username,
        'MAIL_PASSWORD': mail_password,
        'MAIL_USE_TLS': mail_use_tls,
        'MAIL_USE_SSL': mail_use_ssl,
        'MAIL_DEFAULT_SENDER': mail_default_sender
    }
