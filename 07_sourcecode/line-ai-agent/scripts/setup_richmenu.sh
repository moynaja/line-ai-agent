#!/usr/bin/env bash
# One-off setup script: creates the Greenman Rich Menu via the LINE Messaging
# API (not the manager.line.biz web UI, which doesn't support Postback tap
# actions) and sets it as the default menu for all users.
#
# Why this exists: the OA Manager web UI's "Action type" dropdown only
# offers Select/Link/Coupon/Text/Reward cards/No action — there's no
# Postback option there. The bot's mode-routing (app/handlers/webhook_handler.py)
# expects Postback events with data like "mode=task", so we create the rich
# menu directly via the API instead, which fully supports Postback actions.
#
# Run this from your own machine (needs real internet access):
#   cd PJ-LineBOT
#   bash scripts/setup_richmenu.sh
#
# Requires: curl, and a .env file in this same folder with
# LINE_CHANNEL_ACCESS_TOKEN set (already present in your project).

set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "❌ .env not found in $(pwd). Run this from inside the PJ-LineBOT project." >&2
  exit 1
fi

TOKEN=$(grep -E '^LINE_CHANNEL_ACCESS_TOKEN=' .env | cut -d '=' -f2-)
if [ -z "$TOKEN" ]; then
  echo "❌ LINE_CHANNEL_ACCESS_TOKEN is empty in .env" >&2
  exit 1
fi

IMAGE=assets/richmenu_greenman.png
if [ ! -f "$IMAGE" ]; then
  echo "❌ $IMAGE not found." >&2
  exit 1
fi

echo "▶ Creating rich menu object..."
CREATE_RESPONSE=$(curl -s -X POST https://api.line.me/v2/bot/richmenu \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "size": {"width": 2500, "height": 1686},
    "selected": true,
    "name": "Greenman Main Menu",
    "chatBarText": "Menu",
    "areas": [
      {"bounds": {"x": 0,    "y": 0,   "width": 1250, "height": 843},
       "action": {"type": "postback", "data": "mode=task",   "displayText": "งาน"}},
      {"bounds": {"x": 1250, "y": 0,   "width": 1250, "height": 843},
       "action": {"type": "postback", "data": "mode=chat",   "displayText": "ทั่วไป"}},
      {"bounds": {"x": 0,    "y": 843, "width": 1250, "height": 843},
       "action": {"type": "postback", "data": "mode=note",   "displayText": "บันทึก"}},
      {"bounds": {"x": 1250, "y": 843, "width": 1250, "height": 843},
       "action": {"type": "postback", "data": "mode=remind", "displayText": "แจ้งเตือน"}}
    ]
  }')
echo "$CREATE_RESPONSE"

RICH_MENU_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['richMenuId'])" 2>/dev/null || true)
if [ -z "$RICH_MENU_ID" ]; then
  echo "❌ Could not parse richMenuId from response above — something went wrong. Stopping." >&2
  exit 1
fi
echo "✅ richMenuId = $RICH_MENU_ID"

echo "▶ Uploading image..."
UPLOAD_STATUS=$(curl -s -o /tmp/richmenu_upload_body.txt -w "%{http_code}" -X POST \
  "https://api-data.line.me/v2/bot/richmenu/$RICH_MENU_ID/content" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: image/png" \
  --data-binary "@$IMAGE")
if [ "$UPLOAD_STATUS" != "200" ]; then
  echo "❌ Image upload failed (HTTP $UPLOAD_STATUS):" >&2
  cat /tmp/richmenu_upload_body.txt >&2
  exit 1
fi
echo "✅ Image uploaded"

echo "▶ Setting as default rich menu for all users..."
# -d '' forces curl to send Content-Length: 0. Without it, curl sends this
# bodyless POST with neither Content-Length nor Transfer-Encoding, which
# LINE's Akamai-fronted API rejects as a malformed request ("Bad Request /
# your browser sent a request this server could not understand").
DEFAULT_STATUS=$(curl -s -o /tmp/richmenu_default_body.txt -w "%{http_code}" -X POST \
  "https://api.line.me/v2/bot/user/all/richmenu/$RICH_MENU_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -d '')
if [ "$DEFAULT_STATUS" != "200" ]; then
  echo "❌ Setting default rich menu failed (HTTP $DEFAULT_STATUS):" >&2
  cat /tmp/richmenu_default_body.txt >&2
  exit 1
fi
echo "✅ Set as default"

echo "🎉 Done! Greenman rich menu is now live as the default menu."
echo "(You can discard the unfinished draft in manager.line.biz — it's not needed.)"
