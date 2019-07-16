import os
import gazu
import partd

from avalon import io as avalon


os.environ["AVALON_PROJECTS"] = r""
os.environ["AVALON_PROJECT"] = "temp"
os.environ["AVALON_ASSET"] = "bruce"
os.environ["AVALON_SILO"] = "assets"

def get_consistent_name(name):
    """Converts potentially inconsistent names."""
    return name.replace(" ", "_").lower()

def entity_new_callback(data):
    """
    On receiving a entity:new event, insert the asset into the 
    Avalon mongodb and store Zou id and Avalon id key value pair 
    for using in asset update events.
    """

    # Log in to API
    gazu.client.set_host("http://kitsu.teepee/api")
    gazu.log_in("teepee.external@mail.teepee", "qOi4mG6zI50a")
    
    asset = gazu.asset.get_asset(data["entity_id"])
    project = gazu.project.get_project(asset["project_id"])

    os.environ["AVALON_PROJECT"] = project["code"]

    avalon.uninstall()
    avalon.install()

    entity_type = gazu.entity.get_entity_type(asset["entity_type_id"])
    asset_data = {
        "schema": "avalon-core:asset-2.0",
        "name": get_consistent_name(asset["name"]),
        "silo": "assets",
        "type": "asset",
        "parent": avalon.locate([project["code"]]),
        "data": {
            "label": asset.get("label", asset["name"]),
            "group": entity_type["name"]
        }
    }

    # Inset asset into Avalon DB
    avalon.insert_one(asset_data)

    # Store Zou Id and Avalon Id key value pair of the asset
    directory = os.environ["PARTD_PATH"]
    directory = os.path.join(directory, "data", project["code"])

    # Create the data directory for the project if it doesn't exist.
    if not os.path.exists(directory):
        os.mkdir(directory)

    # Init partd
    p = partd.File(directory)

    # Check if the asset is already stored and delete it if it is.
    # (We're making the assumption that IDs supplied to us are unique).
    if p.get(data["entity_id"]):
        p.delete(data["entity_id"])

    # Find the asset in Avalon
    avalon_asset = avalon.find_one(
        {"name": get_consistent_name(asset["name"]),
        "type": "asset"})

    # Incode and store the data as a utf-8 bytes
    value = bytes(str(avalon_asset["_id"]), "utf-8")
    key_values = {data["entity_id"]: value}
    p.append(key_values)

    avalon.uninstall()

    print("Create Asset \"{0}\" in Project \"{1} ({2})\"".format(asset["name"], project["name"], project["code"]))

def entity_update_callback(data):
    """Update an asset name when receiving an entity:update event"""
    # Log in to API
    gazu.client.set_host("http://kitsu.teepee/api")
    gazu.log_in("teepee.external@mail.teepee", "qOi4mG6zI50a")
    
    asset = gazu.asset.get_asset(data["entity_id"])
    project = gazu.project.get_project(asset["project_id"])

    os.environ["AVALON_PROJECT"] = project["code"]

    avalon.uninstall()
    avalon.install()

    # Lookup the Zou Id and Avalon Id key value pair of the asset
    directory = os.environ["PARTD_PATH"]
    directory = os.path.join(directory, "data", project["code"])

    # Init partd
    p = partd.File(directory)

    # Get the Avalon asset ID from partd
    asset_id = p.get(data["entity_id"])
    asset_id = bytes.decode(asset_id, "utf-8")

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
    gazu.client.set_host("http://kitsu.teepee/api")
    gazu.log_in("teepee.external@mail.teepee", "qOi4mG6zI50a")
    
    project = gazu.project.get_project(data["project_id"])

    # Ensure project["code"] consistency.
    project_name = get_consistent_name(project["name"])
    
    if project["code"] != project_name:
        proj = {}
        proj["code"] = project_name
        proj["id"] = project["id"]
        project = gazu.project.update_project(proj)
        print("Updating Project Code...")

    os.environ["AVALON_PROJECT"] = project["code"]

    avalon.uninstall()
    avalon.install()

    # Newly created projects don't have a resolution set
    if project["resolution"]:
        resolution_width = int(int(project["resolution"]) / 9 * 16)
    else:
        resolution_width = None
        project["resolution"] = None

    tasks = [{"name": get_consistent_name(task["name"]), 
        "label":task["name"]} for task in gazu.task.all_task_types()]

    project_data = {
        "schema": "avalon-core:project-2.0",
        "name": project["code"],
        "type": "project",
        "parent": None,
        "data": {
            "label": project["name"],
            "code": project["code"],
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

    # Inset asset into Avalon DB
    avalon.insert_one(project_data)

    # Store Zou Id and Avalon Id key value pair of the asset
    directory = os.environ["PARTD_PATH"]
    directory = os.path.join(directory, "data", project["code"])

    # Create the data directory for the project if it doesn't exist.
    if not os.path.exists(directory):
        os.mkdir(directory)

    # Init partd
    p = partd.File(directory)

    # Check if the asproject set is already stored and delete it if it is.
    # (We're making the assumption that IDs supplied to us are unique).
    if p.get(data["project_id"]):
        p.delete(data["project_id"])

    # Find the project in Avalon
    avalon_project = avalon.find_one(
        {"name": get_consistent_name(project["code"]),
        "type": "project"})

    # Incode and store the data as a utf-8 bytes
    value = bytes(str(avalon_project["_id"]), "utf-8")
    key_values = {data["project_id"]: value}
    p.append(key_values)

    avalon.uninstall()

    print("Create Project \"{0} ({1})\"".format(project["name"], project["code"]))


def project_update_callback(data):
    """Update projects in Avalon"""
    pass
    

gazu.client.set_host("http://kitsu.teepee")
event_client = gazu.events.init()

# Asset Event Types
gazu.events.add_listener(event_client, "entity:new", entity_new_callback)
gazu.events.add_listener(event_client, "entity:update", entity_update_callback)

# Project Event Types
gazu.events.add_listener(event_client, "project:new", project_new_callback)
gazu.events.add_listener(event_client, "project:update", project_update_callback)

gazu.events.run_client(event_client)
