<p align="center">
  <img src="assets/hieasy-logo.svg" alt="HiEasy Camera Bridge" width="640">
</p>

<h1 align="center">HiEasy cho Home Assistant</h1>

<p align="center">
  <a href="https://github.com/trankhanhduy2929-beep/hieasy-camera-homeassistant/actions/workflows/validate.yml"><img src="https://github.com/trankhanhduy2929-beep/hieasy-camera-homeassistant/actions/workflows/validate.yml/badge.svg" alt="Validate"></a>
  <a href="https://github.com/trankhanhduy2929-beep/hieasy-camera-homeassistant/releases"><img src="https://img.shields.io/github/v/release/trankhanhduy2929-beep/hieasy-camera-homeassistant" alt="GitHub release"></a>
</p>

Custom integration cho camera Visioncop/HiEasy (APK `HiEasy 8.1.2`, package
`com.zwcode.p6slite`). Mục tiêu là **chỉ nhập tài khoản cloud một lần**, sau đó
Home Assistant tự lấy danh sách thiết bị, tìm camera trong LAN và dùng RTSP
qua CGI proprietary hoặc ONVIF.

> **Trạng thái 0.3.0:** đã triển khai cloud login, tự dò LAN, IP/hostname thủ
> công, WS-Discovery, HTTP Basic/Digest, CGI RTSP, ONVIF và probe RTSP trực
> tiếp có giới hạn. Toàn bộ endpoint setting của APK (detection AI, báo động,
> đèn, PTZ, lưu trữ, mạng, nguồn, thời gian) được poll và điều khiển qua
> entity hoặc service. Chưa có P2P trực tiếp qua PPCS native của Android.

## Cài bằng HACS

1. Mở **HACS → Integrations**.
2. Mở menu góc phải, chọn **Custom repositories**.
3. Thêm repository
   `https://github.com/trankhanhduy2929-beep/hieasy-camera-homeassistant`, category
   **Integration**.
4. Tìm **HiEasy**, chọn **Download**, rồi khởi động lại Home Assistant.
5. Vào **Settings → Devices & services → Add integration → HiEasy**.

## Cài bằng ZIP

1. Giải nén `hieasy_custom_component.zip` vào thư mục cấu hình Home Assistant
   (thường là `/config`). ZIP đã chứa sẵn thư mục `custom_components/hieasy`.
2. Khởi động lại Home Assistant.
3. Vào **Settings → Devices & services → Add integration → HiEasy**.
4. Nhập tài khoản và mật khẩu HiEasy. Để vùng cloud là **Automatic** nếu không
   biết vùng; integration sẽ thử các máy chủ trong APK. Số điện thoại Việt Nam
   có thể nhập dạng `0912345678`, `912345678` hoặc `+84912345678`; integration
   tự chuẩn hóa về định dạng cloud HiEasy sử dụng.
5. Chờ lần cập nhật đầu tiên. Nếu Home Assistant chạy trong container/VLAN,
   bảo đảm nó có route tới mạng camera và cho phép UDP multicast.

## Sau khi đăng nhập

Mỗi thiết bị trong tài khoản được tạo thành một device Home Assistant với:

- `camera`: ba profile cho mỗi kênh (`main`, `sub`, `third`); entity chỉ hoạt
  động khi tìm được RTSP URI.
- `binary_sensor`: online, kết nối LAN, hỗ trợ PTZ, đang ngủ, alarm output
  active, còi/đèn đang kêu, thẻ nhớ, SIM, pin yếu, ghi cloud.
- `sensor`: model, firmware, serial, MAC, device type, số kênh, IP LAN, cổng
  command/media, transport, pin (cloud + local), tín hiệu Wi-Fi/SIM, SSID,
  nhà mạng SIM, điện áp/trạng thái nguồn, dung lượng thẻ nhớ, thời gian còi
  còn lại, chất lượng không khí, thống kê báo động/người/thức/xem hôm nay.
- `switch` (device): đèn báo, đèn trắng/light control, đèn trang trí, đèn đêm,
  alarm output, không làm phiền, báo động cảm biến khí, phát hiện khóc/la, bám
  mục tiêu thông minh, phát hiện lửa, phát hiện xe điện.
- `switch` (per-channel): phát hiện chuyển động, bám chuyển động, phát hiện
  người, xe, động vật, PIR, radar, đèn cảnh báo, còi báo, báo động một chạm,
  lịch ghi hình.
- `select`: night vision mode, chế độ đàm thoại, chế độ nguồn, chế độ đèn
  trang trí/điều khiển đèn, IR-cut mode/scene, lật ảnh, giao thức PTZ, chế độ
  canh PTZ, kiểu ghi hình.
- `number`: thời gian không làm phiền, thời gian đèn đêm, âm lượng báo
  động/mic/loa, độ sáng đèn bù/đèn có người/không người, ngưỡng pin yếu, độ
  nhạy chuyển động/người/PIR/radar/IR-cut, giảm nhiễu, độ trễ cảnh báo, thời
  gian báo động, chu kỳ push.
