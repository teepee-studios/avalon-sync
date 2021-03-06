import os
import gazu
import shutil

import db as db
import lib as lib


os.environ["AVALON_PROJECT"] = "temp"
os.environ["AVALON_ASSET"] = "bruce"
os.environ["AVALON_SILO"] = "assets"
os.environ["AVALON_TASK"] = "model"
os.environ["AVALON_WORKDIR"] = "/avalon"


def asset_create_callback(data):
    """
    On receiving a asset:create event, insert the asset into the
    Avalon mongodb and store Zou Id and Avalon Id key value pair
    for using in asset update events.
    """

    # Log in to API
    gazu.client.set_host("{0}/api".format(os.environ["GAZU_URL"]))
    gazu.log_in(os.environ["GAZU_USER"], os.environ["GAZU_PASSWD"])

    asset = gazu.asset.get_asset(data["asset_id"])
    project = gazu.project.get_project(asset["project_id"])

    project_name = lib.get_consistent_name(project["name"])

    os.environ["AVALON_PROJECT"] = project_name

    db.uninstall()
    db.install()

    entity_type = gazu.entity.get_entity_type(asset["entity_type_id"])
    asset_data = {
        "schema": "avalon-core:asset-2.0",
        "name": lib.get_consistent_name(asset["name"]),
        "silo": "assets",
        "type": "asset",
        "parent": db.locate([project_name]),
        "data": {
            "label": asset.get("label", asset["name"]),
            "group": entity_type["name"]
        }
    }

    # Inset asset into Avalon DB
    db.insert_one(asset_data)

    # Get the Id of the asset we just inserted into Avalon
    avalon_asset = db.find_one({
        "name": lib.get_consistent_name(asset["name"]),
        "type": "asset"})

    # Encode and store the Gazu Id and Avalon Id
    lib.set_asset_data(project["id"], data["asset_id"], avalon_asset["_id"])

    db.uninstall()

    logger.info("Create Asset \"{0}\" in Project \"{1}\"".format(
        asset["name"], project["name"]))


def asset_update_callback(data):
    """Update an asset name when receiving an asset:update event"""
    # Log in to API
    gazu.client.set_host("{0}/api".format(os.environ["GAZU_URL"]))
    gazu.log_in(os.environ["GAZU_USER"], os.environ["GAZU_PASSWD"])

    asset = gazu.asset.get_asset(data["asset_id"])
    project = gazu.project.get_project(asset["project_id"])
    project_name = lib.get_consistent_name(project["name"])

    os.environ["AVALON_PROJECT"] = project_name

    db.uninstall()
    db.install()

    # Get Avalon Asset Id.
    asset_id = lib.get_asset_data(project["id"], data["asset_id"])
    # Get asset Type
    entity_type = gazu.entity.get_entity_type(asset["entity_type_id"])

    # Find the asset in Avalon
    avalon_asset = db.find_one(
        {"_id": db.ObjectId(asset_id),
            "type": "asset"})

    # Set keep asset name for use in filesystem path renaming.
    old_asset_name = lib.get_consistent_name(avalon_asset["name"])

    # Ensure asset["name"] consistency.
    asset_name = lib.get_consistent_name(asset["name"])

    avalon_asset["name"] = asset_name
    avalon_asset["data"]["label"] = asset["name"]
    avalon_asset["data"]["group"] = entity_type["name"]

    db.replace_one(
        {"_id": db.ObjectId(asset_id), "type": "asset"}, avalon_asset)

    db.uninstall()

    logger.info("Updated Asset \"{0}\" in Project \"{1}\"".format(
        old_asset_name, project["name"]))

    if asset_name != old_asset_name:
        logger.info("Asset renamed from \"{0}\" to \"{1}\"".format(
            old_asset_name, asset_name))

    # If file system path renaming is enabled, rename asset disk
    # filepaths to match.
    if(os.environ["FILESYS_RENAME"]):
        lib.rename_filepath(old_asset_name, asset_name, project_name, "assets")


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

    db.uninstall()
    db.install()

    # Newly created projects don't have a resolution set
    if project["resolution"]:
        resolution_width = int(int(project["resolution"]) / 9 * 16)
    else:
        resolution_width = None
        project["resolution"] = None
    # Get tasks from Gazu API
    tasks = [
        {"name": lib.get_consistent_name(task["name"]),
            "label":task["name"]}
        for task in gazu.task.all_task_types()]

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
    db.insert_one(project_data)

    # Find the project in Avalon
    avalon_project = db.find_one({
        "name": lib.get_consistent_name(project["name"]),
        "type": "project"})

    # Encode and store the data
    lib.set_project_data(
        data["project_id"], avalon_project["_id"], avalon_project['name'])

    db.uninstall()

    logger.info("Created Project: \"{0}\"".format(project["name"]))


