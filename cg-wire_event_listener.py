import os
import sys
import gazu
import pymongo

from avalon import io as avalon

#help("modules")
gazu.client.set_host("http://kitsu.teepee/api")
gazu.log_in("teepee.external@mail.teepee", "qOi4mG6zI50a")

os.environ["AVALON_PROJECTS"] = r""
os.environ["AVALON_PROJECT"] = "temp"
os.environ["AVALON_ASSET"] = "bruce"
os.environ["AVALON_SILO"] = "assets"
os.environ["AVALON_CONFIG"] = "polly"
os.environ["AVALON_MONGO"] = os.environ.get(
    "AVALON_MONGO", "mongodb://127.0.0.1:27017"
)



def get_consistent_name(name):
    """Converts potentially inconsistent names."""
    return name.replace(" ", "_").lower()

def entity_new_callback(data):
    gazu.client.set_host("http://kitsu.teepee/api")
    gazu.log_in("teepee.external@mail.teepee", "qOi4mG6zI50a")
    
    asset = gazu.asset.get_asset(data["entity_id"])
    project = gazu.project.get_project(asset["project_id"])

    os.environ["AVALON_PROJECT"] = project["code"]

    avalon.uninstall()
    avalon.install()

    print("Parent: {0}".format([project["code"]]))
    print(avalon.locate([project["code"]]))

    entity_type = gazu.entity.get_entity_type(asset["entity_type_id"])
    data = {
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

    avalon.uninstall()
    avalon.install()

    avalon.insert_one(data)

    avalon.uninstall()

    #print("Project Name: {1}\nProject Code: {2}\nAsset: {0}\n".format(asset["name"], project["name"], project["code"]))
    print("Create Asset \"{0}\" in Project \"{1} ({2})\"".format(asset["name"], project["name"], project["code"]))

    

gazu.client.set_host("http://kitsu.teepee")
event_client = gazu.events.init()
gazu.events.add_listener(event_client, "entity:new", entity_new_callback)
gazu.events.run_client(event_client)