- `button` (device): dò lại LAN, reboot, ép keyframe, báo động một chạm, dừng
  còi, ngủ/đánh thức, đồng bộ giờ, format thẻ nhớ, nút gọi.
- `button` (per-channel): reset PTZ, reset lens, hiệu chuẩn PTZ, về điểm canh
  chủ, bắt đầu/dừng tuần tra, quỹ đạo tuần tra, bám người, quét ngang, quét
  360, quỹ đạo, gạt mưa, sưởi.

Các entity setting được tạo theo kiểu best-effort: firmware Visioncop có nhiều
biến thể, vì vậy entity có thể ở trạng thái unavailable nếu endpoint không tồn
tại trên model đó.

## Dịch vụ nâng cao

### `hieasy.rediscover`

Làm mới cloud, chạy lại WS-Discovery và quét LAN có giới hạn. Thường không cần
gọi vì integration tự làm định kỳ.

### `hieasy.send_command`

Gửi lệnh proprietary đã thấy trong APK. Chỉ chấp nhận path nội bộ bắt đầu bằng
`/`; không cho phép URL ngoài để tránh biến service thành SSRF.

```yaml
action: hieasy.send_command
data:
  did: "DID_CUA_CAMERA"
  method: GET
  path: "/System/DeviceInfo"
```

PUT XML mẫu:

```yaml
action: hieasy.send_command
data:
  did: "DID_CUA_CAMERA"
  method: PUT
  path: "/System/IndicatorLightCfg"
  xml: |
    <IndicatorLightCfg Version="1.0">
      <Enable>true</Enable>
    </IndicatorLightCfg>
```

### `hieasy.goto_preset`

Gọi preset PTZ theo payload APK (`Param1=<số preset>`):

```yaml
action: hieasy.goto_preset
data:
  did: "DID_CUA_CAMERA"
  channel: 1
  preset: 3
```

### `hieasy.ptz_control`

Chạy mọi hành động PTZ có trong APK:

```yaml
action: hieasy.ptz_control
data:
  did: "DID_CUA_CAMERA"
  channel: 1
  action: human_track_start   # hoặc cruise_start, range_scan360_start, watch_start...
  preset: 3                    # chỉ cần cho preset_set/preset_remove/watch_start/watch_stop
```

Danh sách `action`: `preset_set`, `preset_remove`, `ptz_reset`, `lens_reset`,
`calibration`, `cruise_start`, `cruise_stop`, `cruise_track_start`,
`cruise_track_stop`, `human_track_start`, `human_track_stop`,
`range_scan_start`, `range_scan_stop`, `range_scan_left`, `range_scan_right`,
`range_scan360_start`, `range_scan360_stop`, `track_start`, `track_stop`,
`track_mem_start`, `track_mem_stop`, `watch_start`, `watch_stop`,
`watch_care_goto`, `wiper`, `heater`.

### `hieasy.one_click_alarm` / `hieasy.audio_alarm_stop` / `hieasy.alarm_output`

```yaml
action: hieasy.one_click_alarm
data: {did: "DID", channel: 1}

action: hieasy.audio_alarm_stop
data: {did: "DID", channel: 1}

action: hieasy.alarm_output
data: {did: "DID", channel: 1, action: on}   # on/off relay báo động
```

### `hieasy.sleep_control` / `hieasy.sync_time` / `hieasy.force_iframe` / `hieasy.format_sdcard`

```yaml
action: hieasy.sleep_control
data: {did: "DID", action: sleep}   # hoặc wake

action: hieasy.sync_time
data: {did: "DID"}                  # ghi giờ hệ thống HA vào camera

action: hieasy.force_iframe
data: {did: "DID", channel: 1}

action: hieasy.format_sdcard
data: {did: "DID"}                  # format thẻ nhớ — mất toàn bộ bản ghi
```

### `hieasy.set_osd_text`

```yaml
action: hieasy.set_osd_text
data:
  did: "DID_CUA_CAMERA"
  channel: 1
  text: "Camera sân vườn"
```

### `hieasy.wifi_scan` / `hieasy.wifi_status`

```yaml
action: hieasy.wifi_scan
data: {did: "DID"}
# trả về danh sách AP camera nhìn thấy: [{SSID, SignalValue, Authentication}, ...]

action: hieasy.wifi_status
data: {did: "DID"}
# trả về {ssid, signal_strength} của mạng Wi-Fi camera đang kết nối
```

Hai sensor tự động `sensor.<device>_wifi_signal_strength` và
`sensor.<device>_wifi_name` cũng đọc endpoint `WirelessEx` nếu camera hỗ trợ.

DID có thể xem trong diagnostics hoặc thuộc tính device. Nếu có nhiều config
entry dùng cùng DID, thêm `config_entry_id`.

## Tùy chọn LAN

Vào **Configure** của integration để chỉnh:

- `Camera IP addresses or hostnames`: địa chỉ chính xác, ví dụ
  `192.168.1.20,camera-san.local`; được thử trước khi quét subnet.
- `LAN networks`: CIDR, ví dụ `192.168.1.0/24`; nên điền khi HA chạy trong
  Docker bridge hoặc có nhiều VLAN.