def project_update_callback(data):
    """Update a project in Avalon when receiving an project:update event"""
    # Log in to API
    gazu.client.set_host("{0}/api".format(os.environ["GAZU_URL"]))
    gazu.log_in(os.environ["GAZU_USER"], os.environ["GAZU_PASSWD"])

    project = gazu.project.get_project(data["project_id"])

    # Get the Avalon project ID from partd
    project_data = lib.get_project_data(data["project_id"])

    os.environ["AVALON_PROJECT"] = project_data["collection"]

    db.uninstall()
    db.install()

    # Find the project in Avalon
    avalon_project = db.find_one({
        "_id": db.ObjectId(project_data["id"]),
        "type": "project"})

    # Ensure project["name"] consistency.
    project_name = lib.get_consistent_name(project["name"])
    old_project_name = lib.get_consistent_name(avalon_project["name"])

    # Projects may not have a resolution set
    if project["resolution"]:
        resolution_width = int(int(project["resolution"]) / 9 * 16)
    else:
        resolution_width = None
        project["resolution"] = None

    # Get latest Tasks from Gazu
    tasks = [
        {"name": lib.get_consistent_name(task["name"]),
            "label":task["name"]}
        for task in gazu.task.all_task_types()]

    # Update the Avalon project with new data from Gazu
    avalon_project["name"] = project_name
    avalon_project["data"]["label"] = project["name"]
    avalon_project["data"]["fps"] = int(project["fps"])
    avalon_project["data"]["resolution_width"] = int(resolution_width)
    avalon_project["data"]["resolution_height"] = int(project["resolution"])
    avalon_project["config"]["tasks"] = tasks

    db.replace_one({
        "_id": db.ObjectId(project_data["id"]),
        "type": "project"}, avalon_project
    )

    db.uninstall()

    if old_project_name != project_name:
        logger.info("Updating project name from {0} to {1}".format(
            old_project_name, project_name))
        lib.collection_rename(project_name)

        lib.set_project_data(
            data["project_id"], avalon_project["_id"], avalon_project["name"])

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
                        "Project name updated, trying to rename {0} to {1}, but new "
                        "folder already exists. No action taken."
                        .format(old_folder_name, new_folder_name)
                    )
            else:
                logger.warning(
                    "Project name updated, but {0} does not exist. No "
                    "action taken."
                    .format(old_folder_name))

    logger.info("Updating Project: \"{0} ({1})\"".format(
        avalon_project["data"]["label"], project_name))


