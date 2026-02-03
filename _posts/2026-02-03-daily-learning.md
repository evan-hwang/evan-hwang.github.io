---
layout: default
title: "2026-02-03 일일 학습 기록"
parent: 학습 기록
nav_order: 1
---

# 2026‑02‑03 일일 학습 기록

오늘은 **Claude Code**의 대화 기록 저장 메커니즘을 파악하고, Jekyll + Just the Docs 테마 기반 블로그 자동 게시 시스템을 설계했으며, `pd-disaggregation`, `gpu‑cli` 두 프로젝트를 탐색했습니다. 아래에서는 작업을 **주제별**로 정리하고, 핵심 개념·배운 점을 요약합니다.

---  

## 1️⃣ Claude Code 대화 기록 저장 구조 & 포맷  

### 핵심 개념
| 구분 | 경로 | 주요 파일 | 파일 형식 | 비고 |
|------|------|-----------|-----------|------|
| **전역 히스토리** | `~/.claude/history.jsonl` | ‑ | JSONL (줄마다 독립 JSON) | 전체 대화 시퀀스 |
| **프로젝트별** | `~/.claude/projects/{encoded‑path}/` | `agent-{agentId}.jsonl`, `{sessionId}.jsonl` | JSONL | 프로젝트‑별 세션·에이전트 기록 |
| **트랜스크립트** | `~/.claude/transcripts/` | ‑ | JSONL | 텍스트 전사 |
| **파일 히스토리** | `~/.claude/file-history/` | ‑ | JSONL | 파일 변동 내역 |
| **TODO 리스트** | `~/.claude/todos/` | `*.json` | JSON | 작업 관리 |
| **셸 스냅샷** | `~/.claude/shell‑snapshots/` | ‑ | binary / 텍스트 | 쉘 환경 캡쳐 |

### 주요 JSONL 샘플  

*전역 히스토리*  

```json
{
  "display": "아직 반여안되어있는데? 내가 뭔가 리프레시 해야헤?",
  "pastedContents": {},
  "timestamp": 1770076762442,
  "project": "/Users/evanhwang/my-github/project/gpu-cli",
  "sessionId": "56af2614-e9c4-4140-b065-50f29abf3e92"
}
```

*프로젝트‑agent 파일*  

```json
{
  "cwd": "/Users/evanhwang/my-github/project/recoblog",
  "sessionId": "643c4b7b-6b00-4078-8316-3dfda0ce580a",
  "agentId": "71f79aaa",
  "version": "2.0.57",
  "message": {
    "model": "claude-haiku-4-5-20251001",
    "id": "msg_01Cm8f9a8uUN9q33BkpzjXLe",
    "role": "assistant",
    "content": [
      { "type": "text", "text": "I'm ready to help! I'm Claude Code..." }
    ],
    "usage": { "input_tokens": 741, "output_tokens": 139 }
  },
  "timestamp": "2026-02-02T23:24:50.172Z"
}
```

### 배운 점
- **JSONL**은 라인 단위 파싱이 가능해 대용량 로그를 스트리밍 처리하기에 최적.  
- `project` 필드는 절대 경로를 그대로 저장해, 여러 프로젝트를 구분하는데 활용 가능.  
- `sessionId`‑`agentId` 조합으로 **하위 세션(사이드체인)**을 구분할 수 있다.  

---  

## 2️⃣ Just the Docs 테마 기반 Jekyll 블로그 구조  

### 핵심 디렉터리  

```
recoblog/
├─ .github/
│   └─ workflows/pages.yml          # GitHub Pages 자동 배포
├─ .claude/
│   └─ commands/publish-today.md    # 슬래시 커맨드 정의
├─ _config.yml                      # Jekyll 전역 설정 (Just the Docs)
├─ _data/
│   └─ navigation.yml               # 사이드바/탐색 정의 (옵션)
├─ _includes/                       # 공통 템플릿
├─ _layouts/                        # 레이아웃 (default, page, post)
├─ _posts/
│   └─ 2026-02-03-daily-learning.md # 오늘 만든 포스트 (Markdown)
├─ assets/images/                   # 이미지 정적 파일
├─ docs/
│   ├─ index.md                     # 문서 홈
│   ├─ ai/
│   │   ├─ index.md
│   │   └─ llm-basics.md
│   └─ kubernetes/
│       ├─ index.md
│       └─ gpu-schedule.md
└─ scripts/                         # 자동화 스크립트
    ├─ collect_conversations.py
    ├─ generate_blog_post.py
    └─ auto_deploy.sh
```

### 주요 설정 (`_config.yml`)

```yaml
title: "Recoblog"
theme: just-the-docs
color_scheme: dark
url: "https://yourname.github.io/recoblog"
baseurl: "/recoblog"
aux_links:
  GitHub: https://github.com/yourname/recoblog
```

