#!/bin/bash
#
# LaunchAgent 설정 스크립트
# 매일 23:30에 자동으로 블로그 발행을 실행합니다.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PLIST_NAME="com.recoblog.daily.plist"
PLIST_SRC="$PROJECT_DIR/config/$PLIST_NAME"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "=== RecoBlog LaunchAgent 설정 ==="
echo ""

# 로그 디렉토리 생성
echo "[1/4] 로그 디렉토리 생성..."
mkdir -p "$PROJECT_DIR/logs"

# 기존 서비스 언로드
echo "[2/4] 기존 서비스 확인 및 제거..."
if launchctl list | grep -q "com.recoblog.daily"; then
    launchctl unload "$PLIST_DST" 2>/dev/null || true
fi

# plist 복사
echo "[3/4] LaunchAgent 설정 파일 복사..."
cp "$PLIST_SRC" "$PLIST_DST"

# 서비스 로드
echo "[4/4] LaunchAgent 서비스 로드..."
launchctl load "$PLIST_DST"

echo ""
echo "=== 설정 완료 ==="
echo ""
echo "설정 파일: $PLIST_DST"
echo "실행 시간: 매일 23:30"
echo "로그 파일: $PROJECT_DIR/logs/publish.log"
echo ""
echo "상태 확인: launchctl list | grep recoblog"
echo "수동 실행: launchctl start com.recoblog.daily"
echo "서비스 중지: launchctl unload $PLIST_DST"
echo ""

# API 키 확인
if [ -z "$ANTHROPIC_API_KEY" ] && [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "⚠️  경고: ANTHROPIC_API_KEY가 설정되지 않았습니다."
    echo "다음 중 하나를 수행해주세요:"
    echo "  1. ~/.zshrc에 'export ANTHROPIC_API_KEY=your-key' 추가"
    echo "  2. $PROJECT_DIR/.env 파일에 'ANTHROPIC_API_KEY=your-key' 추가"
    echo ""
fi
