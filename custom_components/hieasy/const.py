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

ATTR_CONFIG_ENTRY_ID: Final = "config_entry_id"
ATTR_DID: Final = "did"
ATTR_PATH: Final = "path"
ATTR_METHOD: Final = "method"
ATTR_XML: Final = "xml"
ATTR_CHANNEL: Final = "channel"
ATTR_PRESET: Final = "preset"

DATA_COORDINATORS: Final = "coordinators"
