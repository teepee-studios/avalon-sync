# Avalon Sync

## Warning: DO NOT USE IN PRODUCTION
This Avalon Sync utils are still in heavy development and have not been fully tested.


Avalon Sync uses Gazu to sync Zou to Avalon via the Kitsu API.  
Some important notes are:  
* Syncing is only **one** direction, Zou/Kitsu -> to Avalon.  
* Only new things are **Added** to Avalon and **Update** existing things in Avalon.
* **Delete** events are *ignored*, nothing is deleted from Avalon (except for Tasks, 
due to the way they're stored in Avalon).
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
| Asset Update | X | X |
| Asset Delete | - | - |
| Shot New | X | X |
| Shot Update | X | X |
| Shot Delete | - | - |
| Sequence New | O | X |
| Sequence Update | O | X |
| Sequence Delete | - | - |
| Episode New | O | X |
| Episode Update | O | X |
| Episode Delete | - | - |
| Task New | X | X |
| Task Update | O | X |
| Task Delete | O | X |
| Task Type New | O | X |
| Task Type Update | O | X |
| Task Type Delete | O | - |

Cells with X are supported Action Types.  
Cells with O are not needed or can't be handled by that script.
Blank cells are Action Types that are not yet supported.  
Cells with - are Action Types that will not be supported.  

<details>
<summary>
The following additional Gazu API events are not supported as Avalon doesn't need 
to know about them currently:
</summary>



- Breakdown  
- Tasks  
- Comments  
- Previews
- Playlists
- People
- Asset Type
- Task Status
- Settings
- Custom Actions


</details>

## How to use:

You will need Avalon, Gazu, pymongo and partd installed, as well as a running 
Kitsu/Zou instance.

### Windows 10

#### Requirements: 
- Python 3.6+  
- [Avalon](https://getavalon.github.io)  
- [gazu](https://pypi.org/project/gazu)  
- [pymongo](https://pypi.org/project/pymongo)  
- [partd](https://pypi.org/project/partd)  
- See [CGWire](https://www.cg-wire.com/) for more information about kitsu/zou
and/or check out their [GitHub](https://github.com/cgwire)  


#### Example bat file to run the scripts:

```bat
@echo off
set PYTHONPATH=Q:\path\to\your\studio-config;%PYTHONPATH%
set PYTHONPATH=Q:\path\to\avalon-core;%PYTHONPATH%
set AVALON_MONGO=mongodb://username:password@mongodb.host.name:27017/databaseName
set AVALON_DB=databaseName
set MONGO_TIMEOUT=5000
set AVALON_PROJECTS=Z:/path/to/avalon/projects
set AVALON_CONFIG=teepee
set DATA_PATH=Q:\path\to\avalon-sync
set LOG_LEVEL=INFO
set GAZU_URL=http://kitsu.hostname
set GAZU_USER=api.username@for.kitsu.com
set GAZU_PASSWD=password
python %*

```
Put the above in run.bat and edit it to match your environment, then you can do: 
`run db_sync.py` or `run event_listener.py`

### Linux:

#### Requirements: 
- Python 3.6+  
- [Avalon](https://getavalon.github.io)  
- [gazu](https://pypi.org/project/gazu)  
- [pymongo](https://pypi.org/project/pymongo)  
- [partd](https://pypi.org/project/partd)  
- See [CGWire](https://www.cg-wire.com/) for more information about kitsu/zou 
and/or check out their [GitHub](https://github.com/cgwire)  


#### Example testing bash file to run the scripts:


```bash
#!/bin/bash

export PYTHONPATH=/opt/avalon-sync/avalon:$PYTHONPATH
export AVALON_MONGO=mongodb://username:password@mongodb.host.name:27017/databaseName
export AVALON_DB=databaseName
export MONGO_TIMEOUT=5000
export AVALON_PROJECTS=Z:/avalonTest
export DATA_PATH=/opt/avalon-sync
export LOG_LEVEL=INFO
export GAZU_URL=http://kitsu.hostname
export GAZU_USER=api.username@for.kitsu.com
export GAZU_PASSWD=password

python3 $*
```

Put the above in a file called 'run' in the bin folder and edit it to match your 
environment, then you can do: `run db_sync.py` or `run event_listener.py`


## Linux Installation

This section will cover how to install these scripts as services under Fedora 29+ 
and should also work for Centos 8 when it's released.

*Replace `vi` with text editor of choice!*  

#### Add User
Add a user for Avalon Sync:
```bash
sudo adduser -d /opt/avalon-sync -m avalon-sync
```
Switch to the avalon-sync user and clone Avalon Sync git to the bin directory:
```bash
sudo su - avalon-sync
git clone http://gitlab.teepee/avalon/avalon-sync.git bin
```
Clone Avalon Core git to the avalon directory:
```bash
git clone https://github.com/getavalon/core.git avalon
```
Create the config file:
```bash
mkdir etc
cd etc/
vi avalon-sync.conf
```
#### Config File
avalon-sync.conf should contain the following modified to match your environment's details:
```
PYTHONPATH=/opt/avalon-sync/avalon:$PYTHONPATH
AVALON_MONGO=mongodb://username:password@mongodb.host.name:27017/databaseName
AVALON_DB=databaseName
MONGO_TIMEOUT=5000
AVALON_PROJECTS=Z:/avalonTest
DATA_PATH=/opt/avalon-sync
LOG_LEVEL=INFO
GAZU_URL=http://kitsu.hostname
GAZU_USER=api.username@for.kitsu.com
GAZU_PASSWD=password
```
`logout` of the avalon-sync user or `ctrl-d`  

Install required python modules:  
partd and pymongo can be installed by either pip **OR** dnf:
```bash
sudo pip3 install partd
sudo pip3 install pymongo

```
**OR**:
```bash
sudo dnf install python3-partd python3-pymongo
```
Install gazu:
```bash
sudo pip3 install gazu
```

#### db_sync systemd Service File

Create the Avalon Sync systemd service file:
```bash
sudo vi /etc/systemd/system/avalon-sync-dbsync.service
```

avalon-sync-dbsync.service should contain:
```bash
[Unit]
Description=Avalon Sync DB
Wants=avalon-sync-dbsync.timer

[Service]
User=avalon-sync
Group=avalon-sync
Type=simple
WorkingDirectory=/opt/avalon-sync/bin
EnvironmentFile=/opt/avalon-sync/etc/avalon-sync.conf
ExecStart=/usr/bin/python3 /opt/avalon-sync/bin/db_sync.py

[Install]
WantedBy=multi-user.target
```
#### db_sync systemd Timer File

Create the Avalon Sync systemd timer file:
```bash
sudo vi /etc/systemd/system/avalon-sync-dbsync.timer
```
avalon-sync-dbsync.timer should contain:
```bash
[Unit]
Description=Avalon Sync DB timer
Requires=avalon-sync-dbsync.service

[Timer]
OnCalendar=*-*-* *:5:00

[Install]
WantedBy=timers.target

```
In the above `[Timer]` section the **OnCalendar** setting can be modified to make 
the script run at set times, for example once a day at 3am or every hour, etc. 
In the above example it's set to run 5 minutes past the hour, every hour, every day.  

It is also possible to make the timer run every 15 minutes, by replacing the 
`[Timer]` section. The setting **OnUnitInactiveSec** will run the timer if the 
timer last ran more than 15 minutes ago, this is useful if your timer takes 
longer than 15 minutes to run. Additionally you can add a random delay using 
**RandomizedDelaySec**, in the example bellow, the timer runs every 15 
minutes + some random duration below 15 minutes:
```bash
[Timer]
OnUnitInactiveSec=15m
RandomizedDelaySec=15m
```
**More information** can be found in the [systemd Timer unit documentation](https://www.freedesktop.org/software/systemd/man/systemd.timer.html)

>  *You could also run db_sync.py from cron if you wished, although that is not covered here.*  

#### event_listener Service File

*The following is **optional**, it's possible to **not** run the event listener 
script if you don't want live updates and only want to sync when the timer runs.*


```bash
sudo vi /etc/systemd/system/avalon-sync-listener.service
```
avalon-sync-listener.service should contain:
```bash
[Unit]
Description=Avalon Sync Event Listener
After=multi-user.target

[Service]
User=avalon-sync
Group=avalon-sync
Type=simple
WorkingDirectory=/opt/avalon-sync/bin
EnvironmentFile=/opt/avalon-sync/etc/avalon-sync.conf
ExecStart=/usr/bin/python3 /opt/avalon-sync/bin/event_listener.py

[Install]
WantedBy=multi-user.target
```
#### Resource control of scripts
While these scripts don't use a lot of resources or take very long to run on small 
setups, for larger setups or servers with limited resources, you might like to control 
what resources the Avalon Sync scripts can use.

<details>
<summary>Using systemd .slice files to control system resource usage</summary>
  
  
systemd can control system resource usage via it's [.slice](https://www.freedesktop.org/software/systemd/man/systemd.slice.html)
files, which in turn use Linux Control Group (cgroup).

```bash
sudo vi /etc/systemd/system/avalon-sync.slice
```
avalon-sync.slice should containt your [resource limits](https://www.freedesktop.org/software/systemd/man/systemd.resource-control.html):
```bash
[Unit]
Description=Avalon Sync resource limiter Slice
DefaultDependencies=no
Before=slices.target

[Slice]
CPUQuota=50%
MemoryLimit=1.2G
```
```bash
sudo vi /etc/systemd/system/avalon-sync-dbsync.service
```
Change avalon-sync-dbsync.service by adding `Slice=avalon-sync.slice` to the 
`[Service]` section, so that it looks like:
```bash
[Unit]
Description=Avalon Sync DB
Wants=avalon-sync-dbsync.timer

[Service]
User=avalon-sync
Group=avalon-sync
Type=simple
WorkingDirectory=/opt/avalon-sync/bin
EnvironmentFile=/opt/avalon-sync/etc/avalon-sync.conf
ExecStart=/usr/bin/python3 /opt/avalon-sync/bin/db_sync.py
Slice=avalon-sync.slice

[Install]
WantedBy=multi-user.target
```

```bash
sudo vi /etc/systemd/system/avalon-sync-listener.service
```

and `avalon-sync-listener.service` looks like:
```bash
[Unit]
Description=Avalon Sync Event Listener
After=multi-user.target

[Service]
User=avalon-sync
Group=avalon-sync
Type=simple
WorkingDirectory=/opt/avalon-sync/bin
EnvironmentFile=/opt/avalon-sync/etc/avalon-sync.conf
ExecStart=/usr/bin/python3 /opt/avalon-sync/bin/event_listener.py
Slice=avalon-sync.slice

[Install]
WantedBy=multi-user.target
```
The above will limit the Avalon Sync scripts to collectively never use more than 50% of the CPU or more than 1.2G of the RAM on your server.

</details>

#### Running the services
Reload systemd and enable & start the db_sync timer:
```bash
sudo systemctl daemon-reload
sudo systemctl enable avalon-sync-dbsync.timer
sudo systemctl start avalon-sync-dbsync.timer
```
Before continuing a complete database sync has to be run via db_sync. This can 
either be via the timer or run manually using the above bash script.

Enable and start the listener service:
```bash
sudo systemctl enable avalon-sync-listener.service
sudo systemctl start avalon-sync-listener.service
```