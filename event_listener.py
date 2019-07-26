import os
import gazu
import partd

from avalon import io as avalon
import lib as lib


os.environ["AVALON_PROJECT"] = "temp"
os.environ["AVALON_ASSET"] = "bruce"
os.environ["AVALON_SILO"] = "assets"

def asset_create_callback(data):
    """
    On receiving a entity:new event, insert the asset into the 
    Avalon mongodb and store Zou id and Avalon id key value pair 
    for using in asset update events.
    """

    # Log in to API
    gazu.client.set_host("{0}/api".format(os.environ["GAZU_URL"]))
    gazu.log_in(os.environ["GAZU_USER"], os.environ["GAZU_PASSWD"])
    
    asset = gazu.asset.get_asset(data["asset_id"])
    project = gazu.project.get_project(asset["project_id"])

    project_name = lib.get_consistent_name(project["name"])

    os.environ["AVALON_PROJECT"] = project_name

    avalon.uninstall()
    avalon.install()

    entity_type = gazu.entity.get_entity_type(asset["entity_type_id"])
    asset_data = {
        "schema": "avalon-core:asset-2.0",
        "name": lib.get_consistent_name(asset["name"]),
        "silo": "assets",
        "type": "asset",
        "parent": avalon.locate([project_name]),
        "data": {
            "label": asset.get("label", asset["name"]),
            "group": entity_type["name"]
        }
    }

    # Inset asset into Avalon DB
    avalon.insert_one(asset_data)


    # Store Zou Id and Avalon Id key value pair of the asset

    # Set the directory where partd stores it's data
    directory = os.environ["PARTD_PATH"]
    directory = os.path.join(directory, "data", project["id"])

    # Create the data directory for the project if it doesn't exist.
    if not os.path.exists(directory):
        os.mkdir(directory)

    # Init partd
    p = partd.File(directory)

    # Check if the asset is already stored and delete it if it is.
    # (We're making the assumption that IDs supplied to us are unique).
    if p.get(data["asset_id"]):
        p.delete(data["asset_id"])

    # Find the asset in Avalon
    avalon_asset = avalon.find_one(
        {"name": lib.get_consistent_name(asset["name"]),
        "type": "asset"})

    # Encode and store the data as a utf-8 bytes
    value = bytes(str(avalon_asset["_id"]), "utf-8")
    key_values = {data["asset_id"]: value}
    p.append(key_values)

    avalon.uninstall()

    print("Create Asset \"{0}\" in Project \"{1} ({2})\"".format(asset["name"], 
        project["name"], project["code"]))

def asset_update_callback(data):
    """Update an asset name when receiving an entity:update event"""
    # Log in to API
    gazu.client.set_host("{0}/api".format(os.environ["GAZU_URL"]))
    gazu.log_in(os.environ["GAZU_USER"], os.environ["GAZU_PASSWD"])
    
    asset = gazu.asset.get_asset(data["asset_id"])
    project = gazu.project.get_project(asset["project_id"])

    os.environ["AVALON_PROJECT"] = get_consistent_name(project["name"])

    avalon.uninstall()
    avalon.install()

    # Get Avalon Asset Id.
    asset_id = lib.get_asset_data(project["id"], data["asset_id"])

    # Find the asset in Avalon
    avalon_asset = avalon.find_one(
        {"_id": avalon.ObjectId(asset_id),
        "type": "asset"})

    print(avalon_asset)

    #avalon.replace_once(
    #    {"_id": avalon.ObjectId(asset_id),
    #    "type": "asset"}, )
    #)

