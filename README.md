# RecoBlog - Claude Code 학습 기록 자동화

Claude Code로 공부한 내용을 자동으로 수집하고 Jekyll 블로그로 발행하는 시스템입니다.

## 기능

- Claude Code 대화 기록 자동 수집
- AI를 활용한 주제별 요약 및 정리
- Jekyll (Just the Docs 테마) 블로그 자동 발행
- 매일 자동 실행 (LaunchAgent)
- Claude Code 슬래시 커맨드 지원

## 빠른 시작

### 1. 의존성 설치

```bash
# Ruby 패키지 설치
bundle install

# Python 가상환경 생성 및 패키지 설치
python3 -m venv .venv
source .venv/bin/activate
pip install anthropic python-dateutil python-dotenv
```

### 2. API 키 설정

```bash
# 방법 1: 환경 변수
export ANTHROPIC_API_KEY="sk-ant-api03-xxxxx"

# 방법 2: .env 파일
echo "ANTHROPIC_API_KEY=sk-ant-api03-xxxxx" > .env
```

API 키는 https://console.anthropic.com/settings/keys 에서 발급받으세요.

### 3. 블로그 발행

```bash
# 오늘 대화 발행
python3 -m scripts.publish --date today

# 미리보기만
python3 -m scripts.publish --date today --dry-run

# 어제 대화 발행
python3 -m scripts.publish --date yesterday
```

## Claude Code 슬래시 커맨드

프로젝트 디렉토리에서 Claude Code를 사용할 때:

```
/publish-today     # 오늘 대화를 블로그로 발행
/publish-preview   # 미리보기 (저장하지 않음)
```

## 자동 실행 설정

매일 23:30에 자동으로 블로그를 발행하려면:

```bash
./scripts/setup_launchd.sh
```

### 자동 실행 관리

```bash
# 상태 확인
launchctl list | grep recoblog

# 수동 실행
launchctl start com.recoblog.daily

# 서비스 중지
launchctl unload ~/Library/LaunchAgents/com.recoblog.daily.plist
```

## 디렉토리 구조

```
recoblog/
├── _config.yml           # Jekyll 설정
├── _posts/               # 블로그 포스트 (자동 생성)
├── docs/                 # 주제별 문서
├── scripts/
│   ├── collect_conversations.py  # 대화 수집
│   ├── generate_blog_post.py     # AI 요약
│   └── publish.py                # 메인 스크립트
├── .claude/commands/     # 슬래시 커맨드
└── config/               # 설정 파일
```

## 대화 기록 위치

Claude Code는 다음 위치에 대화 기록을 저장합니다:

- `~/.claude/history.jsonl` - 글로벌 대화 기록
- `~/.claude/projects/{path}/agent-*.jsonl` - 프로젝트별 상세 기록

## 로컬 개발

```bash
# Jekyll 서버 실행
bundle exec jekyll serve

# 브라우저에서 http://localhost:4000 접속
```

## 배포

GitHub에 푸시하면 GitHub Actions가 자동으로 GitHub Pages에 배포합니다.

배포 URL: https://evan-hwang.github.io

## 라이선스

MIT License
