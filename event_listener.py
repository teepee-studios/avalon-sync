import os
import gazu
import shutil

from avalon import io as avalon
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

    # Get the Id of the asset we just inserted into Avalon
    avalon_asset = avalon.find_one(
        {"name": lib.get_consistent_name(asset["name"]),
            "type": "asset"})

    # Encode and store the Gazu Id and Avalon Id
    lib.set_asset_data(project["id"], data["asset_id"], avalon_asset["_id"])

    avalon.uninstall()

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

    avalon.uninstall()
    avalon.install()

    # Get Avalon Asset Id.
    asset_id = lib.get_asset_data(project["id"], data["asset_id"])
    # Get asset Type
    entity_type = gazu.entity.get_entity_type(asset["entity_type_id"])

    # Find the asset in Avalon
    avalon_asset = avalon.find_one(
        {"_id": avalon.ObjectId(asset_id),
            "type": "asset"})

    # Set keep asset name for use in filesystem path renaming.
    old_asset_name = lib.get_consistent_name(avalon_asset["name"])

    # Ensure asset["name"] consistency.
    asset_name = lib.get_consistent_name(asset["name"])

    avalon_asset["name"] = asset_name
    avalon_asset["data"]["label"] = asset["name"]
    avalon_asset["data"]["group"] = entity_type["name"]

    avalon.replace_one(
        {"_id": avalon.ObjectId(asset_id), "type": "asset"}, avalon_asset)

    avalon.uninstall()

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

    avalon.uninstall()
    avalon.install()

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
    avalon.insert_one(project_data)

    # Find the project in Avalon
    avalon_project = avalon.find_one(
        {"name": lib.get_consistent_name(project["name"]),
            "type": "project"})

    # Encode and store the data
    lib.set_project_data(
        data["project_id"], avalon_project["_id"], avalon_project['name'])

    avalon.uninstall()

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

    avalon.uninstall()
    avalon.install()

    # Find the project in Avalon
    avalon_project = avalon.find_one(
        {"_id": avalon.ObjectId(project_data["id"]),
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

    avalon.replace_one(
        {"_id": avalon.ObjectId(project_data["id"]),
            "type": "project"}, avalon_project
    )

    avalon.uninstall()

    if old_project_name != project_name:
        logger.info("Updating project name from {0} to {1}".format(
            old_project_name, project_name))
        lib.collection_rename(project_name)

        lib.set_project_data(
            data["project_id"], avalon_project["_id"], avalon_project["name"])

        if(os.environ["FILESYS_RENAME"]):
            avalon_projects = os.environ["AVALON_PROJECTS"]

            old_folder_name = os.path.join(avalon_projects, old_project_name)

            new_folder_name = os.path.join(avalon_projects, project_name)

            if os.path.exists(old_folder_name):
                if not os.path.exists(new_folder_name):
                    logger.info("Project name updated, "
                                "renaming {0} to {1}".format(
                                    old_folder_name, new_folder_name))
                    shutil.move(old_folder_name, new_folder_name)
                else:
                    logger.warning(
                        "Project name updated, trying to "
                        "rename {0} to {1}, but new folder "
                        "already exists. No action taken"
                        .format(old_folder_name, new_folder_name)
                    )
            else:
                logger.warning(
                    "Project name updated, but {0} does not exist. No "
                    "action taken"
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

    project_name = lib.get_consistent_name(project["name"])
    episode_name = lib.get_consistent_name(shot["episode_name"])
    sequence_name = lib.get_consistent_name(shot["sequence_name"])
    shot_name = lib.get_consistent_name(shot["name"])
    visualParent = [project_name, "{0}_{1}".format(
        episode_name, sequence_name)]

    os.environ["AVALON_PROJECT"] = project_name

    avalon.uninstall()
    avalon.install()

    shot_data = {
        "schema": "avalon-core:asset-2.0",
        "name": "{0}_{1}_{2}".format(episode_name, sequence_name, shot_name),
        "silo": "shots",
        "type": "asset",
        "parent": avalon.locate([project_name]),
        "data": {
            "label": shot["name"],
            "group": "{0} {1}".format(
                shot["episode_name"].upper(),
                shot["sequence_name"].upper()),
            "visualParent": avalon.locate(visualParent)
        }
    }

    # Inset shot into Avalon DB
    avalon.insert_one(shot_data)

    # Get the Id of the shot we just inserted into Avalon
    avalon_shot = avalon.find_one(
        {"name": lib.get_consistent_name(shot_data["name"]),
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

    # Ensure name consistency.
    project_name = lib.get_consistent_name(project["name"])
    episode_name = lib.get_consistent_name(shot["episode_name"])
    sequence_name = lib.get_consistent_name(shot["sequence_name"])
    shot_name = lib.get_consistent_name(shot["name"])
    visualParent = [project_name, "{0}_{1}".format(
        episode_name, sequence_name)]

    os.environ["AVALON_PROJECT"] = project_name

    avalon.uninstall()
    avalon.install()

    # Get Avalon Shot Id.
    shot_id = lib.get_asset_data(project["id"], data["shot_id"])

    # Find the asset in Avalon
    avalon_shot = avalon.find_one(
        {"_id": avalon.ObjectId(shot_id),
            "type": "asset"})

    # Set keep shot name for use in filesystem path renaming.
    old_shot_name = lib.get_consistent_name(avalon_shot["name"])
    new_shot_name = "{0}_{1}_{2}".format(
        episode_name, sequence_name, shot_name)

    avalon_shot["name"] = new_shot_name
    avalon_shot["data"]["label"] = shot["name"]
    avalon_shot["data"]["group"] = "{0} {1}".format(
        shot["episode_name"].upper(), shot["sequence_name"].upper())
    avalon_shot["data"]["visualParent"] = avalon.locate(visualParent)

    if shot["data"] is not None:
        if "frame_in" in shot["data"]:
            avalon_shot["data"]["edit_in"] = shot["data"]["frame_in"]
            avalon_shot["data"]["startFrame"] = shot["data"]["frame_in"]
        if "frame_out" in shot["data"]:
            avalon_shot["data"]["edit_out"] = shot["data"]["frame_out"]
            avalon_shot["data"]["endFrame"] = shot["data"]["frame_out"]

    avalon.replace_one(
        {"_id": avalon.ObjectId(shot_id),
            "type": "asset"}, avalon_shot)

    avalon.uninstall()

    logger.info("Updated Shot \"{0}\" in Project \"{1}\"".format(
        avalon_shot["name"], project["name"]))

    if shot_name != old_shot_name:
        logger.info("Shot renamed from \"{0}\" to \"{1}\"".format(
            old_shot_name, new_shot_name))

    # If file system path renaming is enabled, rename asset disk
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

    avalon.uninstall()
    avalon.install()

    # Find the asset in Avalon
    avalon_entity = avalon.find_one(
        {"_id": avalon.ObjectId(entity_id),
            "type": "asset"})

    if avalon_entity["data"] is not None:
        if "tasks" in avalon_entity["data"]:
            avalon_entity["data"]["tasks"].append(task_name)
        else:
            avalon_entity["data"]["tasks"] = [task_name]
    else:
        avalon_entity["data"]["tasks"] = [task_name]

    avalon.replace_one(
        {"_id": avalon.ObjectId(entity_id), "type": "asset"}, avalon_entity)

    avalon.uninstall()

    logger.info("Added new \"{2}\" Task to \"{0}\" in Project \"{1}\"".format(
        avalon_entity["name"], project["name"], task_type["name"]))


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
gazu.events.add_listener(
    event_client, "project:update", project_update_callback)

# Shot Event Types
gazu.events.add_listener(event_client, "shot:new", shot_new_callback)
gazu.events.add_listener(event_client, "shot:update", shot_update_callback)

# Task Event Types
gazu.events.add_listener(event_client, "task:new", task_new_callback)


gazu.events.run_client(event_client)
