import os
import sys
import gazu
import partd
import pymongo

self = sys.modules[__name__]

def get_consistent_name(name):
    """Converts potentially inconsistent names."""
    return name.replace(" ", "_").lower()

def get_project_data(project_id):
    # Lookup the Zou Id and Avalon Id key value pair of the asset

    # Set the directory where partd stores it's data
    directory = os.environ["PARTD_PATH"]
    directory = os.path.join(directory, "data", project_id)

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

def set_project_data(gazu_project_id, avalon_project_id, avalon_collection):
    # Lookup the Zou Id and Avalon Id key value pair of the asset

    # Set the directory where partd stores it's data
    directory = os.environ["PARTD_PATH"]
    directory = os.path.join(directory, "data", gazu_project_id)

    # Create the data directory for the project if it doesn't exist.
    if not os.path.exists(directory):
        os.mkdir(directory)

    # Init partd
    p = partd.Pickle(partd.File(directory))

    # Check if the project set is already stored and delete it if it is.
    # (We're making the assumption that IDs supplied to us are unique).
    if p.get(gazu_project_id):
        p.delete(gazu_project_id)
        print("Removing old project info for: {0}".format(gazu_project_id))
          
    # Encode and store the data as a utf-8 bytes
    value = [avalon_project_id, avalon_collection]
    key_values = {gazu_project_id: value}
    p.append(key_values)
    print("Adding new project info for: {0}".format(gazu_project_id))

def set_asset_data(gazu_project_id, gazu_asset_id, avalon_asset_id):
    # Store Zou Id and Avalon Id key value pair of the asset
            
    # Set the directory where partd stores it's data
    directory = os.environ["PARTD_PATH"]
    directory = os.path.join(directory, "data", gazu_project_id)

    # Create the data directory for the project if it doesn't exist.
    if not os.path.exists(directory):
        os.mkdir(directory)

    # Init partd
    p = partd.File(directory)

    # Check if the asset is already stored and delete it if it is.
    # (We're making the assumption that IDs supplied to us are unique).
    if p.get(gazu_asset_id):
        p.delete(gazu_asset_id)
        print("Deleting: {0}".format(gazu_asset_id))
    
    # Encode and store the data as a utf-8 bytes
    value = bytes(str(avalon_asset_id), "utf-8")
    key_values = {gazu_asset_id: value}
    p.append(key_values)


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
