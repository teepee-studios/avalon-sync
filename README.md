# Avalon Sync

## Warning: DO NOT USE IN PRODUCTION
This Avalon Sync utils are still in heavy development and have not been fully tested.


Avalon Sync uses Gazu to sync Zou to Avalon via the Kitsu API.  
Some important notes are:  
* Syncing is only **one** direction, Zou/Kitsu -> to Avalon.  
* Only new things are **Added** to Avalon and **Update** existing things in Avalon.
* **Delete** events are *ignored*, nothing is deleted from Avalon.
* While added things *should* be done in Kitsu/Zou and then synced to Avalon, it's 
still possible add things via the Avalon Project manager, however if you later add 
the same thing to Kitsu, you will end up with **duplicates** in Avalon as Avalon 
Sync will know nothing about what has already been added to Avalon and will treat 
the newly added thing to Kitsu as not existing in Avalon.  


### Currently support actions


| Supported Actions | Event Listener | DB Syncer |
| ------ | :------: | :------: |
| Project New | X | X |
| Project Update | X | X |
| Project Delete | - | - |
| Asset New | X | X |
| Asset Update |  | X |
| Asset Delete | - | - |
| Shot New |  | X |
| Shot Update |  |  |
| Shot Delete | - | - |
| Sequence New |  | X |
| Sequence Update |  |  |
| Sequence Delete | - | - |
| Episode New |  | X |
| Episode Update |  |  |
| Episode Delete | - | - |
| Task Type New |  |  |
| Task Type Update |  |  |
| Task Type Delete |  |  |

Cells with X are supported Action Types.  
Blank cells are Action Types that are not yet supported.  
Cells with - are Action Types that will not be supported.  

<details>
<summary>
The following additional Gazu API events are not supported as Avalon doesn't need to know about them currently:
</summary>



- Breakdown  
- Tasks  
- Comments  
- Previews
- Playlists
- People
- Asset Type
- Task Status
- Task
- Settings
- Custom Actions


</details>

## How to use:

You will need Avalon, Gazu, pymongo and partd installed, as well as a running Kitsu/Zou instance.

**Requirements:** 
- Python 3.6+  
- [Avalon](https://getavalon.github.io)  
- `pip install gazu`  
- `pip install pymongo`  
- `pip install partd`  
- See [CGWire](https://www.cg-wire.com/) for more information about kitsu/zou and/or check out their [GitHub](https://github.com/cgwire)  



### Windows 10:

**Example bat file to run the scripts:**  

```
@echo off
set PYTHONPATH=Q:\path\to\your\studio-config;%PYTHONPATH%
set PYTHONPATH=Q:\path\to\avalon-core;%PYTHONPATH%
set AVALON_MONGO=mongodb://username:password@mongodb.host.name:27017/databaseName
set AVALON_DB=databaseName
set MONGO_TIMEOUT=5000
set AVALON_PROJECTS=Z:/path/to/avalon/projects
set AVALON_CONFIG=teepee
set PARTD_PATH=Q:\path\to\avalon-sync
set GAZU_URL=http://kitsu.hostname
set GAZU_USER=api.username@example.com
set GAZU_PASSWD=password
python %*

```
Put the above in run.bat and edit it to match your environment, then you can do: `run db_sync.py` or `run event_listener.py`

### Linux:
Coming soon...  
While this is being developed on Windows, we will be running it on our Kitsu/Zou Linux server once in production.