def shot_new_callback(data):
    """
    On receiving a shot:new event, insert the shot into the
    Avalon mongodb and store Zou Id and Avalon Id key value pair
    for using in asset update events.
    """

    # Log in to API
    gazu.client.set_host("{0}/api".format(os.environ["GAZU_URL"]))
    gazu.log_in(os.environ["GAZU_USER"], os.environ["GAZU_PASSWD"])

    shot = gazu.shot.get_shot(data["shot_id"])
    project = gazu.project.get_project(shot["project_id"])

    if project["production_type"] == "tvshow":
        project_name = lib.get_consistent_name(project["name"])
        episode_name = lib.get_consistent_name(shot["episode_name"])
        sequence_name = lib.get_consistent_name(shot["sequence_name"])
        shot_name = lib.get_consistent_name(shot["name"])
        visualParent = [project_name, "{0}_{1}".format(
            episode_name, sequence_name)]

        os.environ["AVALON_PROJECT"] = project_name

        db.uninstall()
        db.install()

        shot_data = {
            "schema": "avalon-core:asset-2.0",
            "name": "{0}_{1}_{2}".format(episode_name, sequence_name, shot_name),
            "silo": "shots",
            "type": "asset",
            "parent": db.locate([project_name]),
            "data": {
                "label": shot["name"],
                "group": "{0} {1}".format(
                    shot["episode_name"].upper(),
                    shot["sequence_name"].upper()),
                "visualParent": db.locate(visualParent)
            }
        }
    else:
        project_name = lib.get_consistent_name(project["name"])
        sequence_name = lib.get_consistent_name(shot["sequence_name"])
        shot_name = lib.get_consistent_name(shot["name"])
        visualParent = [project_name, "{0}".format(
            sequence_name)]

        os.environ["AVALON_PROJECT"] = project_name

        db.uninstall()
        db.install()

        shot_data = {
            "schema": "avalon-core:asset-2.0",
            "name": "{0}_{1}".format(sequence_name, shot_name),
            "silo": "shots",
            "type": "asset",
            "parent": db.locate([project_name]),
            "data": {
                "label": shot["name"],
                "group": "{0}".format(shot["sequence_name"].upper()),
                "visualParent": db.locate(visualParent)
            }
        }

    # Inset shot into Avalon DB
    db.insert_one(shot_data)

    # Get the Id of the shot we just inserted into Avalon
    avalon_shot = db.find_one({
        "name": lib.get_consistent_name(shot_data["name"]),
        "type": "asset"})

    # Encode and store the Gazu Id and Avalon Id
    lib.set_asset_data(project["id"], data["shot_id"], avalon_shot["_id"])

    logger.info("Created Shot \"{0}\" in Project \"{1}\"".format(
        shot["name"], project["name"]))


def shot_update_callback(data):
    """Update an shot name when receiving an shot:update event"""
    # Log in to API
    gazu.client.set_host("{0}/api".format(os.environ["GAZU_URL"]))
    gazu.log_in(os.environ["GAZU_USER"], os.environ["GAZU_PASSWD"])

    shot = gazu.shot.get_shot(data["shot_id"])
    project = gazu.project.get_project(shot["project_id"])
    if project["production_type"] == "tvshow":
        # Ensure name consistency.
        project_name = lib.get_consistent_name(project["name"])
        episode_name = lib.get_consistent_name(shot["episode_name"])
        sequence_name = lib.get_consistent_name(shot["sequence_name"])
        shot_name = lib.get_consistent_name(shot["name"])
        visualParent = [project_name, "{0}_{1}".format(
            episode_name, sequence_name)]

        os.environ["AVALON_PROJECT"] = project_name

        db.uninstall()
        db.install()

        # Get Avalon Shot Id.
        shot_id = lib.get_asset_data(project["id"], data["shot_id"])

        # Find the asset in Avalon
        avalon_shot = db.find_one({
            "_id": db.ObjectId(shot_id),
            "type": "asset"})

        # Set keep shot name for use in filesystem path renaming.
        old_shot_name = lib.get_consistent_name(avalon_shot["name"])
        new_shot_name = "{0}_{1}_{2}".format(
            episode_name, sequence_name, shot_name)

        avalon_shot["name"] = new_shot_name
        avalon_shot["data"]["label"] = shot["name"]
        avalon_shot["data"]["group"] = "{0} {1}".format(
            shot["episode_name"].upper(), shot["sequence_name"].upper())
        avalon_shot["data"]["visualParent"] = db.locate(visualParent)

    else:
        # Ensure name consistency.
        project_name = lib.get_consistent_name(project["name"])
        sequence_name = lib.get_consistent_name(shot["sequence_name"])
        shot_name = lib.get_consistent_name(shot["name"])
        visualParent = [project_name, "{0}".format(sequence_name)]

        os.environ["AVALON_PROJECT"] = project_name

        db.uninstall()
        db.install()

        # Get Avalon Shot Id.
        shot_id = lib.get_asset_data(project["id"], data["shot_id"])

        # Find the asset in Avalon
        avalon_shot = db.find_one({
            "_id": db.ObjectId(shot_id),
            "type": "asset"})

        # Set keep shot name for use in filesystem path renaming.
        old_shot_name = lib.get_consistent_name(avalon_shot["name"])
        new_shot_name = "{0}_{1}".format(sequence_name, shot_name)

        avalon_shot["name"] = new_shot_name
        avalon_shot["data"]["label"] = shot["name"]
        avalon_shot["data"]["group"] = "{0}".format(shot["sequence_name"].upper())
        avalon_shot["data"]["visualParent"] = db.locate(visualParent)

    if shot["data"] is not None:
        if "frame_in" in shot["data"]:
            avalon_shot["data"]["edit_in"] = shot["data"]["frame_in"]
            avalon_shot["data"]["startFrame"] = shot["data"]["frame_in"]
        if "frame_out" in shot["data"]:
            avalon_shot["data"]["edit_out"] = shot["data"]["frame_out"]
            avalon_shot["data"]["endFrame"] = shot["data"]["frame_out"]
        if "fps" in shot["data"]:
            if shot["data"]["fps"] != "":
                avalon_shot["data"]["fps"] = int(shot["data"]["fps"])
        if "fps" in avalon_shot["data"] and shot["data"]["fps"] == "":
            del avalon_shot["data"]["fps"]

    db.replace_one({
        "_id": db.ObjectId(shot_id),
        "type": "asset"}, avalon_shot)

    db.uninstall()

    logger.info("Updated Shot \"{0}\" in Project \"{1}\"".format(
        avalon_shot["name"], project["name"]))

    if new_shot_name != old_shot_name:
        logger.info("Shot renamed from \"{0}\" to \"{1}\"".format(
            old_shot_name, new_shot_name))

    # If file system path renaming is enabled, rename shot disk
    # filepaths to match.
    if(os.environ["FILESYS_RENAME"]):
        lib.rename_filepath(
            old_shot_name, new_shot_name, project_name, "shots")


