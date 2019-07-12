import os
import gazu
import partd

from avalon import io as avalon

#help("modules")
gazu.client.set_host("http://kitsu.teepee/api")
gazu.log_in("teepee.external@mail.teepee", "qOi4mG6zI50a")

os.environ["AVALON_PROJECTS"] = r""
os.environ["AVALON_PROJECT"] = "temp"
os.environ["AVALON_ASSET"] = "bruce"
os.environ["AVALON_SILO"] = "assets"

def get_consistent_name(name):
    """Converts potentially inconsistent names."""
    return name.replace(" ", "_").lower()

def entity_new_callback(data):
    """On receiving an asset creation event insert it the Avalon mongodb
    and store Zou id and Avalon id key value pair for using in asset 
    update events"""

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

    if not os.path.exists(directory):
        os.mkdir(directory)

    p = partd.File(directory)

    if p.get(data["entity_id"]):
        p.delete(data["entity_id"])

    avalon_asset = avalon.find_one(
        {"name": get_consistent_name(asset["name"]),
        "type": "asset"})

    value = bytes(str(avalon_asset["_id"]), "utf-8")
    key_values = {data["entity_id"]: value}
    p.append(key_values)

    avalon.uninstall()

    print("Create Asset \"{0}\" in Project \"{1} ({2})\"".format(asset["name"], project["name"], project["code"]))

    

gazu.client.set_host("http://kitsu.teepee")
event_client = gazu.events.init()
gazu.events.add_listener(event_client, "entity:new", entity_new_callback)
gazu.events.run_client(event_client)