- `HTTP / ONVIF ports`: mặc định `80,81,8000,8080,8899`.
- `RTSP ports`: mặc định `554,8554`.
- `RTSP path templates`: danh sách path tương đối. Có thể dùng `{channel}`,
  `{channel02}`, `{stream}`, `{subtype}` và `{profile}`.
- `Maximum hosts`: giới hạn quét để không tạo lưu lượng lớn.
- `Per-request timeout` và chu kỳ polling.

Khi nâng cấp từ bản cũ, integration tự xóa entity registry có unique ID
`<did>_last_seen` và option timestamp cũ ở lần setup tiếp theo.

Luồng dò tìm:

1. WS-Discovery ONVIF.
2. Địa chỉ IP có trong metadata cloud và danh sách IP/hostname thủ công.
3. Probe `/Network/Port` với Basic/Digest auth.
4. Ghép thiết bị bằng DID/serial/MAC và lấy `/Streams/{channel}/{1,2,3}`.
5. Nếu không có CGI proprietary, gọi ONVIF `GetCapabilities`,
   `GetProfiles`, `GetStreamUri`.
6. Quét subnet đã giới hạn trên các cổng HTTP/ONVIF.
7. Với thiết bị chưa ghép được, chỉ giữ các cổng RTSP TCP đang mở rồi gửi
   `OPTIONS`/`DESCRIBE` bằng Basic hoặc Digest trên tối đa 48 path đã mở rộng.

Nếu chỉ tìm được RTSP trực tiếp, camera entity hoạt động với transport
`rtsp_scan`; các nút/setting CGI không có endpoint HTTP sẽ unavailable.

## Giới hạn quan trọng: P2P

APK dùng SDK native PPCS/EasyCam cho P2P, gồm các thư viện Android ARM64 như
`libPPCS_API.so`, `libEasyCamSdk.so`, `libStreamerClient.so` và decoder
FFmpeg/Hisi. Luồng P2P không phải RTSP URL; Android SDK mở channel native rồi
đưa frame/audio vào renderer JNI. Vì vậy:

- Python/Home Assistant không thể nạp trực tiếp các `.so` Bionic/JNI này.
- Không copy hoặc phân phối binary native của APK trong component.
- Component này **không giả vờ hỗ trợ P2P**: camera chỉ có live view khi LAN
  CGI/RTSP hoặc ONVIF truy cập được.
- Nếu camera chỉ online cloud/P2P và không mở ONVIF/RTSP LAN, entity metadata
  vẫn có thể hoạt động nhưng camera stream sẽ unavailable.

Để hỗ trợ P2P thật sự cần một bridge Android/ARM chạy SDK được cấp phép, sau đó
expose RTSP/WebRTC/MJPEG cho HA. Đó là một dự án add-on/sidecar riêng, không an
toàn để suy ra từ APK và không được đưa vào gói này.

## Bảo mật

- Mật khẩu cloud và mật khẩu từng camera được dùng để đăng nhập Basic/Digest và
  chèn vào RTSP URI trong bộ xử lý stream của HA; không ghi vào log chủ động.
- Diagnostics đã redact `account`, `password`, `pwd`, `token`.
- RTSP URL trong state attributes không được expose; chỉ lưu transport/host/port.
- Chỉ dùng với camera và tài khoản mà bạn có quyền quản trị. Không mở CGI
  camera ra Internet.

## Xử lý lỗi

- **Đăng nhập thất bại:** thử `Automatic`; nếu biết vùng, chọn đúng `World`,
  `America`, `Europe`, `China` hoặc `YL`. Với số Việt Nam, có thể nhập số nội
  địa bắt đầu bằng `0` hoặc dạng quốc tế bắt đầu bằng `+84`.
- **Server nhận ra tài khoản nhưng từ chối mật khẩu:** integration sẽ chỉ rõ
  vùng cloud. Hãy đăng xuất hoàn toàn khỏi ứng dụng HiEasy rồi đăng nhập lại
  bằng chính mật khẩu đó. Nếu ứng dụng thường đăng nhập bằng mã SMS, hãy dùng
  chức năng quên mật khẩu để tạo/đặt lại mật khẩu tài khoản trước khi thêm vào
  Home Assistant.
- **Có sensor nhưng không có camera:** điền IP chính xác vào `Camera IP
  addresses or hostnames`, kiểm tra route, cổng HTTP/ONVIF và RTSP; sau đó gọi
  `hieasy.rediscover`.
- **Camera ONVIF được tìm nhưng không phát:** kiểm tra FFmpeg/stream của HA,
  thử profile `sub`, và xem URL/port trong diagnostics.
- **Cổng 554 mở nhưng vẫn không có camera:** thêm đúng path RTSP của model vào
  `RTSP path templates`; chỉ path trả `DESCRIBE 200` mới được dùng.
- **Nhiều VLAN:** WS-Discovery thường không đi qua router; nhập CIDR và port
  thủ công, hoặc dùng ONVIF discovery ở cùng broadcast domain.
- **Setting unavailable:** đó là khác biệt firmware; dùng `send_command` với
  endpoint CGI tương ứng của model (ví dụ `/System/DeviceInfo`).