### 배운 점
- `Just the Docs`는 **사이드바 네비게이션**을 `_data/navigation.yml` 혹은 디렉터리 구조 기반 자동 생성으로 관리한다.  
- `_posts` 에 저장된 마크다운은 `jekyll-feed` 와 `jekyll-seo-tag` 플러그인과 함께 자동으로 **RSS/SEO**가 적용된다.  
- `docs/` 아래에 카테고리 폴더를 만들면 **버전 관리**와 **다중 페이지** 구성이 쉬워진다.  

---  

## 3️⃣ Claude Code 슬래시 커맨드와 자동 블로그 게시 파이프라인  

### 슬래시 커맨드 정의 (`.claude/commands/publish-today.md`)

```markdown
# /publish-today
description: 오늘의 학습 기록을 자동으로 블로그에 게시합니다.
arguments:
  - name: date
    type: string
    description: "YYYY-MM-DD 형식 (default: 오늘)"
    required: false
```

### 파이프라인 흐름  

```
┌─────────────────────┐
│  Claude 대화 기록   │
│  (~/.claude/*.jsonl)│
└───────┬─────────────┘
        ▼
┌─────────────────────┐   Claude API (요약)
│  collect_conversations.py  │ ──►  요약 텍스트
└───────┬─────────────┘
        ▼
┌─────────────────────┐
│  generate_blog_post.py   │  →  _posts/YYYY-MM-DD-daily-learning.md
└───────┬─────────────┘
        ▼
┌─────────────────────┐
│  git commit & push │
└───────┬─────────────┘
        ▼
┌─────────────────────┐
│  GitHub Actions → GitHub Pages
└─────────────────────┘
```

#### `collect_conversations.py` 핵심 코드

```python
import json, pathlib, datetime

BASE = pathlib.Path.home() / ".claude"
today = datetime.date.today().isoformat()

def load_jsonl(p: pathlib.Path):
    with p.open() as f:
        for line in f:
            yield json.loads(line)

def filter_today():
    for p in (BASE / "projects").rglob("*.jsonl"):
        for obj in load_jsonl(p):
            ts = datetime.datetime.fromtimestamp(obj["timestamp"]/1000).date()
            if ts.isoformat() == today:
                yield obj

if __name__ == "__main__":
    for msg in filter_today():
        print(msg["display"])
```

#### `generate_blog_post.py` 핵심 흐름

```python
import os, frontmatter, datetime
from openai import OpenAI   # Claude API wrapper 사용

def summarize(messages):
    client = OpenAI(api_key=os.getenv("CLAUDE_API_KEY"))
    resp = client.chat.completions.create(
        model="claude-3-haiku-20240307",
        messages=[{"role":"user","content": "\n".join(messages)}],
        max_tokens=1500,
    )
    return resp.choices[0].message.content

if __name__ == "__main__":
    msgs = list(filter_today())
    summary = summarize([m["display"] for m in msgs])

    post = frontmatter.Post(summary)
    post["layout"] = "post"
    post["title"] = f"{datetime.date.today().isoformat()} 일일 학습 기록"
    post["date"] = datetime.datetime.now()
    post_path = pathlib.Path("_posts") / f"{datetime.date.today().isoformat()}-daily-learning.md"
    post_path.write_text(frontmatter.dumps(post))
```

### 배운 점
- **슬래시 커맨드**는 Claude Code에 명령형 인터페이스를 제공해, 한 줄 호출로 전체 파이프라인을 트리거한다.  
- `OpenAI`‑compatible 클라이언트를 이용해 **Claude API**에 요약 요청을 보낼 수 있다 (키는 `CLAUDE_API_KEY`).  
- `frontmatter` 파이썬 패키지는 YAML 헤더를 손쉽게 삽입·수정하게 해준다.  

---  

## 4️⃣ 자동 실행 (launchd + cron)  

| 방식 | 파일 위치 | 주요 내용 |
|------|-----------|-----------|
| **launchd** (macOS) | `~/Library/LaunchAgents/com.recoblog.daily.plist` | 매일 02:00에 `scripts/auto_deploy.sh` 실행 |
| **cron** (Linux) | `/etc/cron.d/recoblog` | `0 2 * * * /usr/bin/python3 /path/to/generate_blog_post.py` |

### 예시 `launchd` plist

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.recoblog.daily</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/bin/python3</string>
    <string>/Users/evanhwang/my-github/project/recoblog/scripts/auto_deploy.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>2</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key><string>/tmp/recoblog.out</string>
  <key>StandardErrorPath</key><string>/tmp/recoblog.err</string>
