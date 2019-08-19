import os
import sys
import gazu
import partd
import pymongo
import logging

self = sys.modules[__name__]

def init_logging(script_name):
    global logger
    base_directory = os.environ["DATA_PATH"]
    logs_directory = os.path.join(base_directory, "logs")

    # Create the logs directory for the project if it doesn't exist.
    if not os.path.exists(logs_directory):
        os.mkdir(logs_directory)

    log_level = os.environ["LOG_LEVEL"].upper()
    log_handler = logging.FileHandler("{0}/{1}.log".format(logs_directory, script_name))
    
    formatter = logging.Formatter('{asctime} - {levelname} - {message}', style="{")
    log_handler.setFormatter(formatter)

    logger = logging.getLogger("avalon_sync")
    logger.setLevel(log_level)

    logger.addHandler(log_handler)

    return logger
    
def get_consistent_name(name):
    """Converts potentially inconsistent names."""
    return name.replace(" ", "_").lower()

def set_project_data(gazu_project_id, avalon_project_id, avalon_collection):
    # Lookup the Zou Id and Avalon Id key value pair of the asset

    # Set the directory where partd stores it's data
    base_directory = os.environ["DATA_PATH"]
    data_directory = os.path.join(base_directory, "data")
    directory = os.path.join(data_directory, gazu_project_id)

    # Create the data directory for the project if it doesn't exist.
    if not os.path.exists(directory):
        if not os.path.exists(data_directory):
            os.mkdir(data_directory)
        os.mkdir(directory)

    # Init partd
    p = partd.Pickle(partd.File(directory))

    # Check if the project set is already stored and delete it if it is.
    # (We're making the assumption that IDs supplied to us are unique).
    if p.get(gazu_project_id):
        p.delete(gazu_project_id)
        logger.info("Removing old project info for: {0}".format(avalon_collection))
          
    # Encode and store the data as a utf-8 bytes
    value = [avalon_project_id, avalon_collection]
    key_values = {gazu_project_id: value}
    p.append(key_values)
    logger.info("Adding new project info for: {0}".format(avalon_collection))

def get_project_data(project_id):
    # Lookup the Zou Id and Avalon Id key value pair of the asset

    # Set the directory where partd stores it's data
    directory = os.path.join(os.environ["DATA_PATH"], "data", project_id)

    # Init partd
    p = partd.Pickle(partd.File(directory))

    if not p.get(project_id):
        return False
    else:
        # Get the Avalon asset ID from partd
        project_info = p.get(project_id)
        project_data = {
            "id": project_info[0],
            "collection": project_info[1]
        }
        return project_data

def set_asset_data(gazu_project_id, gazu_asset_id, avalon_asset_id):
    # Store Zou Id and Avalon Id key value pair of the asset
            
    # Set the directory where partd stores it's data
    base_directory = os.environ["DATA_PATH"]
    data_directory = os.path.join(base_directory, "data")
    directory = os.path.join(data_directory, gazu_project_id)

    # Create the data directory for the project if it doesn't exist.
    if not os.path.exists(directory):
        if not os.path.exists(data_directory):
            os.mkdir(data_directory)
        os.mkdir(directory)

    # Init partd
    p = partd.File(directory)

    # Check if the asset is already stored and delete it if it is.
    # (We're making the assumption that IDs supplied to us are unique).
    if p.get(gazu_asset_id):
        p.delete(gazu_asset_id)
        logger.info("Deleting: {0}".format(gazu_asset_id))
    
    # Encode and store the data as a utf-8 bytes
    value = bytes(str(avalon_asset_id), "utf-8")
    key_values = {gazu_asset_id: value}
    p.append(key_values)

def get_asset_data(gazu_project_id, gazu_asset_id):
    # Lookup the Zou Id and Avalon Id key value pair of the asset

    # Set the directory where partd stores it's data
    base_directory = os.environ["DATA_PATH"]
    directory = os.path.join(base_directory, "data", gazu_project_id)

    # Init partd
    p = partd.File(directory)
    
    if not p.get(gazu_asset_id):
        return False
    else:
        # Get the Avalon asset ID from partd
        project_data = bytes.decode(p.get(gazu_asset_id), "utf-8")
        return project_data


def collection_rename(*args, **kwargs):
    """Rename mongodb collection name.
    
    Renames the current collection to the supplied name."""
    timeout = os.getenv("MONGO_TIMEOUT", 5000) 
    mongo = os.environ["AVALON_MONGO"]
    database = os.environ["AVALON_DB"]

    self._mongo_client = pymongo.MongoClient(mongo, serverSelectionTimeoutMS=timeout)
    self._database = self._mongo_client[database]
    self._database[os.environ["AVALON_PROJECT"]].rename(
        *args, **kwargs)
