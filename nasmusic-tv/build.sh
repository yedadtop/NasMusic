#!/usr/bin/env bash
# 构建 NasMusic 电视端 APK 并安装到电视。
#   ./build.sh          # 构建 + 安装
#   ./build.sh build    # 只构建
#
# 说明：这是纯原生 Android TV 应用，直连 NasMusic 后端 API，
# 不再依赖 frontned 的构建产物——网页版改了不影响这里，反之亦然。
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -W)"
ROOT="$(dirname "$HERE")"
# JDK 17：优先本目录 .tools，其次 android tv 项目里那份（NasMusic 目录下没有）
JDK="$ROOT/.tools/jdk-17.0.20.1+1"
[ -d "$JDK" ] || JDK="C:/Users/yedad/workbuddy-ai/android tv/.tools/jdk-17.0.20.1+1"
TV_HOST="${TV_HOST:-10.0.0.229}"

echo "==> Gradle 构建"
cd "$HERE"
JAVA_HOME="$JDK" ./gradlew assembleRelease --console=plain -q

APK="$HERE/app/build/outputs/apk/release/app-release.apk"
ls -lh "$APK"

if [ "${1:-install}" = "build" ]; then
  echo "构建完成: $APK"
  exit 0
fi

echo "==> 安装到 $TV_HOST"
# 用官方 adb 推送：cleanyourtv 的 adb_shell filesync 在这台盒子上会 300s 超时
TV_HOST="$TV_HOST" bash "$HERE/install.sh"

echo "完成。"