</dict>
</plist>
```

### `auto_deploy.sh` 핵심 흐름

```bash
#!/bin/bash
set -e
cd "$(dirname "$0")/.."
git pull
python scripts/generate_blog_post.py
git add _posts/*.md
git commit -m "🤖 $(date +%F) 자동 학습 기록"
git push origin main
```

**배운 점**  
- `launchd`는 **macOS 전용**이며, `cron`보다 로그 관리가 편리하다.  
- 배포 자동화 스크립트는 **실패 시 이메일 알림**을 추가하면 운영 안정성이 높아진다.  

---  

## 5️⃣ Claude API 활용 팁  

| 단계 | 내용 | 참고 코드 |
|------|------|------------|
| 1️⃣ 인증 | `CLAUDE_API_KEY` 환경 변수 설정 | `export CLAUDE_API_KEY=..."` |
| 2️⃣ 클라이언트 초기화 | `OpenAI` wrapper 사용 (Claude 호환) | `client = OpenAI(api_key=os.getenv("CLAUDE_API_KEY"))` |
| 3️⃣ 요약 요청 | `max_tokens`, `temperature=0` 권장 | `client.chat.completions.create(model="claude-3-haiku-20240307", ...)` |
| 4️⃣ 오류 처리 | `try/except OpenAIError` | `except OpenAIError as e: print(e)` |
| 5️⃣ 비용 모니터링 | `usage.input_tokens`·`output_tokens` 로그 | `print(resp.usage)` |

**핵심 포인트**  
- Claude 모델은 **컨텍스트 길이 제한**이 있기에, 하루 전체 로그를 한 번에 보내면 토큰 초과가 발생한다.  
  → **시간대별** 혹은 **topic 별**로 나눠서 요약을 여러 차례 호출한다.  
- `system` 프롬트를 활용해 *“다음 대화 기록을 주제별로 정리해 주세요.”* 와 같이 **구조화된 출력**을 강제할 수 있다.  

---  

## 6️⃣ 프로젝트 탐색 요약  

### 6.1 `pd-disaggregation`  

| 탐색 내용 | 핵심 포인트 |
|----------|-------------|
| 레포 구조 확인 | `src/`, `benchmarks/`, `docs/` 디렉터리 존재 |
| 주요 프레임워크 | vLLM, SGLang, llm‑d (reference) |
| 환경 제약 | **읽기 전용**(파일 생성·수정 금지) |
| 목표 | 프리필‑디코드 단계 분리 성능 검증 (AWS EFA) |

> **배운 점** – 대형 LLM 벤치마크를 **프리필/디코드** 단계별로 측정하려면, `vllm` 의 `PrefillEngine` 과 `DecodeEngine` 를 별도 프로파일링 해야 함.  

### 6.2 `gpu-cli`  

| 탐색 내용 | 핵심 포인트 |
|----------|-------------|
| 레포 주요 파일 | `README.md`, `src/kgpu/k8s/client.py`, `src/kgpu/tui/app.py` |
| 기능 | Kubernetes‑GPU 모니터링, TUI 기반 CLI |
| 최근 커밋 | GPU 모니터링 파드 자동 스케줄링 로직 추가 |
| 향후 작업 | **멀티‑GPU 리소스 할당 전략** 구현, 테스트 자동화 CI |

> **배운 점** – `k8s` 클라이언트 코드를 탐색하면서 **CustomResourceDefinition(CRD)** 활용법과 `watch` API 로 실시간 메트릭 수집 방법을 복습했다.  

---  

## 7️⃣ 전체 요약 & 다음 단계  

1. **Claude Code 기록**을 파일 구조·JSONL 포맷까지 완전 파악.  
2. **Just the Docs + Jekyll** 기반 블로그 skeleton 을 설계하고, `_posts` 자동 생성 파이프라인 구현.  
3. **슬래시 커맨드**와 **launchd/cron**을 연결해 매일 02:00 자동 배포 흐름 구축.  
4. **Claude API**를 이용한 토큰‑효율적인 요약 전략 정립.  
5. `pd-disaggregation`·`gpu-cli` 두 프로젝트를 읽기 전용 모드로 탐색하고, 향후 진행 방향을 메모.  

### 다음에 할 일
- `scripts/collect_conversations.py` 를 **시간대별**(아침·점심·저녁)로 분할하여 토큰 제한 회피.  
- `Just the Docs` 사이드바에 **학습 주제**(AI, Kubernetes, GPU) 별 네비게이션 추가.  
- `pd-disaggregation` 에서 **Prefill/Decode** 프로파일링 스크립트 초안 작성.  
- `gpu-cli` 에 **멀티‑GPU 스케줄러** 설계 문서(`docs/kubernetes/gpu-schedule.md`) 작성.  

---  

이상으로 2026‑02‑03 일일 학습 기록을 정리했습니다. 앞으로도 자동화된 기록·요약 파이프라인을 다듬어, **지식 축적을 지속적으로 블로그에 반영**하도록 하겠습니다. 🚀