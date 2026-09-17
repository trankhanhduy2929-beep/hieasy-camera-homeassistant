"""Pure protocol helpers for Visioncop/HiEasy XML, RTSP and HTTP auth."""

from __future__ import annotations

import hashlib
import html
import ipaddress
import os
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Mapping, Sequence
from typing import Any
from urllib.parse import quote, unquote, urlsplit, urlunsplit

_XML_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_DIGEST_VALUE_RE = re.compile(r"([a-zA-Z0-9_-]+)=(?:\"([^\"]*)\"|([^,\s]+))")
_RTSP_RE = re.compile(r"rtsp://[^\s<>'\"]+", re.IGNORECASE)
_URL_RE = re.compile(r"https?://[^\s<>'\"]+", re.IGNORECASE)


class HiEasyXmlError(ValueError):
    """Raised when a device response cannot be parsed as XML."""


def parse_xml(xml_text: str) -> ET.Element:
    """Parse slightly malformed device XML and return its root element."""
    if not xml_text:
        raise HiEasyXmlError("Phản hồi XML trống")
    cleaned = _XML_CONTROL_RE.sub("", xml_text).strip().lstrip("\ufeff")
    first_tag = cleaned.find("<")
    if first_tag > 0:
        cleaned = cleaned[first_tag:]
    try:
        return ET.fromstring(cleaned)
    except ET.ParseError as err:
        raise HiEasyXmlError(str(err)) from err


def local_name(tag: str) -> str:
    """Strip an XML namespace from a tag."""
    return tag.rsplit("}", 1)[-1].split(":", 1)[-1]


def find_xml_value(xml_text: str, names: Iterable[str]) -> str | None:
    """Return the first non-empty value matching any local tag name."""
    root = parse_xml(xml_text)
    wanted = {name.lower() for name in names}
    for element in root.iter():
        if local_name(element.tag).lower() not in wanted:
            continue
        value = (element.text or "").strip()
        if value:
            return html.unescape(value)
    return None


def flatten_xml(xml_text: str) -> dict[str, Any]:
    """Flatten XML leaves into case-insensitive path and leaf-name keys."""
    root = parse_xml(xml_text)
    result: dict[str, Any] = {}

    def visit(element: ET.Element, path: tuple[str, ...]) -> None:
        name = local_name(element.tag)
        current = (*path, name)
        children = list(element)
        text = (element.text or "").strip()
        if not children and text:
            value = scalar_value(html.unescape(text))
            path_key = ".".join(part.lower() for part in current)
            result[path_key] = value
            result.setdefault(name.lower(), value)
        for attr_name, attr_value in element.attrib.items():
            result[f"{'.'.join(part.lower() for part in current)}.@{local_name(attr_name).lower()}"] = scalar_value(attr_value)
        for child in children:
            visit(child, current)

    visit(root, ())
    return result


def scalar_value(value: str) -> str | bool | int | float:
    """Convert an XML scalar while preserving unrecognized strings."""
    stripped = value.strip()
    lowered = stripped.lower()
    if lowered in {"true", "yes", "on", "enabled"}:
        return True
    if lowered in {"false", "no", "off", "disabled"}:
        return False
    try:
        if re.fullmatch(r"[-+]?\d+", stripped):
            return int(stripped)
        if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)", stripped):
            return float(stripped)
    except ValueError:
        pass
    return stripped


def parse_bool(value: Any) -> bool | None:
    """Interpret common device boolean encodings."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on", "enable", "enabled", "open"}:
            return True
        if lowered in {"0", "false", "no", "off", "disable", "disabled", "close"}:
            return False
    return None


def parse_number(value: Any) -> float | None:
    """Convert a scalar to a float when possible."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_port_config(xml_text: str) -> dict[str, int]:
    """Parse command, HTTP, HTTPS, RTSP and media ports from /Network/Port."""
    values = flatten_xml(xml_text)
    aliases = {
        "command": ("command", "cmdport", "commandport", "http", "httpport"),
        "media": ("media", "mediaport", "rtsp", "rtspport"),
        "https": ("https", "httpsport"),
        "onvif": ("onvif", "onvifport"),
    }
    ports: dict[str, int] = {}
    for output_name, names in aliases.items():
        value = value_by_alias(values, names)
        try:
            port = int(value)
        except (TypeError, ValueError):
            continue
        if 0 < port <= 65535:
            ports[output_name] = port
    return ports


def parse_device_identity(xml_text: str) -> dict[str, str]:
    """Extract stable identity and firmware values from /System/DeviceInfo."""
    values = flatten_xml(xml_text)
    fields = {
        "did": ("did", "p2pid", "uid", "deviceid"),
        "serial": ("devicesn", "serialnum", "serialnumber", "serial", "sn"),
        "mac": ("mac", "macaddress"),
        "model": ("model", "devicename", "modelname", "productname"),
        "firmware": (
            "firmwareversion",
            "softwareversion",
            "version",
            "customerVersion",
        ),
    }
    identity: dict[str, str] = {}
    for key, aliases in fields.items():
        value = value_by_alias(values, aliases)
        if value not in (None, ""):
            identity[key] = str(value).strip()
    return identity