def task_new_callback(data):
    """
    On receiving a task:new event, add a task to an asset in the
    Avalon mongodb.
    """

    # Log in to API
    gazu.client.set_host("{0}/api".format(os.environ["GAZU_URL"]))
    gazu.log_in(os.environ["GAZU_USER"], os.environ["GAZU_PASSWD"])

    task = gazu.task.get_task(data["task_id"])
    entity = task["entity"]
    project = task["project"]
    task_type = task["task_type"]

    project_name = lib.get_consistent_name(project["name"])
    task_name = lib.get_consistent_name(task_type["name"])

    # Get Avalon Asset Id.
    entity_id = lib.get_asset_data(project["id"], entity["id"])

    os.environ["AVALON_PROJECT"] = project_name

    db.uninstall()
    db.install()

    # Find the asset in Avalon
    avalon_entity = db.find_one({
        "_id": db.ObjectId(entity_id),
        "type": "asset"})

    if avalon_entity["data"] is not None:
        if "tasks" in avalon_entity["data"]:
            avalon_entity["data"]["tasks"].append(task_name)
        else:
            avalon_entity["data"]["tasks"] = [task_name]
    else:
        avalon_entity["data"]["tasks"] = [task_name]

    db.replace_one(
        {"_id": db.ObjectId(entity_id), "type": "asset"}, avalon_entity)

    db.uninstall()

    logger.info("Added new \"{2}\" Task to \"{0}\" in Project \"{1}\"".format(
        avalon_entity["name"], project["name"], task_type["name"]))


def episode_new_callback(data):
    """
    On receiving a episode:new event, add the episode to the Avalon
    mongodb.
    """

    # Log in to API
    gazu.client.set_host("{0}/api".format(os.environ["GAZU_URL"]))
    gazu.log_in(os.environ["GAZU_USER"], os.environ["GAZU_PASSWD"])

    episode = gazu.shot.get_episode(data["episode_id"])
    project = gazu.project.get_project(episode["project_id"])

    project_name = lib.get_consistent_name(project["name"])

    os.environ["AVALON_PROJECT"] = project_name

    db.uninstall()
    db.install()

    episode_data = {
        "schema": "avalon-core:asset-2.0",
        "name": lib.get_consistent_name(episode["name"]),
        "silo": "shots",
        "type": "asset",
        "parent": db.locate([project_name]),
        "data": {
            "label": episode["name"].upper(),
            "group": "Episode"
        }
    }
    episode_data["data"]["visible"] = False

    # Inset asset into Avalon DB
    db.insert_one(episode_data)

    # Get the Id of the asset we just inserted into Avalon
    avalon_episode = db.find_one({
        "name": lib.get_consistent_name(episode["name"]),
        "type": "asset"})

    # Encode and store the Gazu Id and Avalon Id
    lib.set_asset_data(project["id"], data["episode_id"], avalon_episode["_id"])

    db.uninstall()

    logger.info("Create Episode \"{0}\" in Project \"{1}\"".format(
        episode["name"], project["name"]))


