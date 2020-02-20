import os
import sys
import time
import pymongo
import logging
import functools

from bson.objectid import ObjectId

__all__ = [
    "ObjectId",
    "install",
    "uninstall",
    "locate",
    "insert_one",
    "find_one",
    "replace_one",
]

self = sys.modules[__name__]
self._mongo_client = None
self._database = None
self._is_installed = False

log = logging.getLogger(__name__)

def install():
    """Establish a persistent connection to the database"""
    if self._is_installed:
        return

    log_handler = logging.StreamHandler()
    log.addHandler(log_handler)

    mongo_connection = os.environ["AVALON_MONGO"]
    database = os.environ["AVALON_DB"]
    timeout = int(os.getenv("MONGO_TIMEOUT", 5000))
    self._mongo_client = pymongo.MongoClient(mongo_connection, serverSelectionTimeoutMS=timeout)

    for retry in range(3):
        try:
            t1 = time.time()
            self._mongo_client.server_info()

        except Exception:
            log.error("Retrying..")
            time.sleep(1)
            timeout *= 1.5

        else:
            break

    else:
        raise IOError(
            "ERROR: Couldn't connect to %s in "
            "less than %.3f ms" % (mongo_connection, timeout))

    log.info("Connected to %s, delay %.3f s" % (
        mongo_connection, time.time() - t1))

    self._database = self._mongo_client[database]
    self._is_installed = True


def uninstall():
    """Close any connection to the database"""
    try:
        self._mongo_client.close()
    except AttributeError:
        pass

    self._mongo_client = None
    self._database = None
    self._is_installed = False


def auto_reconnect(f):
    """Handling auto reconnect in 3 retry times"""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        for retry in range(3):
            try:
                return f(*args, **kwargs)
            except pymongo.errors.AutoReconnect:
                log.error("Reconnecting..")
                time.sleep(0.1)
        else:
            raise

    return decorated


def locate(path):
    """Traverse a hierarchy from top-to-bottom

    Example:
        representation = locate(["hulk", "Bruce", "modelDefault", 1, "ma"])

    Returns:
        representation (ObjectId)

    """

    components = zip(
        ("project", "asset", "subset", "version", "representation"),
        path
    )

    parent = None
    for type_, name in components:
        latest = (type_ == "version") and name in (None, -1)

        try:
            if latest:
                parent = find_one(
                    filter={
                        "type": type_,
                        "parent": parent
                    },
                    projection={"_id": 1},
                    sort=[("name", -1)]
                )["_id"]
            else:
                parent = find_one(
                    filter={
                        "type": type_,
                        "name": name,
                        "parent": parent
                    },
                    projection={"_id": 1},
                )["_id"]

        except TypeError:
            return None

    return parent


@auto_reconnect
def insert_one(item):
    assert isinstance(item, dict), "item must be of type <dict>"
    return self._database[os.environ["AVALON_PROJECT"]].insert_one(item)


@auto_reconnect
def find_one(filter, projection=None, sort=None):
    assert isinstance(filter, dict), "filter must be <dict>"

    return self._database[os.environ["AVALON_PROJECT"]].find_one(
        filter=filter,
        projection=projection,
        sort=sort
    )


@auto_reconnect
def replace_one(filter, replacement):
    return self._database[os.environ["AVALON_PROJECT"]].replace_one(
        filter, replacement)


def collection_rename(filter, replacement):
    """Rename mongodb collection name.

    Renames the current collection to the supplied name."""
    return self._database[os.environ["AVALON_PROJECT"]].rename(
        filter, replacement)