def project_new_callback(data):
    """
    On receiving a project:new event, insert the project into the 
    Avalon mongodb and store Zou id and Avalon id key value pair for 
    using in asset update events.
    """

    # Log in to API
    gazu.client.set_host("{0}/api".format(os.environ["GAZU_URL"]))
    gazu.log_in(os.environ["GAZU_USER"], os.environ["GAZU_PASSWD"])
    
    project = gazu.project.get_project(data["project_id"])

    # Ensure project["name"] consistency.
    project_name = lib.get_consistent_name(project["name"])
    
    os.environ["AVALON_PROJECT"] = project_name

    avalon.uninstall()
    avalon.install()

    # Newly created projects don't have a resolution set
    if project["resolution"]:
        resolution_width = int(int(project["resolution"]) / 9 * 16)
    else:
        resolution_width = None
        project["resolution"] = None
    # Get tasks from Gazu API
    tasks = [{"name": lib.get_consistent_name(task["name"]), 
        "label":task["name"]} for task in gazu.task.all_task_types()]

    project_data = {
        "schema": "avalon-core:project-2.0",
        "name": project_name,
        "type": "project",
        "parent": None,
        "data": {
            "label": project["name"],
            "fps":  project["fps"],
            "resolution_width": resolution_width,
            "resolution_height": project["resolution"]
        },
        "config": {
            "schema": "avalon-core:config-1.0",
            "apps": [
                {
                    "name": "maya2018",
                    "label": "Autodesk Maya 2018"
                }
            ],
            "tasks": tasks,
            "template": {
                "work":
                    "{root}/{project}/{silo}/{asset}/work/"
                    "{task}/{app}",
                "publish":
                    "{root}/{project}/{silo}/{asset}/publish/"
                    "{subset}/v{version:0>3}/{subset}.{representation}"
            }
        }
    }

    # Insert asset into Avalon DB
    avalon.insert_one(project_data)

    # Find the project in Avalon
    avalon_project = avalon.find_one(
        {"name": lib.get_consistent_name(project["name"]),
        "type": "project"})

    # Encode and store the data
    lib.set_project_data(data["project_id"], avalon_project["_id"],
        avalon_project['name'])

    avalon.uninstall()

    print("Create Project: \"{0} ({1})\"".format(project["name"], project["name"]))

def project_update_callback(data):
    """Update a project in Avalon when receiving an project:update event"""
    # Log in to API
    gazu.client.set_host("{0}/api".format(os.environ["GAZU_URL"]))
    gazu.log_in(os.environ["GAZU_USER"], os.environ["GAZU_PASSWD"])
    
    project = gazu.project.get_project(data["project_id"])

    # Get the Avalon project ID from partd
    project_data = lib.get_project_data(data["project_id"])

    os.environ["AVALON_PROJECT"] = project_data["collection"]

    avalon.uninstall()
    avalon.install()

    # Find the project in Avalon
    avalon_project = avalon.find_one(
        {"_id": avalon.ObjectId(project_data["id"]),
        "type": "project"})

    # Ensure project["name"] consistency.
    project_name = lib.get_consistent_name(project["name"])
    
    # Projects may not have a resolution set
    if project["resolution"]:
        resolution_width = int(int(project["resolution"]) / 9 * 16)
    else:
        resolution_width = None
        project["resolution"] = None

    # Get latest Tasks from Gazu
    tasks = [{"name": lib.get_consistent_name(task["name"]), 
        "label":task["name"]} for task in gazu.task.all_task_types()]

    # Update the Avalon project with new data from Gazu
    avalon_project["name"] = project_name
    avalon_project["data"]["label"] = project["name"]
    avalon_project["data"]["fps"] = project["fps"]
    avalon_project["data"]["resolution_width"] = resolution_width
    avalon_project["data"]["resolution_height"] = project["resolution"]
    avalon_project["config"]["tasks"] = tasks

    avalon.replace_one(
        {"_id": avalon.ObjectId(project_data["id"]),
        "type": "project"}, avalon_project
    )
    
    avalon.uninstall()

    
    if os.environ["AVALON_PROJECT"] != avalon_project["name"]:
        print("Updating project name from {0} to {1}".format(
            os.environ["AVALON_PROJECT"], avalon_project["name"]))
        lib.collection_rename(avalon_project["name"])

        lib.set_project_data(data["project_id"], avalon_project["_id"],
            avalon_project["name"])

    print("Updating Project: \"{0} ({1})\"".format(
        avalon_project["data"]["label"], avalon_project["name"]))
    

gazu.client.set_host(os.environ["GAZU_URL"])
event_client = gazu.events.init()

# Asset Event Types
gazu.events.add_listener(event_client, "asset:create", asset_create_callback)
gazu.events.add_listener(event_client, "asset:update", asset_update_callback)

# Project Event Types
gazu.events.add_listener(event_client, "project:new", project_new_callback)
gazu.events.add_listener(event_client, "project:update", project_update_callback)

gazu.events.run_client(event_client)
