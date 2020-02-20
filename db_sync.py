import os
import gazu
import shutil

import db as db
import lib as lib


def main():
    projects = {}
    objects = {}
    objects_count = 0

    logger.info("Get Project, Task, Asset and Shot Data...")

    tasks = [
        {"name": lib.get_consistent_name(task["name"]),
            "label":task["name"]} for task in gazu.task.all_task_types()
        ]

    for project in gazu.project.all_projects():
        # Ensure project["name"] consistency.
        project_name = lib.get_consistent_name(project["name"])

        # Collect assets.
        assets = []
        for asset in gazu.asset.all_assets_for_project(project):
            # Faking a parent for better hierarchy structure, until folders are
            # supported in Kitsu.
            asset["parents"] = ["assets"]
            asset["tasks"] = gazu.task.all_tasks_for_asset(asset)
            assets.append(asset)

        # Collect shots and parents.
        episodes = []
        sequences = []
        shots = []
        if project["production_type"] == "tvshow":
            for episode in (gazu.shot.all_episodes_for_project(project) or []):
                episode["code"] = lib.get_consistent_name(episode["name"])

                # Faking a parent for better hierarchy structure, until
                # folders are supported in Kitsu.
                episode["parents"] = ["episodes"]
                episodes.append(episode)
                for sequence in gazu.shot.all_sequences_for_episode(episode):
                    sequence["code"] = lib.get_consistent_name(sequence["name"])
                    sequence["label"] = sequence["name"]
                    sequence["name"] = "{0}_{1}".format(
                        episode["code"], sequence["code"]
                    )
                    sequence["visualParent"] = episode["name"]
                    sequences.append(sequence)
                    for shot in gazu.shot.all_shots_for_sequence(sequence):
                        shot["code"] = lib.get_consistent_name(shot["name"])
                        shot["label"] = shot["name"]
                        shot["name"] = "{0}_{1}_{2}".format(
                            episode["code"], sequence["code"], shot["code"]
                        )
                        shot["visualParent"] = sequence["name"]
                        shot["tasks"] = gazu.task.all_tasks_for_shot(shot)
                        shots.append(shot)
        else:
            for sequence in gazu.shot.all_sequences_for_project(project):
                sequence["code"] = lib.get_consistent_name(sequence["name"])
                sequence["label"] = sequence["name"]
                sequence["name"] = "{0}".format(sequence["code"])
                sequences.append(sequence)
                for shot in gazu.shot.all_shots_for_sequence(sequence):
                    shot["code"] = lib.get_consistent_name(shot["name"])
                    shot["label"] = shot["name"]
                    shot["name"] = "{0}_{1}".format(
                        sequence["code"], shot["code"]
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
                    asset["entity_type_id"])

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
                    }
                }

                if silo == "assets":
                    data["data"]["group"] = entity_type["name"]

                # If the silo is shots, group the shot under the proper
                # sequence and episode and hide sequences and episodes in the
                # launcher.
                elif silo == "shots":
                    if asset["type"] == "Shot":
                        data["data"]["group"] = asset["visualParent"].upper(
                            ).replace("_", " ")
                        # Add frame data for shots.
                        if asset["data"] is not None:
                            if "frame_in" in asset["data"]:
                                data["data"]["edit_in"] = asset["data"]["frame_in"]
                                data["data"]["startFrame"] = asset["data"]["frame_in"]
                            if "frame_out" in asset["data"]:
                                data["data"]["edit_out"] = asset["data"]["frame_out"]
                                data["data"]["endFrame"] = asset["data"]["frame_out"]
                            if "fps" in asset["data"]:
                                if asset["data"]["fps"] != "":
                                    data["data"]["fps"] = int(asset["data"]["fps"])
                    elif asset["type"] == "Sequence":
                        if "visualParent" in asset:
                            data["data"]["group"] = asset["visualParent"]
                        data["data"]["visible"] = False
                    elif asset["type"] == "Episode":
                        data["data"]["visible"] = False
                    data["asset_type"] = asset["type"]

                if "visualParent" in asset:
                    data["data"]["visualParent"] = asset["visualParent"]

                if "tasks" in asset:
                    data["data"]["tasks"] = []
                    for task in asset["tasks"]:
                        data["data"]["tasks"].append(lib.get_consistent_name(
                            task["task_type_name"]))

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
                "fps": int(project["fps"]),
                "resolution_width": int(resolution_width),
                "resolution_height": int(project["resolution"])
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

    logger.info("Found {0} projects".format(len(projects)))
    logger.info("Found {0} assets".format(objects_count))

    os.environ["AVALON_PROJECT"] = "temp"
    os.environ["AVALON_ASSET"] = "bruce"
    os.environ["AVALON_SILO"] = "assets"
    os.environ["AVALON_TASK"] = "model"
    os.environ["AVALON_WORKDIR"] = "/avalon"

    existing_projects = {}

    logger.info("Synchronising...")
    for name, project in projects.items():
        project_info = lib.get_project_data(project["id"])
        if project_info:
            existing_projects[project["name"]] = project
            # Update project
            os.environ["AVALON_PROJECT"] = project_info["collection"]
            db.uninstall()
            db.install()

            # Find the project in Avalon
            avalon_project = {}
            avalon_project = db.find_one(
                {"_id": db.ObjectId(project_info["id"]),
                    "type": "project"})

            # If project not found in Avalon DB error.
            if not avalon_project:
                logger.critical("Project missing from db.")
                logger.critical("Data directory and Avalon out of sync "
                                "quitting...")
                quit()

            # Set old and new project names
            project_name = lib.get_consistent_name(project["name"])
            old_project_name = lib.get_consistent_name(avalon_project["name"])

            # Update the Avalon project with new data from Gazu
            logger.info("Updating Project: {0} ({1})".format(
                project["data"]["label"], name))
            
            avalon_project["name"] = project_name
            avalon_project["data"]["label"] = project["data"]["label"]
            avalon_project["data"]["fps"] = int(project["data"]["fps"])
            avalon_project["data"]["resolution_width"] = int(
                project["data"]["resolution_width"])
            avalon_project["data"]["resolution_height"] = int(
                project["data"]["resolution_height"])
            avalon_project["config"]["tasks"] = tasks

            db.replace_one(
                {"_id": db.ObjectId(project_info["id"]),
                    "type": "project"}, avalon_project
            )
            db.uninstall()
            if old_project_name != project_name:
                logger.info("Updating project name from {0} to {1}".format(
                    old_project_name, project_name))

                lib.collection_rename(project_name)

                lib.set_project_data(
                    project["id"], project_info["id"], avalon_project["name"])

                # If file system path renaming is enabled, rename project disk
                # filepaths to match.
                if(os.environ["FILESYS_RENAME"]):
                    avalon_projects = os.environ["AVALON_PROJECTS"]

                    old_folder_name = os.path.join(avalon_projects, old_project_name)

                    new_folder_name = os.path.join(avalon_projects, project_name)

                    if os.path.exists(old_folder_name):
                        if not os.path.exists(new_folder_name):
                            logger.info("Project name updated, renaming {0} to {1}"
                                        .format(old_folder_name, new_folder_name))
                            shutil.move(old_folder_name, new_folder_name)
                        else:
                            logger.warning(
                                "Project name updated, trying to rename {0} to {1}, but "
                                "new folder already exists. No action taken."
                                .format(old_folder_name, new_folder_name)
                            )
                    else:
                        logger.warning(
                            "Project name updated, but {0} does not exist. No "
                            "action taken."
                            .format(old_folder_name))

        else:
            logger.info("Installing project: {0}".format(project["name"]))
            os.environ["AVALON_PROJECT"] = project["name"]
            db.uninstall()
            db.install()

            # Remove Gazu ID from project so it doesn't go into the Avalon DB
            project_id = project.pop("id")

            # Inset project into Avalon DB
            db.insert_one(project)

            # Put Gazu ID back into the project so we can use it later for
            # assets.
            project.update(id=project_id)

            # Find the new project in Avalon
            avalon_project = db.find_one(
                {"name": lib.get_consistent_name(project["name"]),
                    "type": "project"})

            # Store a key of Gazu project ID and a list of the Avalon
            # project ID and project code (mongodb collection) as a value.
            lib.set_project_data(
                project_id, avalon_project["_id"], project["name"])

    for project["id"], assets in objects.items():
        project_info = lib.get_project_data(project["id"])
        os.environ["AVALON_PROJECT"] = project_info["collection"]
        db.uninstall()
        db.install()

        for asset_name, asset in assets.items():
            asset_id = lib.get_asset_data(project["id"], asset["id"])

            if asset_id:
                # Update Assets in Avalon with new data from Gazu

                # Find asset in Avalon
                avalon_asset = {}
                avalon_asset = db.find_one(
                    {"_id": db.ObjectId(asset_id), "type": "asset"})

                logger.info("Updating Asset: {0} ({1})".format(
                    avalon_asset["data"]["label"], avalon_asset["name"]))

                # Set keep asset name for use in filesystem path renaming.
                old_asset_name = lib.get_consistent_name(avalon_asset["name"])

                # Ensure asset["name"] consistency.
                asset_name = lib.get_consistent_name(asset["name"])

                if old_asset_name != asset_name:
                    logger.info("Updating asset name from {0} to {1}".format(
                        avalon_asset["name"], asset_name))

                avalon_asset["name"] = asset_name
                avalon_asset["data"]["label"] = asset["data"]["label"]
                avalon_asset["data"]["group"] = asset["data"]["group"]

                if avalon_asset["silo"] == "shots" and asset["asset_type"] == "Shot":

                    if asset["data"] is not None:
                        if "edit_in" in asset["data"]:
                            avalon_asset["data"]["edit_in"] = asset["data"]["edit_in"]
                            avalon_asset["data"]["startFrame"] = asset["data"][
                                "startFrame"]
                        if "edit_out" in asset["data"]:
                            avalon_asset["data"]["edit_out"] = asset["data"]["edit_out"]
                            avalon_asset["data"]["endFrame"] = asset["data"]["endFrame"]
                        if "fps" in asset["data"]:
                            if asset["data"]["fps"] != "":
                                avalon_asset["data"]["fps"] = int(asset["data"]["fps"])
                        if "fps" in avalon_asset["data"] and "fps" not in asset["data"]:
                            del avalon_asset["data"]["fps"]

                if "tasks" in asset["data"]:
                    avalon_asset["data"]["tasks"] = asset["data"]["tasks"]

                db.replace_one(
                    {"_id": db.ObjectId(asset_id), "type": "asset"},
                    avalon_asset)

                if(os.environ["FILESYS_RENAME"]):
                    if avalon_asset["silo"] == "shots":
                        # If file system path renaming is enabled, rename shot disk
                        # filepaths to match.
                        lib.rename_filepath(
                            old_asset_name, asset_name, project_name, "shots")
                    else:
                        # If file system path renaming is enabled, rename asset disk
                        # filepaths to match.
                        lib.rename_filepath(
                            old_asset_name, asset_name, project_name, "assets"
                            )
            else:
                # Insert new Assets into Avalon
                asset["parent"] = db.locate([asset["parent"]])

                if "visualParent" in asset["data"]:
                    visual_parent = lib.get_consistent_name(
                        asset["data"]["visualParent"])
                    asset_data = db.find_one(
                        {"type": "asset", "name": visual_parent})
                    asset["data"]["visualParent"] = asset_data["_id"]

                logger.info("Installing asset: \"{0} / {1}\"".format(
                    project["id"], asset_name))

                # Remove Gazu ID and asset_type from asset so it doesn't go
                # into the Avalon DB.
                asset_gazu_id = asset.pop("id")
                if "asset_type" in asset:
                    asset.pop("asset_type")

                # Inset asset into Avalon DB
                db.insert_one(asset)

                # Get the Id of the asset we just inserted into Avalon
                avalon_asset = db.find_one(
                    {"name": lib.get_consistent_name(asset["name"]), "type": "asset"})

                # Encode and store the Gazu Id and Avalon Id
                lib.set_asset_data(
                    project["id"], asset_gazu_id, avalon_asset["_id"])

    logger.info("Success")


logger = lib.init_logging("db_sync")

logger.info("Logging in...")
gazu.client.set_host("{0}/api".format(os.environ["GAZU_URL"]))
gazu.log_in(os.environ["GAZU_USER"], os.environ["GAZU_PASSWD"])
logger.info("Logged in...")


logger.info("Syncing...")
main()
