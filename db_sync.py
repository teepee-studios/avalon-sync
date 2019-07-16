import os
import gazu
import partd

from avalon import io as avalon


def get_consistent_name(name):
    """Converts potentially inconsistent names."""
    return name.replace(" ", "_").lower()


def main():
    projects = {}
    objects = {}
    objects_count = 0
    tasks = [{"name": get_consistent_name(task["name"]), 
        "label":task["name"]} for task in gazu.task.all_task_types()]
    print("Get Tasks...")
    for project in gazu.project.all_projects():
        # Ensure project["code"] consistency.
        project_name = get_consistent_name(project["name"])

        if project["code"] != project_name:
            proj = {}
            proj["code"] = project_name
            proj["id"] = project["id"]
            project = gazu.project.update_project(proj)
            print("Updating Project Code...")

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
            episode["code"] = get_consistent_name(episode["name"])
            episode["parent"] = project
            # Faking a parent for better hierarchy structure, until folders are
            # supported in Kitsu.
            episode["parents"] = ["episodes"]
            episodes.append(episode)
            for sequence in gazu.shot.all_sequences_for_episode(episode):
                sequence["code"] = get_consistent_name(sequence["name"])
                sequence["parent"] = episode
                sequence["parents"] = episode["parents"] + [episode["code"]]
                sequence["label"] = sequence["name"]
                sequence["name"] = "{0}_{1}".format(
                    episode["code"], sequence["code"]
                )
                sequence["visualParent"] = episode["name"]
                sequences.append(sequence)
                for shot in gazu.shot.all_shots_for_sequence(sequence):
                    shot["code"] = get_consistent_name(shot["name"])
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
                    "name": get_consistent_name(asset["name"]),
                    "silo": silo,
                    "type": "asset",
                    "parent": project["code"],
                    "data": {
                        "label": asset.get("label", asset["name"]),
                        "group": entity_type["name"],
                        "parents": asset["parents"]
                    }
                }

                if asset.get("visualParent"):
                    data["data"]["visualParent"] = asset["visualParent"]

                if asset.get("tasks"):
                    data["data"]["tasks"] = [
                        task["task_type_name"] for task in asset["tasks"]
                    ]

                entities[data["name"]] = data

                objects_count += 1

        objects[project["code"]] = entities

        # Newly created projects don't have a resolution set
        if project["resolution"]:
            resolution_width = int(int(project["resolution"]) / 9 * 16)
        else:
            resolution_width = None
            project["resolution"] = None

        projects[project["code"]] = {
            "schema": "avalon-core:project-2.0",
            "type": "project",
            "name": project["code"],
            "data": {
                "label": project["name"],
                "code": project["code"],
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

    os.environ["AVALON_PROJECTS"] = r""
    os.environ["AVALON_PROJECT"] = "temp"
    os.environ["AVALON_ASSET"] = "bruce"
    os.environ["AVALON_SILO"] = "assets"
    os.environ["AVALON_CONFIG"] = "polly"
    os.environ["AVALON_MONGO"] = os.environ.get(
        "AVALON_MONGO", "mongodb://127.0.0.1:27017"
    )

    print("Fetching Avalon data..")
    avalon.install()

    existing_projects = {}
    existing_objects = {}

    for project in avalon.projects():
        existing_projects[project["name"]] = project

        # Update project
        os.environ["AVALON_PROJECT"] = project["name"]
        avalon.uninstall()
        avalon.install()

        # Collect assets
        assets = {}
        for asset in avalon.find({"type": "asset"}):
            assets[asset["name"]] = asset

        existing_objects[project["name"]] = assets

    print("Synchronising..")
    for name, project in projects.items():
        if project["name"] in existing_projects:
            # Update task types
            existing_project = existing_projects[project["name"]]
            existing_project_task_types = existing_project["config"]["tasks"]
            if existing_project_task_types != tasks:
                print(
                    "Updating tasks types on project \"{0}\" to:\n{1}".format(
                        project["name"], tasks
                    )
                )
                existing_project["config"]["tasks"] = tasks
                os.environ["AVALON_PROJECT"] = project["name"]
                avalon.uninstall()
                avalon.install()
                avalon.replace_one({"type": "project"}, existing_project)

            continue

        print("Installing project: {0}".format(project["name"]))
        os.environ["AVALON_PROJECT"] = project["name"]
        avalon.uninstall()
        avalon.install()

        avalon.insert_one(project)

    for project["code"], assets in objects.items():
        os.environ["AVALON_PROJECT"] = project["code"]
        avalon.uninstall()
        avalon.install()

        for asset_name, asset in assets.items():
            if asset_name in existing_objects.get(project["code"], {}):
                # Update tasks
                if asset["data"].get("tasks"):
                    existing_project = existing_objects[project["code"]]
                    existing_asset = existing_project[asset_name]
                    existing_tasks = existing_asset["data"].get("tasks", [])
                    if existing_tasks != asset["data"]["tasks"]:
                        tasks = asset["data"]["tasks"]
                        print(
                            "Updating tasks on \"{0} / {1}\" to:\n{2}".format(
                                project["code"], asset_name, tasks
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
                asset["data"]["visualParent"] = avalon.find_one(
                    {"type": "asset", "name": asset["data"]["visualParent"]}
                )["_id"]
            print(
                "Installing asset: \"{0} / {1}\"".format(
                    project["code"], asset_name
                )
            )
            entity_id = asset.pop("id")
            avalon.insert_one(asset)

            # Store Zou Id and Avalon Id key value pair of the asset
            directory = os.environ["PARTD_PATH"]
            directory = os.path.join(directory, "data", project["id"])

            # Create the data directory for the project if it doesn't exist.
            if not os.path.exists(directory):
                os.mkdir(directory)

            # Init partd
            p = partd.File(directory)

            # Check if the asset is already stored and delete it if it is.
            # (We're making the assumption that IDs supplied to us are unique).
            if p.get(entity_id):
                p.delete(entity_id)
                print("Deleting: {0}".format(entity_id))
                

            avalon_asset = avalon.find_one(
                {"name": get_consistent_name(asset["name"]),
                "type": "asset"})

            # Encode and store the data as a utf-8 bytes
            value = bytes(str(avalon_asset["_id"]), "utf-8")
            key_values = {entity_id: value}
            p.append(key_values)

    print("Success")


if __name__ == '__main__':
    import time

    print("Logging in..")
    gazu.client.set_host("http://kitsu.teepee/api")
    gazu.log_in("teepee.external@mail.teepee", "qOi4mG6zI50a")
    print("Logged in..")

    while True:
        print("Syncing..")
        main()
        print("Sleeping for 30 seconds..")
        time.sleep(30)