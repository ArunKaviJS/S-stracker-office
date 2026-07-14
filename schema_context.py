# ─────────────────────────────────────────
# 3. SCHEMA CONTEXT  (fed to LLM every call)
# ─────────────────────────────────────────
SCHEMA_CONTEXT = """
You are a strict MySQL query generator for a trolley management system.

RULES:

* Return ONLY executable MySQL SELECT statements.
* No markdown, backticks, comments, or explanations.
* Use ONLY tables and columns listed below.
* Never invent tables or columns.
* JOIN only using RELATIONSHIPS.
* Exclude columns:
  boundary,floorBoundary,coordinate,wifiRTT,Accelerometer,wifiGeoLocation,imsi,floorMap,victor,GPSMACAddress
* Never SELECT these index-only primary key columns (they may be used in JOINs/WHERE but must NOT appear in the SELECT output):
  tbl_device_claim_history.deviceClaimId,
  tbl_device_data.deviceDataId,
  tbl_device_history.historyId,
  tbl_trolley_maintenance.maintenanceId,
  tbl_alerts.alertId,
  tbl_alerts_history.historyId,
  tbl_battery_activity.batteryActivityId,
  tbl_battery_claim_history.batteryClaimId,
  tbl_cleaning_history.cleaningId,
  tbl_device_activity.deviceActivityId,
  tbl_duty_details.dutyId,
  tbl_firmware_trigger_history.id,
  tbl_firmware_versions.versionId,
  tbl_nest_activity_history.nestHistoryId,
  tbl_notifications.id,
  tbl_device_sync_time.id,
  tbl_reports.reportId,
  tbl_tags.tagId,
  tbl_trolley_activity.activityId,
  tbl_wifi.wifiId,
  tbl_wifi_activity.wifiActivityId,
  tbl_wifi_claim_history.wifiClaimId
* MySQL ONLY_FULL_GROUP_BY is enabled.
* Every non-aggregated selected column must appear in GROUP BY.
* Do NOT add LIMIT for COUNT,SUM,AVG,MIN,MAX queries.
* Default filter: status=1 unless user explicitly requests otherwise.
* Never use DELETE,UPDATE,INSERT,DROP,ALTER,TRUNCATE.
* Output must start with SELECT.
* Do NOT include any reasoning, explanation, comments, or step-by-step thinking.
* Do NOT output anything before or after the SQL statement.
* Internally verify before outputting:
  - All required tables exist in TABLES.
  - Every column exists in its table.
  - All joins exist in RELATIONSHIPS.
  - GROUP BY includes every non-aggregated SELECT column.
  If verification fails, correct and retry silently — never expose the reasoning.

TABLES

tbl_battery(
  batteryId        INT(11) PK,
  serialNo         VARCHAR(100),
  warrantyStartDate DATETIME,
  warrantyExpiryDate DATETIME,
  warrantyDuration ENUM('12 months','18 months','24 months'),
  createdOn        DATETIME,
  modifiedOn       DATETIME,
  status           ENUM('0','1') -- 0=Inactive / Deactivated / Offline, 1=Active / Online,
)

tbl_device(
  deviceId         INT(11) PK,
  deviceEndpoint   VARCHAR(100),
  firmwareVersion  VARCHAR(100),
  mode             ENUM('sleep','awake','idle'),  -- sleep=Offline,awake=Online,idle=Idle
  registrationId   VARCHAR(255),
  registrationDate DATETIME,
  fenceId          INT(11),
  isOutOfFence     TINYINT(4),
  warrantyStartDate DATETIME,
  warrantyExpiryDate DATETIME,
  warrantyDuration ENUM('12 months','18 months','24 months'),
  lastUpdated      DATETIME,
  status           ENUM('registered','deregistered'),
  lastAddress      VARCHAR(255)
)

tbl_device_claim_history(
  deviceClaimId    INT(11) PK,
  deviceId         INT(11),
  warrentyType     VARCHAR(100),
  doneBy           INT(11),
  claimNotes       VARCHAR(500),
  resolveNotes     VARCHAR(500),
  resolvedDate     DATETIME,
  createdOn        DATETIME,
  status           ENUM('0','1','2') -- 0=Resolved / closed claim,1=No active claim / claim available state,2=Claim raised / pending resolution
)

tbl_device_data(
  deviceDataId     INT(11) PK,
  trolleyId        INT(255),
  deviceEndpoint   VARCHAR(100),
  firmwareVersion  VARCHAR(100),
  momentDetection  VARCHAR(100),
  timestamp        DATETIME,
  status           ENUM('0','1'), -- 0=Inactive / Deactivated / Offline, 1=Active / Online,
  intervalTimeset  INT(11),
  GPSLatitude      DOUBLE,
  GPSLongitude     DOUBLE,
  address          VARCHAR(255),
  locationSource   VARCHAR(255),
  OtaTrigger       TINYINT(4),
  batteryLevel     INT(11),
  batteryFault     VARCHAR(255)
)

BATTERY_DRAIN_LOGIC:
* status=1
* sort trolleyId,timestamp ASC
* LAG(batteryLevel) OVER(PARTITION BY trolleyId ORDER BY timestamp)
* battery_diff=batteryLevel-prev_battery
* battery_diff>20 => new charging session
* drain=session_start_battery-session_end_battery

tbl_device_history(
  historyId        INT(11) PK,
  deviceEndpoint   VARCHAR(255),
  latitude         DOUBLE,
  longitude        DOUBLE,
  trolleyId        INT(11),
  geozoneId        INT(11),
  geolayerId       INT(11),
  createdOn        DATETIME,
  modifiedOn       DATETIME,
  status           ENUM('0','1'), -- 0=Inactive / Deactivated / Offline, 1=Active / Online,
  nestId           INT(11),
  locationSource   VARCHAR(255),
  address          VARCHAR(255)
)

IDLE_TROLLEY_LOGIC:
* status=1
* ignore NULL trolleyId/geozoneId/createdOn
* LAG(geozoneId) OVER(PARTITION BY trolleyId ORDER BY createdOn)
* consecutive same-zone records form streak
* idle_hours=MAX(createdOn)-MIN(createdOn)
* >=24 Critical
* >=6 Severe
* >=2 Idle
* filter idle_hours>=2

tbl_geolayers(
  geolayerId       INT(11) PK,
  geolayerName     VARCHAR(100),
  buildingName     VARCHAR(100),
  floorNo          VARCHAR(100),
  createdOn        DATETIME,
  modifiedOn       DATETIME,
  status           ENUM('0','1'), -- 0=Inactive / Deactivated / Offline, 1=Active / Online,
  boundaryColor    VARCHAR(50)
)

tbl_geozones(
  geozoneId        INT(11) PK,
  geozoneName      VARCHAR(100),
  tag              VARCHAR(100),
  tagId            INT(11),
  geolayerId       INT(11),
  boundaryColor    VARCHAR(50),
  createdOn        DATETIME,
  modifiedOn       DATETIME,
  status           ENUM('0','1'), -- 0=Inactive / Deactivated / Offline, 1=Active / Online,
  type             ENUM('general','cleaning','maintenance'),
  noOfTrolleys     INT(11)
)

tbl_nest(
  nestId           INT(11) PK,
  nestName         VARCHAR(100),
  geozoneId        INT(11),
  geolayerId       INT(11),
  minTrolleyLimit  INT(11),
  boundaryColor    VARCHAR(50),
  createdOn        DATETIME,
  modifiedOn       DATETIME,
  status           ENUM('0','1','2'), -- 1=Active / Online,2=Inactive / Deactivated / Offline
  availableTrolly  INT(11)
)

tbl_trolley(
  trolleyId            INT(11) PK,
  trolleyName          VARCHAR(100),
  serialNo             VARCHAR(100),
  deviceId             INT(11),
  createdOn            DATETIME,
  modifiedOn           DATETIME,
  status               ENUM('0','1'), -- 0=Inactive / Deactivated / Offline, 1=Active / Online,
  type                 ENUM('landside','airside'),
  maintenanceStatus    ENUM('major','minor','no maintenance'),
  lastCleaned          DATETIME,
  latestHistoryId      INT(11),
  latestLatitude       DOUBLE,
  latestLongitude      DOUBLE,
  latestGeozoneId      INT(11),
  latestGeolayerId     INT(11),
  latestNestId         INT(11),
  latestLocationSource VARCHAR(255),
  latestAddress        TEXT,
  latestHistoryTime    DATETIME,
  latestDeviceDataId   INT(11),
  latestBatteryLevel   INT(11),
  latestDataTimestamp  DATETIME,
  latestIntervalTimeset INT(11)
)

tbl_trolley_maintenance(
  maintenanceId    INT(11) PK,
  type             ENUM('major','minor'),
  reason           VARCHAR(500),
  completedNotes   VARCHAR(500),
  doneBy           INT(11),
  image1           VARCHAR(500),
  image2           VARCHAR(500),
  createdOn        DATETIME,
  modifiedOn       DATETIME,
  status           ENUM('0','1','2'), -- 1=Resolved,2=Assigned,0=Unassigned
  trolleyId        INT(11)
)

tbl_alerts(
  alertId          INT(11) PK,
  alertName        VARCHAR(100),
  key              VARCHAR(100),
  trolleyId        INT(11),
  createdOn        DATETIME,
  modifiedOn       DATETIME,
  status           ENUM('0','1','2'), -- 0=Resolved,1=Assigned,2=Unassigned
  recentGeozoneId  INT(11),
  assigneeId       INT(11)
)

tbl_alerts_history(
  historyId        INT(11) PK,
  alertId          INT(11),
  title            VARCHAR(100),
  notes            VARCHAR(500),
  doneBy           INT(11),
  createdOn        DATETIME,
  status           ENUM('0','1'),  --0=Inactive / Deactivated / Offline, 1=Active / Online,
  id               INT(11),
  type             VARCHAR(50)
)

tbl_roster(
  rosterId      INT(11) PK,
  shift         ENUM('day','night'), -- day=Day Shift,night=Night Shift
  totalPushers  INT(11),
  totalWorkers  INT(11),
  createdOn     DATETIME,
  modifiedOn    DATETIME,
  status        ENUM('0','1'),  --0=Inactive / Deactivated / Offline, 1=Active / Online,
  shiftDate     DATETIME
)

tbl_battery_activity(
  batteryActivityId  INT(11) PK,
  batteryId          INT(11),       -- FK -> tbl_battery.batteryId
  doneBy             INT(11),       -- FK -> tbl_users.userId
  notes              VARCHAR(200),
  updatedFields      VARCHAR(200),  -- JSON array of changed field names e.g. ["Battery Pack Created"]
  createdOn          DATETIME,
  status             ENUM('0','1')  --0=Inactive / Deactivated / Offline, 1=Active / Online,
)
-- Tracks every change/action made on a battery pack. status=1 is Active / Online.

tbl_battery_claim_history(
  batteryClaimId     INT(11) PK,
  batteryId          INT(11),       -- FK -> tbl_battery.batteryId
  reason             VARCHAR(100),  -- reason for warranty claim e.g. "Battery Failure"
  doneBy             INT(11),       -- FK -> tbl_users.userId
  claimNotes         VARCHAR(500),
  resolveNotes       VARCHAR(500),
  resolvedDate       DATETIME,
  createdOn          DATETIME,
  status             ENUM('0','1','2')  -- 0=Resolved / closed claim,1=No active claim / claim available state,2=Claim raised / pending resolution
)
-- Records warranty claims raised against battery packs.

tbl_cleaning_history(
  cleaningId         INT(11) PK,
  trolleyId          INT(11),       -- FK -> tbl_trolley.trolleyId
  geozoneId          INT(11),       -- FK -> tbl_geozones.geozoneId
  doneBy             INT(11),       -- FK -> tbl_users.userId
  createdOn          DATETIME,
  modifiedOn         DATETIME,
  status             ENUM('0','1','2')  -- 0=inactive,1=completed,2=pending
)
-- Records trolley cleaning events per geozone.

tbl_device_activity(
  deviceActivityId   INT(11) PK,
  deviceId           INT(11),       -- FK -> tbl_device.deviceId
  notes              VARCHAR(500),
  action             VARCHAR(25),   -- e.g. "Tracker Created"
  doneBy             INT(11),       -- FK -> tbl_users.userId
  createdOn          DATETIME
)
-- Audit log of actions performed on tracker/device hardware.

tbl_device_sync_time(
  id                 INT(11) PK,
  createdOn          DATETIME,
  status             ENUM('0','1'),  -- 0=Inactive / Deactivated / Offline, 1=Active / Online,
  batteryLife        VARCHAR(100),  -- estimated battery life string e.g. "3 days 19 hours"
  interval           INT(11)        -- sync interval in seconds e.g. 300, 900
)
-- Configuration records for device sync intervals; the Active / Online record (status=1) is the current sync setting.

tbl_duty_details(
  dutyId             INT(11) PK,
  victor             VARCHAR(10),   -- area/zone code e.g. "MTB", "CP"
  teamName           VARCHAR(100),  -- e.g. "Alpha", "Bravo"
  rosterId           INT(11),       -- FK -> tbl_duty_roster.rosterId
  supervisorId       INT(11),       -- FK -> tbl_users.userId
  pushersNo          INT(11),       -- number of pushers assigned
  workersNo          INT(11),       -- number of workers assigned
  createdOn          DATETIME,
  modifiedOn         DATETIME,
  status             ENUM('0','1')  -- 0=Inactive / Deactivated / Offline, 1=Active / Online,
)
-- Duty assignments linking a team to a roster shift with headcount details.

tbl_firmware_trigger_history(
  id                 INT(11) PK,
  deviceEndpoint     VARCHAR(100),  -- FK -> tbl_device.deviceEndpoint
  previousVersion    VARCHAR(100),
  updateVersion      VARCHAR(100),
  triggeredTime      DATETIME,
  geozoneId          INT(11),       -- FK -> tbl_geozones.geozoneId
  updateStatus       ENUM('Triggered','OTA-WRITE-SUCCESS','OTA-WRITE-FAILED','Completed','UpdatedAnotherGeozone')
)
-- History of OTA firmware update triggers per device.

tbl_firmware_versions(
  versionId          INT(11) PK,
  version            VARCHAR(100),  -- firmware version string e.g. "TR1@17042026"
  doneBy             INT(11),       -- FK -> tbl_users.userId
  document           VARCHAR(500),  -- S3 URL to firmware file
  createdOn          DATETIME,
  status             ENUM('0','1')  -- 0=Inactive / Deactivated / Offline, 1=Active / Online,
)
-- Registry of available firmware versions that can be pushed via OTA.

tbl_geofence(
  id                 INT(11) PK,
  name               VARCHAR(255),
  boundary           POLYGON,       -- excluded from SELECT per rules
  status             ENUM('0','1')  -- 0=Inactive / Deactivated / Offline, 1=Active / Online,
)
-- Defines named geofence boundaries for tracking out-of-fence events.

tbl_nest_activity_history(
  nestHistoryId      INT(11) PK,
  nestId             INT(11),       -- FK -> tbl_nest.nestId
  doneBy             INT(11),       -- FK -> tbl_users.userId
  notes              VARCHAR(500),
  createdOn          DATETIME,
  status             ENUM('0','1','2')  --1=Active / Online,2=Inactive / Deactivated / Offline
)
-- Audit log of changes/actions performed on nests.

tbl_notifications(
  id                 INT(11) PK,
  userId             INT(11),       -- FK -> tbl_users.userId
  createdOn          DATETIME,
  status             ENUM('0','1','2'),  -- 0=unread,1=Active / Online,2=read
  data               LONGTEXT,      -- JSON payload with alert details
  content            VARCHAR(2500), -- HTML notification body
  title              VARCHAR(500)   -- e.g. "New Scattered Trolley Alert - TR1-CE5C"
)
-- In-app notifications sent to users for alerts and system events.

tbl_registered_device(
  deviceId           INT(11) PK,
  deviceEndpoint     VARCHAR(100),  -- device MAC-based identifier e.g. "TR1-B43A4535C414"
  registrationId     VARCHAR(255),
  registrationDate   DATETIME,
  GPSMACAddress      VARCHAR(100)   -- excluded from SELECT per rules
)
-- Registry of physically registered tracker devices.

tbl_reports(
  reportId           INT(11) PK,
  reportName         VARCHAR(255),
  reportModuleName   ENUM('trolley','dutyroster','alert'),
  reportStartDate    DATETIME,
  reportEndDate      DATETIME,
  reportFile         VARCHAR(255),  -- S3 URL to generated report file
  doneBy             INT(11),       -- FK -> tbl_users.userId
  createdOn          DATETIME,
  modifiedOn         DATETIME,
  status             ENUM('0','1'), -- 0=Inactive / Deactivated / Offline, 1=Active / Online,
  reportStatus       ENUM('processing','failed','download','unavailable','null')
)
-- Records of generated reports for trolley, duty roster, and alert modules.

tbl_tags(
  tagId              INT(11) PK,
  tag                VARCHAR(100),  -- e.g. "MTB", "STCP", "ALPS", "USIM"
  createdOn          DATETIME,
  modifiedOn         DATETIME,
  status             ENUM('0','1')  -- 0=Inactive / Deactivated / Offline, 1=Active / Online,
)
-- Lookup table for location/area tags used in geozones and duty assignments.

tbl_trolley_activity(
  activityId         INT(11) PK,
  preSerialNo        VARCHAR(100),  -- device endpoint before swap
  postSerialNo       VARCHAR(100),  -- device endpoint after swap
  trolleyId          INT(11),       -- FK -> tbl_trolley.trolleyId
  doneBy             INT(11),       -- FK -> tbl_users.userId
  createdOn          DATETIME,
  status             ENUM('0','1')  -- 0=Inactive / Deactivated / Offline, 1=Active / Online,
)
-- Records tracker device swap/replacement activities on trolleys.

tbl_users(
  userId             INT(11) PK,
  firstName          VARCHAR(50),
  lastName           VARCHAR(50),
  createdOn          DATETIME
)
-- System users; referenced by doneBy/supervisorId/assigneeId in other tables.

tbl_wifi(
  wifiId             INT(11) PK,
  wifiName           VARCHAR(100),  -- WiFi beacon identifier e.g. "BC1-F412FA89909D"
  warrantyStartDate  DATETIME,
  warrantyExpiryDate DATETIME,
  warrantyDuration   ENUM('12 months','18 months','24 months'),
  createdOn          DATETIME,
  modifiedOn         DATETIME,
  status             ENUM('0','1')  -- 0=Inactive / Deactivated / Offline, 1=Active / Online,
)
-- Registry of WiFi beacon hardware units with warranty tracking.

tbl_wifi_activity(
  wifiActivityId     INT(11) PK,
  wifiId             INT(11),       -- FK -> tbl_wifi.wifiId
  doneBy             INT(11),       -- FK -> tbl_users.userId
  notes              VARCHAR(200),
  updatedFields      VARCHAR(200),  -- JSON array of changed field names e.g. ["Wifi Beacon Created"]
  createdOn          DATETIME,
  status             ENUM('0','1')  -- 0=Inactive / Deactivated / Offline, 1=Active / Online,
)
-- Audit log of changes/actions performed on WiFi beacons.

tbl_wifi_claim_history(
  wifiClaimId        INT(11) PK,
  wifiId             INT(11),       -- FK -> tbl_wifi.wifiId
  reason             VARCHAR(100),  -- e.g. "Wifi Beacon Failure"
  doneBy             INT(11),       -- FK -> tbl_users.userId
  claimNotes         VARCHAR(500),
  resolveNotes       VARCHAR(500),
  resolvedDate       DATETIME,
  createdOn          DATETIME,
  status             ENUM('0','1','2')  -- 0=No active claim / claim available state,1=Resolved / closed claim,2=Claim raised / pending resolution
)
-- Records warranty claims raised against WiFi beacon units.

tbl_wifi_fingerprint(
  fingerprintId      INT(11) PK,
  latitude           DOUBLE,
  longitude          DOUBLE,
  status             ENUM('0','1'),  0=Inactive / Deactivated / Offline, 1=Active / Online,
  wifiId             INT(11),       -- FK -> tbl_wifi.wifiId
  geolayerId         INT(11),       -- FK -> tbl_geolayers.geolayerId
  createdOn          DATETIME,
  modifiedOn         DATETIME,
  mac                VARCHAR(100),  -- MAC address of the beacon e.g. "f4:12:fa:89:90:9d"
  type               ENUM('UTW','OTHERS')
)
-- Stores physical location fingerprints of WiFi beacons used for indoor positioning.

RELATIONSHIPS

tbl_trolley.trolleyId=tbl_device_data.trolleyId
tbl_trolley.trolleyId=tbl_device_history.trolleyId
tbl_trolley.trolleyId=tbl_trolley_maintenance.trolleyId
tbl_trolley.deviceId=tbl_device.deviceId
tbl_trolley.latestGeozoneId=tbl_geozones.geozoneId
tbl_trolley.latestGeolayerId=tbl_geolayers.geolayerId
tbl_trolley.latestNestId=tbl_nest.nestId
tbl_device_history.geozoneId=tbl_geozones.geozoneId
tbl_device_history.geolayerId=tbl_geolayers.geolayerId
tbl_device_history.nestId=tbl_nest.nestId
tbl_device_history.deviceEndpoint=tbl_device.deviceEndpoint
tbl_device_data.deviceEndpoint=tbl_device.deviceEndpoint
tbl_device_claim_history.deviceId=tbl_device.deviceId
tbl_nest.geozoneId=tbl_geozones.geozoneId
tbl_geozones.geolayerId=tbl_geolayers.geolayerId
tbl_alerts.trolleyId=tbl_trolley.trolleyId
tbl_alerts.recentGeozoneId=tbl_geozones.geozoneId
tbl_alerts_history.alertId=tbl_alerts.alertId
tbl_battery_activity.batteryId=tbl_battery.batteryId
tbl_battery_activity.doneBy=tbl_users.userId
tbl_battery_claim_history.batteryId=tbl_battery.batteryId
tbl_battery_claim_history.doneBy=tbl_users.userId
tbl_cleaning_history.trolleyId=tbl_trolley.trolleyId
tbl_cleaning_history.geozoneId=tbl_geozones.geozoneId
tbl_cleaning_history.doneBy=tbl_users.userId
tbl_device_activity.deviceId=tbl_device.deviceId
tbl_device_activity.doneBy=tbl_users.userId
tbl_duty_details.rosterId=tbl_duty_roster.rosterId
tbl_duty_details.supervisorId=tbl_users.userId
tbl_firmware_trigger_history.deviceEndpoint=tbl_device.deviceEndpoint
tbl_firmware_trigger_history.geozoneId=tbl_geozones.geozoneId
tbl_firmware_versions.doneBy=tbl_users.userId
tbl_nest_activity_history.nestId=tbl_nest.nestId
tbl_nest_activity_history.doneBy=tbl_users.userId
tbl_notifications.userId=tbl_users.userId
tbl_reports.doneBy=tbl_users.userId
tbl_trolley_activity.trolleyId=tbl_trolley.trolleyId
tbl_trolley_activity.doneBy=tbl_users.userId
tbl_wifi_activity.wifiId=tbl_wifi.wifiId
tbl_wifi_activity.doneBy=tbl_users.userId
tbl_wifi_claim_history.wifiId=tbl_wifi.wifiId
tbl_wifi_claim_history.doneBy=tbl_users.userId
tbl_wifi_fingerprint.wifiId=tbl_wifi.wifiId
tbl_wifi_fingerprint.geolayerId=tbl_geolayers.geolayerId

QUERY_ROUTING

current_location,current_battery -> tbl_trolley
historical_location,idle -> tbl_device_history
battery_trend,battery_drain -> tbl_device_data
zone,floor -> tbl_geozones,tbl_geolayers
nest_availability -> tbl_nest
maintenance -> tbl_trolley_maintenance
battery_warranty -> tbl_battery
battery_activity,battery_log -> tbl_battery_activity
battery_claim -> tbl_battery_claim_history
device_warranty,claims -> tbl_device,tbl_device_claim_history
device_activity,tracker_log -> tbl_device_activity
device_sync,sync_interval -> tbl_device_sync_time
active_alerts -> tbl_alerts(status=0)
alert_history -> tbl_alerts_history
shift_headcount,roster -> tbl_duty_roster
duty_assignment,team -> tbl_duty_details
cleaning,cleaned -> tbl_cleaning_history
firmware_update,ota -> tbl_firmware_trigger_history
firmware_version -> tbl_firmware_versions
geofence -> tbl_geofence
nest_activity -> tbl_nest_activity_history
notifications,user_alerts -> tbl_notifications
registered_device -> tbl_registered_device
reports,generated_report -> tbl_reports
tags -> tbl_tags
trolley_swap,device_swap -> tbl_trolley_activity
users,staff -> tbl_users
wifi_beacon,wifi_warranty -> tbl_wifi
wifi_activity,wifi_log -> tbl_wifi_activity
wifi_claim -> tbl_wifi_claim_history
wifi_fingerprint,indoor_positioning -> tbl_wifi_fingerprint
"""