def sequence_new_callback(data):
    """
    On receiving a sequence:new event, add a sequence to the Avalon
    mongodb.
    """

    # Log in to API
    gazu.client.set_host("{0}/api".format(os.environ["GAZU_URL"]))
    gazu.log_in(os.environ["GAZU_USER"], os.environ["GAZU_PASSWD"])

    sequence = gazu.shot.get_sequence(data["sequence_id"])
    project = gazu.project.get_project(sequence["project_id"])

    if project["production_type"] == "tvshow":
        project_name = lib.get_consistent_name(project["name"])
        episode_name = lib.get_consistent_name(sequence["episode_name"])
        sequence_name = lib.get_consistent_name(sequence["name"])
        visualParent = [project_name, episode_name]

        os.environ["AVALON_PROJECT"] = project_name

        db.uninstall()
        db.install()

        sequence_data = {
            "schema": "avalon-core:asset-2.0",
            "name": "{0}_{1}".format(episode_name, sequence_name),
            "silo": "shots",
            "type": "asset",
            "parent": db.locate([project_name]),
            "data": {
                "label": sequence["name"].upper(),
                "group": sequence["episode_name"].upper()
            }
        }

        sequence_data["data"]["visible"] = False
        sequence_data["data"]["visualParent"] = db.locate(visualParent)
    else:
        project_name = lib.get_consistent_name(project["name"])
        sequence_name = lib.get_consistent_name(sequence["name"])

        os.environ["AVALON_PROJECT"] = project_name

        db.uninstall()
        db.install()

        sequence_data = {
            "schema": "avalon-core:asset-2.0",
            "name": "{0}".format(sequence_name),
            "silo": "shots",
            "type": "asset",
            "parent": db.locate([project_name]),
            "data": {
                "label": sequence["name"].upper(),
                "group": "Sequence"
            }
        }
        sequence_data["data"]["visible"] = False

    # Inset asset into Avalon DB
    db.insert_one(sequence_data)

    # Get the Id of the asset we just inserted into Avalon
    avalon_sequence = db.find_one({
        "name": lib.get_consistent_name(sequence_data["name"]),
        "type": "asset"})

    # Encode and store the Gazu Id and Avalon Id
    lib.set_asset_data(project["id"], data["sequence_id"], avalon_sequence["_id"])

    db.uninstall()

    logger.info("Create Sequence \"{0}\" in Project \"{1}\"".format(
        sequence_data["name"], project["name"]))


# Init Logging
logger = lib.init_logging("event_listener")

# Init Gazu
gazu.client.set_host(os.environ["GAZU_URL"])
event_client = gazu.events.init()

# Asset Event Types
gazu.events.add_listener(event_client, "asset:create", asset_create_callback)
gazu.events.add_listener(event_client, "asset:update", asset_update_callback)

# Project Event Types
gazu.events.add_listener(event_client, "project:new", project_new_callback)
gazu.events.add_listener(event_client, "project:update", project_update_callback)

# Shot Event Types
gazu.events.add_listener(event_client, "shot:new", shot_new_callback)
gazu.events.add_listener(event_client, "shot:update", shot_update_callback)

# Task Event Types
gazu.events.add_listener(event_client, "task:new", task_new_callback)

# Episode Event Types
gazu.events.add_listener(event_client, "episode:new", episode_new_callback)

# Sequence Event Types
gazu.events.add_listener(event_client, "sequence:new", sequence_new_callback)


gazu.events.run_client(event_client)
