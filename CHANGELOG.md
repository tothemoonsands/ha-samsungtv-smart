# Changelog

## 9.1.1
- Report Art Mode as `off` instead of `unknown` when the TV is clearly showing
  a normal source/app such as Apple TV but the Art websocket does not return a
  status.

## 9.1.0
- Restore upstream's tokenless Art websocket behavior for newer Frame firmware:
  accept `ms.channel.connect` on the Art channel and stop trying the remote
  websocket token, which can return `No Authorized`.
- Learn when a TV does not answer the dedicated `get_brightness` request and
  use `get_artmode_settings` directly on later reads.
- Track the TV's native Art brightness range from settings payloads so HA can
  map models that report `0..50` instead of the older `0..10` scale.

## 9.0.0
- Restore authenticated secure Art websocket fallback for Frames that connect
  tokenless but never answer Art API requests. Tokenless connections must now
  reach `ms.channel.ready`; authenticated `8002` can use the older
  `ms.channel.connect`-only behavior that previously worked for brightness.

## 8.0.2
- Fix Art websocket handshakes by ignoring `ms.channel.clientConnect` as a
  successful Art API connection. Only `ms.channel.connect` and
  `ms.channel.ready` indicate a usable host connection; accepting
  `clientConnect` could leave brightness commands writing to a silent channel.
- Shorten the direct `get_brightness` probe before falling back to Art Mode
  settings, matching upstream behavior for newer Frame TVs that do not answer
  the dedicated brightness read.

## 8.0.1
- Stop using Samsung IP Control `backlightControl` as an Art Mode brightness
  fallback. On newer Frame TVs it can report/update panel backlight while the
  actual Art Mode brightness remains unchanged, causing false HA success states.
- Add SmartThings diagnostic services for reading exposed device states and
  testing explicit capability commands while investigating the new Art Mode
  brightness API path.

## 8.0.0
- Add an IP Control backlight fallback for Art Mode brightness reads and writes
  when the Samsung Art websocket no longer answers brightness requests.
- Fix the Art Mode switch state mirroring: `switch.artmode_art_mode` now trusts
  the media player/sensor Art Mode status before falling back to the unreliable
  2024 Frame art websocket.
- Fix Art Mode brightness handling when Samsung returns websocket error objects
  or consolidated settings payloads: brightness errors no longer look like
  success, settings-style brightness is parsed, and successful writes update
  the local brightness cache for HA verification.
- Fix 2024 Frame IP Control status reads: avoid the side-effect-prone
  artModeControl getter and infer Art Mode off when the TV is actively showing
  a normal media_player source such as Apple TV.
- Major Art Mode reliability update: backported upstream Frame TV WebSocket fixes for tokenless art-channel connections, connect-without-ready handshakes, shared Art API client ownership, and accurate Art Mode service success reporting.
- Branding refresh: updated display names and documentation to use the new friendly integration name while keeping the `samsungtv_artmode` domain unchanged.
- Fixed Frame Art websocket connection handling to fall back between ports `8002` and `8001` when the TV rejects one of them.
