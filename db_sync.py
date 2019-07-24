import os
import gazu
import partd

from avalon import io as avalon
import lib as lib

def main():
    projects = {}
    objects = {}
    objects_count = 0
    tasks = [{"name": lib.get_consistent_name(task["name"]), 
        "label":task["name"]} for task in gazu.task.all_task_types()]
    print("Get Tasks...")
    for project in gazu.project.all_projects():
        # Ensure project["name"] consistency.
        project_name = lib.get_consistent_name(project["name"])

        # Collect assets.
        assets = []
        for asset in gazu.asset.all_assets_for_project(project):
            # Faking a parent for better hierarchy structure, until folders are
            # supported in Kitsu.
            asset["parents"] = ["assets"]
            assets.append(asset)

        # Collect shots and parents.
        episodes = []
        sequences = []
        shots = []
        for episode in (gazu.shot.all_episodes_for_project(project) or []):
            episode["code"] = lib.get_consistent_name(episode["name"])
            episode["parent"] = project
            # Faking a parent for better hierarchy structure, until folders are
            # supported in Kitsu.
            episode["parents"] = ["episodes"]
            episodes.append(episode)
            for sequence in gazu.shot.all_sequences_for_episode(episode):
                sequence["code"] = lib.get_consistent_name(sequence["name"])
                sequence["parent"] = episode
                sequence["parents"] = episode["parents"] + [episode["code"]]
                sequence["label"] = sequence["name"]
                sequence["name"] = "{0}_{1}".format(
                    episode["code"], sequence["code"]
                )
                sequence["visualParent"] = episode["name"]
                sequences.append(sequence)
                for shot in gazu.shot.all_shots_for_sequence(sequence):
                    shot["code"] = lib.get_consistent_name(shot["name"])
                    shot["parent"] = sequence
                    shot["parents"] = sequence["parents"] + [sequence["code"]]
                    shot["label"] = shot["name"]
                    shot["name"] = "{0}_{1}_{2}".format(
                        episode["code"], sequence["code"], shot["code"]
                    )
                    shot["visualParent"] = sequence["name"]
                    shot["tasks"] = gazu.task.all_tasks_for_shot(shot)
                    shots.append(shot)

        silos = [
            [assets, "assets"],
            [episodes, "shots"],
            [sequences, "shots"],
            [shots, "shots"]
        ]
        entities = {}
        for assets, silo in silos:
            for asset in assets:
                entity_type = gazu.entity.get_entity_type(
                    asset["entity_type_id"]
                )

                data = {
                    "id": asset["id"],
                    "schema": "avalon-core:asset-2.0",
                    "name": lib.get_consistent_name(asset["name"]),
                    "silo": silo,
                    "type": "asset",
                    "parent": project_name,
                    "data": {
                        "label": asset.get("label", asset["name"]),
                        "group": entity_type["name"],
                        "parents": asset["parents"]
                    }
                }
                
                if silo == "assets":
                    data["group"] = entity_type["name"]

                # If the silo is shots, group the shot under the proper sequence 
                # and episode and hide sequences and episodes in the launcher.
                elif silo == "shots":
                    if asset["type"] == "Shot":
                        layout_data = asset["visualParent"].split("_")
                        data["data"]["group"] = "{0} {1}".format(layout_data[0].upper(), 
                            layout_data[1].upper())
                    elif asset["type"] == "Sequence":
                        data["data"]["group"] = asset["visualParent"]
                        data["data"]["visible"] = False
                    elif asset["type"] == "Episode":
                        data["data"]["visible"] = False

                if asset.get("visualParent"):
                    data["data"]["visualParent"] = asset["visualParent"]

                if asset.get("tasks"):
                    data["data"]["tasks"] = [
                        task["task_type_name"] for task in asset["tasks"]
                    ]

                entities[data["name"]] = data

                objects_count += 1

        objects[project["id"]] = entities

        # Newly created projects don't have a resolution set
        if project["resolution"]:
            resolution_width = int(int(project["resolution"]) / 9 * 16)
        else:
            resolution_width = None
            project["resolution"] = None

        projects[project_name] = {
            "id": project["id"],
            "schema": "avalon-core:project-2.0",
            "type": "project",
            "name": project_name,
            "data": {
                "label": project["name"],
                "fps": project["fps"],
                "resolution_width": resolution_width,
                "resolution_height": project["resolution"]
            },
            "parent": None,
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

    print("Found:")
    print("- %d projects" % len(projects))
    print("- %d assets" % objects_count)

    os.environ["AVALON_PROJECT"] = "temp"
    os.environ["AVALON_ASSET"] = "bruce"
    os.environ["AVALON_SILO"] = "assets"

    existing_projects = {}
    existing_objects = {}

    print("Synchronising..")
    for name, project in projects.items():
        project_info = lib.get_project_data(project["id"])
        if project_info:
            existing_projects[project["name"]] = project
            # Update project
            os.environ["AVALON_PROJECT"] = project_info["collection"]
            avalon.uninstall()
            avalon.install()

            # Collect assets
            print("Fetching Avalon assets..")
            assets = {}
            for asset in avalon.find({"type": "asset"}):
                assets[asset["name"]] = asset

            existing_objects[project["id"]] = assets
            
            # Find the project in Avalon
            avalon_project = avalon.find_one(
                {"_id": avalon.ObjectId(project_info["id"]),
                "type": "project"})
            print
            # Update the Avalon project with new data from Gazu
            print("Updating Project: \"{0} ({1})\"".format(project["data"]["label"], 
                name))
            avalon_project["name"] = project["name"]
            avalon_project["data"]["label"] = project["data"]["label"]
            avalon_project["data"]["fps"] = project["data"]["fps"]
            avalon_project["data"]["resolution_width"] = project["data"]["resolution_width"]
            avalon_project["data"]["resolution_height"] = project["data"]["resolution_height"]
            avalon_project["config"]["tasks"] = tasks

            avalon.replace_one(
                {"_id": avalon.ObjectId(project_info["id"]),
                "type": "project"}, avalon_project
            )
            if os.environ["AVALON_PROJECT"] != avalon_project["name"]:
                print("Updating project name from {0} to {1}".format(
                    os.environ["AVALON_PROJECT"], avalon_project["name"]))
                lib.collection_rename(avalon_project["name"])

                lib.set_project_data(project["id"], project_info["id"],
                    avalon_project["name"])

        else:
            print("Installing project: {0}".format(project["name"]))
            os.environ["AVALON_PROJECT"] = project["name"]
            avalon.uninstall()
            avalon.install()

            # Remove Gazu ID from project so it doesn't go into the Avalon DB
            project_id = project.pop("id")
            
            # Inset project into Avalon DB
            avalon.insert_one(project)

            # Put Gazu ID back into the project so we can use it later for assets
            project.update(id=project_id)
            
            # Find the new project in Avalon
            avalon_project = avalon.find_one(
                {"name": lib.get_consistent_name(project["name"]),
                "type": "project"})

            # Store a key of Gazu project ID and a list of the Avalon project ID 
            # and project code (mongodb collection) as a value.
            lib.set_project_data(project_id, avalon_project["_id"], project["name"])
            
    for project["id"], assets in objects.items():
        project_info = lib.get_project_data(project["id"])
        os.environ["AVALON_PROJECT"] = project_info["collection"]
        avalon.uninstall()
        avalon.install()

        for asset_name, asset in assets.items():
            if asset_name in existing_objects.get(project["id"], {}):
                # Update tasks
                if asset["data"].get("tasks"):
                    existing_project = existing_objects[project["id"]]
                    existing_asset = existing_project[asset_name]
                    existing_tasks = existing_asset["data"].get("tasks", [])
                    if existing_tasks != asset["data"]["tasks"]:
                        tasks = asset["data"]["tasks"]
                        print(
                            "Updating tasks on \"{0} / {1}\" to:\n{2}".format(
                                project["id"], asset_name, tasks
                            )
                        )
                        existing_asset["data"]["tasks"] = tasks
                        avalon.replace_one(
                            {"type": "asset", "name": asset_name},
                            existing_asset
                        )

                continue

            asset["parent"] = avalon.locate([asset["parent"]])
            
            if asset["data"].get("visualParent"):
                vp = lib.get_consistent_name(asset["data"]["visualParent"])
                asset_data = avalon.find_one({"type": "asset", "name": vp})
                asset["data"]["visualParent"] = asset_data["_id"]
            print(
                "Installing asset: \"{0} / {1}\"".format(
                    project["id"], asset_name
                )
            )
            entity_id = asset.pop("id")
            # Inset asset into Avalon DB
            avalon.insert_one(asset)

            avalon_asset = avalon.find_one(
                {"name": lib.get_consistent_name(asset["name"]),
                "type": "asset"})

            # Encode and store the data as a utf-8 bytes
            lib.set_asset_data(project["id"], entity_id, avalon_asset["_id"])

    print("Success")


if __name__ == '__main__':
    import time

    print("Logging in..")
    gazu.client.set_host("{0}/api".format(os.environ["GAZU_URL"]))
    gazu.log_in(os.environ["GAZU_USER"], os.environ["GAZU_PASSWD"])
    print("Logged in..")

    while True:
        print("Syncing..")
        main()
        print("Sleeping for 30 seconds..")
        time.sleep(30)