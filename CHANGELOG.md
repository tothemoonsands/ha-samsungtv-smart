# Changelog

## Unreleased
- Fix 2024 Frame IP Control status reads: avoid the side-effect-prone
  artModeControl getter and infer Art Mode off when the TV is actively showing
  a normal media_player source such as Apple TV.
- Major Art Mode reliability update: backported upstream Frame TV WebSocket fixes for tokenless art-channel connections, connect-without-ready handshakes, shared Art API client ownership, and accurate Art Mode service success reporting.
- Branding refresh: updated display names and documentation to use the new friendly integration name while keeping the `samsungtv_artmode` domain unchanged.
- Fixed Frame Art websocket connection handling to fall back between ports `8002` and `8001` when the TV rejects one of them.