def value_by_alias(values: Mapping[str, Any], aliases: Iterable[str]) -> Any:
    """Find a flattened XML value by leaf or path suffix."""
    lower_aliases = tuple(alias.lower() for alias in aliases)
    for alias in lower_aliases:
        if alias in values:
            return values[alias]
    for key, value in values.items():
        leaf = key.rsplit(".", 1)[-1]
        if leaf in lower_aliases:
            return value
    return None


def mutate_xml_fields(
    xml_text: str,
    updates: Mapping[str, Any],
    *,
    root_name: str | None = None,
) -> str:
    """Update XML fields while retaining the device's remaining configuration."""
    if xml_text.strip():
        root = parse_xml(xml_text)
    elif root_name:
        root = ET.Element(root_name, {"Version": "1.0"})
    else:
        raise HiEasyXmlError("Cần XML gốc hoặc tên root")

    elements = {local_name(element.tag).lower(): element for element in root.iter()}
    for field_name, value in updates.items():
        target = elements.get(field_name.lower())
        if target is None:
            target = ET.SubElement(root, field_name)
            elements[field_name.lower()] = target
        target.text = xml_scalar_text(value)
    return ET.tostring(root, encoding="unicode", short_empty_elements=False)


def mutate_first_alias(
    xml_text: str,
    aliases: Sequence[str],
    value: Any,
    *,
    root_name: str,
    fallback_field: str = "Enable",
) -> str:
    """Update the first existing field alias, or append a safe fallback field."""
    if xml_text.strip():
        root = parse_xml(xml_text)
    else:
        root = ET.Element(root_name, {"Version": "1.0"})
    wanted = {alias.lower() for alias in aliases}
    target = next(
        (
            element
            for element in root.iter()
            if local_name(element.tag).lower() in wanted
        ),
        None,
    )
    if target is None:
        target = ET.SubElement(root, fallback_field)
    target.text = xml_scalar_text(value)
    return ET.tostring(root, encoding="unicode", short_empty_elements=False)


