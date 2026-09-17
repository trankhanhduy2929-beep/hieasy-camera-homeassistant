"""Constants for the HiEasy integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "hieasy"
NAME: Final = "HiEasy"
MANUFACTURER: Final = "Visioncop / HiEasy"

PLATFORMS: Final = (
    "binary_sensor",
    "button",
    "camera",
    "number",
    "select",
    "sensor",
    "switch",
)

APP_SN: Final = "4BED294759948BF1AF0F15AF3F09687C"
APP_VERSION: Final = "8.1.2"
APP_SOURCE: Final = 1
TOKEN_SECRET: Final = "Zw-Technology-eca2163200"

CONF_ACCOUNT: Final = "account"
CONF_REGION: Final = "region"
CONF_DISCOVER_LAN: Final = "discover_lan"
CONF_LAN_HOSTS: Final = "lan_hosts"
CONF_LAN_NETWORKS: Final = "lan_networks"
CONF_RTSP_PATHS: Final = "rtsp_paths"
CONF_RTSP_PORTS: Final = "rtsp_ports"
CONF_SCAN_PORTS: Final = "scan_ports"
CONF_SCAN_TIMEOUT: Final = "scan_timeout"
CONF_UPDATE_INTERVAL: Final = "update_interval"
CONF_MAX_SCAN_HOSTS: Final = "max_scan_hosts"

REGION_AUTO: Final = "auto"
REGION_WORLD: Final = "world"
REGION_AMERICA: Final = "america"
REGION_EUROPE: Final = "europe"
REGION_CHINA: Final = "china"
REGION_YL: Final = "yl"

REGION_ORDER: Final = (
    REGION_WORLD,
    REGION_AMERICA,
    REGION_EUROPE,
    REGION_CHINA,
    REGION_YL,
)

REGION_SERVERS: Final = {
    REGION_CHINA: (
        "https://erp-cn.p6sai.com/p6s",
        "/api/mgr/lite/v1",
        False,
    ),
    REGION_WORLD: (
        "https://erp-sgp.p6sai.com/p6s",
        "/api/mgr/lite/v1",
        False,
    ),
    REGION_EUROPE: (
        "https://p6storeworld-euro.p6sai.com:8089",
        "/p6scloud-server/api/v1/lite",
        True,
    ),
    REGION_AMERICA: (
        "https://p6storeworld-us.p6sai.com:8089",
        "/p6scloud-server/api/v1/lite",
        True,
    ),
    REGION_YL: (
        "https://p6sstore-pe-yl-1.pxyvision.com:8089",
        "/p6scloud-server/api/v1/lite",
        True,
    ),
}

LOGIN_PATH: Final = "/user-login"
DEVICE_LIST_PATH: Final = f"/safe/get-device-list/{APP_SN}"

DEFAULT_DISCOVER_LAN: Final = True
DEFAULT_SCAN_PORTS: Final = "80,81,8000,8080,8899"
DEFAULT_RTSP_PORTS: Final = "554,8554"
DEFAULT_RTSP_PATHS: Final = (
    "/live/ch{channel},/live/ch{channel}_{subtype},/stream{stream},"
    "/Streaming/Channels/{channel}0{stream},"
    "/cam/realmonitor?channel={channel}&subtype={subtype},"
    "/h264Preview_{channel02}_{profile}"
)
DEFAULT_SCAN_TIMEOUT: Final = 0.8
DEFAULT_MAX_SCAN_HOSTS: Final = 256
DEFAULT_UPDATE_INTERVAL: Final = 60
MIN_UPDATE_INTERVAL: Final = 30
MAX_UPDATE_INTERVAL: Final = 3600
DEFAULT_CLOUD_REFRESH: Final = timedelta(minutes=10)

ENDPOINT_NETWORK_PORT: Final = "/Network/Port"
ENDPOINT_DEVICE_INFO: Final = "/System/DeviceInfo"
ENDPOINT_RUNNING_INFO: Final = "/System/DeviceRunningInfo"
ENDPOINT_INDICATOR: Final = "/System/IndicatorLightCfg"
ENDPOINT_NIGHT_VISION: Final = "/System/DeviceNightVisionCfg"
ENDPOINT_LIGHT_CONTROL: Final = "/System/LightControlCfg"
ENDPOINT_PTZ_CAP: Final = "/System/PTZCap"
ENDPOINT_ALARM_OUT: Final = "/Alarm/AlarmOut"
ENDPOINT_REBOOT: Final = "/System/Reboot"

ENDPOINT_DEVICE_CAP: Final = "/System/DeviceCap"
ENDPOINT_AI_CAP: Final = "/System/AICap"
ENDPOINT_LIGHT_CAP: Final = "/System/LightCap"
ENDPOINT_WHITE_LIGHT: Final = "/System/WhiteLightEnable"
ENDPOINT_NIGHT_LED: Final = "/System/NightLedInfo"
ENDPOINT_ATMOSPHERE_LIGHT: Final = "/System/AtmosphereLightCfg"
ENDPOINT_AUDIO_STREAM: Final = "/Streams/AudioStream"
ENDPOINT_AUDIO_ALARM: Final = "/System/AudioAlarmConfig"
ENDPOINT_AUDIO_ALARM_V1: Final = "/System/1/AudioAlarmConfigV1"
ENDPOINT_VOICE_LIGHT_STATE: Final = "/Alarm/1/VoiceLightState"
ENDPOINT_ALARM_OUT_STATE: Final = "/System/AlarmoutState"
ENDPOINT_ONE_CLICK_ALARM_CFG: Final = "/Alarm/{channel}/OneClickAlarmCfg"
ENDPOINT_ONE_CLICK_ALARM_STATUS: Final = "/Alarm/{channel}/OneClickAlarmStatus"
ENDPOINT_ONE_CLICK_ALARM_CONTROL: Final = "/Alarm/{channel}/OneClickAlarmControl"
ENDPOINT_ALARM_SCHEDULE: Final = "/Alarm/{channel}/AlarmSchedule"
ENDPOINT_LIGHT_WARNING: Final = "/Alarm/{channel}/LightWarning"
ENDPOINT_VOICE_LIGHT_CONFIG: Final = "/Alarm/{channel}/VoiceLightConfig"
ENDPOINT_ALARM_OUT_SCHEDULE: Final = "/Alarm/AlarmOut/{channel}/Schedule"
ENDPOINT_POLYGON_CONFIG: Final = "/Alarm/{channel}/PolygonConfig"
ENDPOINT_POLYGON_SCHEDULE: Final = "/Alarm/{channel}/PolygonSchedule"
ENDPOINT_ALARM_OVERLAY: Final = "/Alarm/OverlayInfo"
ENDPOINT_ASSISTANT_IF: Final = "/System/1/AssistantInterfaceControl"
ENDPOINT_ARI_DECT: Final = "/System/AriDectAudioLightAlarm"
ENDPOINT_DND: Final = "/System/DoNotDisturbMode"
ENDPOINT_SLEEP_INFO: Final = "/System/DeviceSleepInfo"
ENDPOINT_SLEEP_CONTROL: Final = "/System/DeviceSleepControl"
ENDPOINT_POWER_CONFIG: Final = "/System/PowerConfig"
ENDPOINT_POWER_MANAGE: Final = "/System/DevicePowerManageCfg"
ENDPOINT_DIGITAL_ZOOM: Final = "/System/DeviceDigitalMultiple"
ENDPOINT_PUSH_INTERVAL: Final = "/System/{channel}/PushEventInterval"
ENDPOINT_INTERCOM_MODE: Final = "/System/DeviceIntercomMode"
ENDPOINT_TIME: Final = "/System/Time"
ENDPOINT_NTP: Final = "/System/NTP"
ENDPOINT_DISK: Final = "/Disk"
ENDPOINT_SD_FORMAT: Final = "/Record/Format/Call"
ENDPOINT_RECORD_SCHEDULE: Final = "/Record/{channel}/RecordScheduleV2"
ENDPOINT_EMAIL: Final = "/Network/Email"
ENDPOINT_FTP: Final = "/Network/FTP"
ENDPOINT_P2PV2: Final = "/Network/P2PV2"
ENDPOINT_4G_CARD: Final = "/Network/Interfaces/3/4GCardInfo"
ENDPOINT_SIM_INFO: Final = "/System/DeviceSIMCardInfo"
ENDPOINT_WIFI_AP_LIST: Final = "/Network/Interfaces/2/WIFIAccessPointList"
ENDPOINT_WIFI_CONFIG: Final = "/Network/Interfaces/2"
ENDPOINT_WIFI_BOOST: Final = "/Network/Interfaces/2"
ENDPOINT_FORCE_IFRAME: Final = "/System/{channel}/RemoteForceIFrame"
ENDPOINT_PTZ_CONFIG: Final = "/PTZ/{channel}/Config"
ENDPOINT_PTZ_CALIBRATION_CFG: Final = "/PTZ/1/CalibrationCfg"
ENDPOINT_PTZ_RESET: Final = "/PTZ/{channel}/PTZReset"
ENDPOINT_LENS_RESET: Final = "/PTZ/{channel}/CameraLensReset"
ENDPOINT_PTZ_HEATER: Final = "/PTZ/{channel}/Hearter"
ENDPOINT_PTZ_WIPER: Final = "/PTZ/{channel}/RainBrush"
ENDPOINT_PTZ_CALIBRATION: Final = "/PTZ/{channel}/Calibration"
ENDPOINT_PTZ_LINKAGE: Final = "/PTZ/1/Linkage/Goto"
ENDPOINT_WATCH_CARE_PRESET: Final = "/PTZ/{channel}/WatchCarePreset"
ENDPOINT_WATCH_CARE_ATTR: Final = "/PTZ/{channel}/WatchCarePresetAttribute"
ENDPOINT_CRUISE_TIMESLOT: Final = "/PTZ/{channel}/CruiseTimeSlot"
ENDPOINT_TRACK_TIMESLOT: Final = "/PTZ/{channel}/TrackTimeSlot"
ENDPOINT_WATCH_CARE_GOTO: Final = "/PTZ/1/WatchCareGoto"
ENDPOINT_ONE_BUTTON_CALL_CFG: Final = "/System/DevOneBtnCallFuncCfg"
ENDPOINT_ONE_BUTTON_CALL: Final = "/System/DeviceOneButtonCall"
ENDPOINT_BIND_CONFIG: Final = "/System/DeviceBindConfig"
ENDPOINT_MP_SERVER: Final = "/System/P6SMPServerParam"
ENDPOINT_CLOUD_ERRORS: Final = "/System/CloudMessageErrorCodeList"
ENDPOINT_CLOUD_STORAGE_STATUS: Final = "/Network/CloudStorage/BaseStatus"
ENDPOINT_CLOUD_STORAGE_MODE: Final = "/Network/CloudStorage/WorkMode"
ENDPOINT_CLOUD_RECORD_CFG: Final = "/Network/CloudStorage/BaseConfig"
ENDPOINT_CLOUD_RECORD_PLAN: Final = "/Network/CloudStorage/RecordPlan"
ENDPOINT_OSD: Final = "/Pictures/{channel}/OSD"
ENDPOINT_MULTI_OSD: Final = "/Pictures/{channel}/MultiOSDV2"
ENDPOINT_IMAGE_BASIC: Final = "/Images/{channel}/Basic"
ENDPOINT_IRCUT: Final = "/Images/{channel}/IrCutFilter"
ENDPOINT_IRCUT_EX: Final = "/Images/{channel}/IrCutFilterEx"
ENDPOINT_MOVE_TRACK: Final = "/Pictures/{channel}/MoveTrack"
ENDPOINT_MOTION: Final = "/Pictures/{channel}/Motion"
ENDPOINT_MOTION_REGIONS: Final = "/Pictures/{channel}/Motion/RegionsV2"
ENDPOINT_PIR: Final = "/Pictures/{channel}/PIRDetect"
ENDPOINT_RADAR: Final = "/Pictures/{channel}/RadarDetect"
ENDPOINT_PEOPLE_DETECT: Final = "/Pictures/{channel}/PeopleDetect"
ENDPOINT_PEOPLE_DETECT_V1: Final = "/Pictures/{channel}/PeopleDetectV1"
ENDPOINT_PEOPLE_STAY: Final = "/Pictures/{channel}/PeopleDetectStayTime"
ENDPOINT_PEOPLE_TRACK_SCHEDULE: Final = "/Pictures/{channel}/PeopleTrackSchedule"
ENDPOINT_CAR_DETECT: Final = "/Pictures/{channel}/CarDetect"
ENDPOINT_ANIMAL_DETECT: Final = "/Pictures/{channel}/AnimalDetect"
ENDPOINT_FACE_DETECT: Final = "/Pictures/{channel}/FaceDetect"
ENDPOINT_FACE_REGION: Final = "/Face/{channel}/DetectRegion"
ENDPOINT_CRY_DETECT: Final = "/AI/CryScreamDetect"
ENDPOINT_INTELLIGENT_TRACK: Final = "/AI/IntelligentTrack"
ENDPOINT_INTELLIGENT_TRACK_CH: Final = "/AI/{channel}/IntelligentTrack"
ENDPOINT_FACE_SNAPSHOT: Final = "/AI/FaceSnapshotCfg"
ENDPOINT_CAR_PLATE: Final = "/AI/CarPlateSnap"
ENDPOINT_FIRE_DETECT: Final = "/System/FireDetectCfgInfo"
ENDPOINT_FIRE_DETECT_EX: Final = "/System/FireDetectExCfg"
ENDPOINT_EBIKE_DETECT: Final = "/System/EBikeDetectCfg"
ENDPOINT_CROSS_BORDER: Final = "/System/CrossBorderDetectUIDesignInfo"
ENDPOINT_CROSS_BORDER_CH: Final = "/System/{channel}/CrossBorderDetectUIDesignInfo"
ENDPOINT_OFF_DUTY: Final = "/System/OffDutyDetectUIDesignCfg"
ENDPOINT_ELECTRONIC_FENCE: Final = "/System/ElectronicDenceUIDesignCfg"
ENDPOINT_PEOPLE_STATS: Final = "/System/PeopleStatisticsUIDesignCfg"
ENDPOINT_PASSENGER_FLOW: Final = "/System/PassengerFlowStatisticsUIDesignCfg"
ENDPOINT_PASSENGER_FLOW_EX: Final = "/System/PassengerFlowStaticsExCfg"
ENDPOINT_TRAFFIC_STATS: Final = "/System/TrafficStatisticsUIDesignCfg"
ENDPOINT_AIR_QUALITY: Final = "/System/AirQualityInfo"
ENDPOINT_LP_SURVEILLANCE: Final = "/System/LicensePlateSurveillanceUIDesignCfg"
ENDPOINT_FACE_RECO_BASE: Final = "/FaceReco/{channel}/BaseConfig"
ENDPOINT_FACE_RECO_RULES: Final = "/FaceReco/{channel}/RecoRuleList"
ENDPOINT_STREAM_CAP: Final = "/Streams/{channel}/CapabilityV2"

STREAM_MAIN: Final = 1
STREAM_SUB: Final = 2
STREAM_THIRD: Final = 3
STREAM_NAMES: Final = {
    STREAM_MAIN: "main",
    STREAM_SUB: "sub",
    STREAM_THIRD: "third",
}

SERVICE_SEND_COMMAND: Final = "send_command"
SERVICE_REDISCOVER: Final = "rediscover"
SERVICE_GOTO_PRESET: Final = "goto_preset"
SERVICE_PTZ_CONTROL: Final = "ptz_control"
SERVICE_ONE_CLICK_ALARM: Final = "one_click_alarm"
SERVICE_SLEEP_CONTROL: Final = "sleep_control"
SERVICE_FORMAT_SDCARD: Final = "format_sdcard"
SERVICE_FORCE_IFRAME: Final = "force_iframe"
SERVICE_SET_OSD_TEXT: Final = "set_osd_text"
SERVICE_ALARM_OUTPUT: Final = "alarm_output"
SERVICE_AUDIO_ALARM_STOP: Final = "audio_alarm_stop"
SERVICE_SYNC_TIME: Final = "sync_time"

ATTR_CONFIG_ENTRY_ID: Final = "config_entry_id"
ATTR_DID: Final = "did"
ATTR_PATH: Final = "path"
ATTR_METHOD: Final = "method"
ATTR_XML: Final = "xml"
ATTR_CHANNEL: Final = "channel"
ATTR_PRESET: Final = "preset"
ATTR_ACTION: Final = "action"
ATTR_TEXT: Final = "text"
ATTR_DURATION: Final = "duration"

DATA_COORDINATORS: Final = "coordinators"
