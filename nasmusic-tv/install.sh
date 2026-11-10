#!/usr/bin/env bash
# 用官方 adb 推送并安装（tv.py 的 filesync 在这台盒子上会超时）
set -euo pipefail
# Git Bash 会把 /data/... 当成本地路径改写，必须关掉
export MSYS_NO_PATHCONV=1
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -W)"
ADB="C:/Users/yedad/AppData/Local/Android/Sdk/platform-tools/adb.exe"
SERIAL="${TV_HOST:-10.0.0.229}:5555"
APK="$HERE/app/build/outputs/apk/release/app-release.apk"

"$ADB" start-server >/dev/null 2>&1 || true
"$ADB" connect "$SERIAL" >/dev/null
sleep 1

# adb daemon 在这台机器上偶尔会自己退出，重连重试几次
for i in 1 2 3 4; do
  if "$ADB" -s "$SERIAL" push "$APK" /data/local/tmp/nasmusic-tv.apk; then
    break
  fi
  echo "push 失败，第 $i 次重试" >&2
  "$ADB" connect "$SERIAL" >/dev/null
  sleep 2
done
"$ADB" -s "$SERIAL" shell pm install -r -d /data/local/tmp/nasmusic-tv.apk
"$ADB" -s "$SERIAL" shell am start -n com.nasmusic.tv/.MainActivity