def xml_scalar_text(value: Any) -> str:
    """Format a scalar as expected by HiEasy XML endpoints."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def extract_rtsp_uri(xml_text: str) -> str | None:
    """Extract RTSPURI from StreamConfig XML, with a text fallback."""
    try:
        value = find_xml_value(xml_text, ("RTSPURI", "StreamUri", "Uri", "MediaUri"))
    except HiEasyXmlError:
        value = None
    if value:
        match = _RTSP_RE.search(value)
        return html.unescape(match.group(0) if match else value.strip())
    match = _RTSP_RE.search(html.unescape(xml_text))
    return match.group(0) if match else None


def normalize_rtsp_uri(
    uri: str,
    host: str,
    media_port: int | None,
    username: str,
    password: str,
) -> str:
    """Normalize a device RTSP URI and inject URL-escaped credentials."""
    candidate = html.unescape(uri).strip()
    if not candidate.lower().startswith("rtsp://"):
        path = candidate if candidate.startswith("/") else f"/{candidate}"
        port_part = f":{media_port}" if media_port else ""
        candidate = f"rtsp://{host}{port_part}{path}"

    parts = urlsplit(candidate)
    uri_host = parts.hostname or host
    try:
        parsed_ip = ipaddress.ip_address(uri_host.strip("[]"))
        if parsed_ip.is_unspecified or parsed_ip.is_loopback:
            uri_host = host
    except ValueError:
        if uri_host.lower() in {"localhost", "camera", "ipc"}:
            uri_host = host

    port = parts.port or media_port
    host_text = f"[{uri_host}]" if ":" in uri_host and not uri_host.startswith("[") else uri_host
    if username:
        userinfo = quote(unquote(username), safe="")
        if password:
            userinfo += f":{quote(unquote(password), safe='')}"
        netloc = f"{userinfo}@{host_text}"
    else:
        netloc = host_text
    if port:
        netloc += f":{port}"
    return urlunsplit(("rtsp", netloc, parts.path or "/", parts.query, parts.fragment))


def redact_url_credentials(uri: str | None) -> str | None:
    """Remove credentials from a URL before exposing diagnostics."""
    if not uri:
        return uri
    parts = urlsplit(uri)
    host = parts.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = host
    if parts.port:
        netloc += f":{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def normalize_mac(value: str | None) -> str:
    """Normalize a MAC address for comparisons."""
    return re.sub(r"[^0-9a-f]", "", (value or "").lower())


def identities_match(cloud: Any, identity: Mapping[str, str]) -> bool:
    """Return whether local identity fields match a cloud device."""
    comparisons = (
        (getattr(cloud, "did", None), identity.get("did"), False),
        (getattr(cloud, "serial", None), identity.get("serial"), False),
        (getattr(cloud, "mac", None), identity.get("mac"), True),
    )
    compared = False
    for cloud_value, local_value, is_mac in comparisons:
        if not cloud_value or not local_value:
            continue
        compared = True
        if is_mac:
            if normalize_mac(str(cloud_value)) == normalize_mac(str(local_value)):
                return True
        elif str(cloud_value).strip().lower() == str(local_value).strip().lower():
            return True
    return not compared


def parse_ws_discovery_urls(payload: str) -> set[str]:
    """Extract XAddr URLs from a WS-Discovery response."""
    urls: set[str] = set()
    try:
        root = parse_xml(payload)
        for element in root.iter():
            if local_name(element.tag).lower() != "xaddrs":
                continue
            for url in (element.text or "").split():
                if url.startswith(("http://", "https://")):
                    urls.add(url)
    except HiEasyXmlError:
        urls.update(_URL_RE.findall(payload))
    return urls


def parse_onvif_profiles(xml_text: str) -> list[str]:
    """Extract ONVIF profile tokens from GetProfiles."""
    root = parse_xml(xml_text)
    tokens: list[str] = []
    for element in root.iter():
        if local_name(element.tag).lower() not in {"profiles", "profile"}:
            continue
        token = element.attrib.get("token") or element.attrib.get("Token")
        if token and token not in tokens:
            tokens.append(token)
    return tokens


def parse_onvif_media_url(xml_text: str) -> str | None:
    """Extract the Media XAddr from ONVIF GetCapabilities."""
    root = parse_xml(xml_text)
    for element in root.iter():
        if local_name(element.tag).lower() != "media":
            continue
        for child in element.iter():
            if local_name(child.tag).lower() == "xaddr" and (child.text or "").strip():
                return html.unescape((child.text or "").strip())
    for element in root.iter():
        if local_name(element.tag).lower() == "xaddr":
            value = (element.text or "").strip()
            if value and "media" in value.lower():
                return html.unescape(value)
    return None


def parse_onvif_stream_uri(xml_text: str) -> str | None:
    """Extract a media URI from an ONVIF GetStreamUri response."""
    try:
        value = find_xml_value(xml_text, ("Uri", "URI", "MediaUri", "RTSPURI"))
    except HiEasyXmlError:
        value = None
    if value and value.lower().startswith("rtsp://"):
        return value
    match = _RTSP_RE.search(xml_text)
    return html.unescape(match.group(0)) if match else None


def parse_digest_challenge(header: str) -> dict[str, str]:
    """Parse an HTTP Digest WWW-Authenticate challenge."""
    if not header.lower().startswith("digest "):
        return {}
    return {
        key.lower(): quoted if quoted is not None else bare
        for key, quoted, bare in _DIGEST_VALUE_RE.findall(header[7:])
    }


def build_digest_authorization(
    challenge: Mapping[str, str],
    method: str,
    request_target: str,
    username: str,
    password: str,
) -> str:
    """Build RFC 7616 MD5 authorization used by many low-cost ONVIF cameras."""
    realm = challenge.get("realm", "")
    nonce = challenge.get("nonce", "")
    algorithm = challenge.get("algorithm", "MD5").upper()
    qop_values = [item.strip() for item in challenge.get("qop", "").split(",")]
    qop = "auth" if "auth" in qop_values else ""
    opaque = challenge.get("opaque")
    if not realm or not nonce or algorithm not in {"MD5", "MD5-SESS"}:
        return ""

    def md5(value: str) -> str:
        return hashlib.md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()

    cnonce = os.urandom(8).hex()
    nonce_count = "00000001"
    ha1 = md5(f"{username}:{realm}:{password}")
    if algorithm == "MD5-SESS":
        ha1 = md5(f"{ha1}:{nonce}:{cnonce}")
    ha2 = md5(f"{method.upper()}:{request_target}")
    if qop:
        response = md5(f"{ha1}:{nonce}:{nonce_count}:{cnonce}:{qop}:{ha2}")
    else:
        response = md5(f"{ha1}:{nonce}:{ha2}")

    fields = [
        f'username="{username}"',
        f'realm="{realm}"',
        f'nonce="{nonce}"',
        f'uri="{request_target}"',
        f'response="{response}"',
        f"algorithm={algorithm}",
    ]
    if opaque:
        fields.append(f'opaque="{opaque}"')
    if qop:
        fields.extend((f"qop={qop}", f"nc={nonce_count}", f'cnonce="{cnonce}"'))
    return "Digest " + ", ".join(fields)
