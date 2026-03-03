---
layout: default
title: "Claude Code Skills 딥다이브: 구조와 동작 원리"
parent: 파인만 학습
nav_order: 20260303
date: 2026-03-03
tags: [claude-code, skills]
---

# Claude Code Skills 딥다이브: 구조와 동작 원리

Claude Code를 쓰다 보면 반복되는 워크플로우가 생긴다. 코드 리뷰, 배포, 이슈 생성 같은 작업을 매번 프롬프트로 설명하는 건 비효율적이다. **Skills**는 이런 반복 작업을 `.md` 파일 하나로 정의해두고, Claude가 상황에 맞게 알아서 꺼내 쓰도록 만드는 기능이다.

이 글에서는 Skills가 왜 필요한지, 내부적으로 어떻게 동작하는지, 그리고 비슷해 보이는 Commands나 CLAUDE.md와 어떻게 다른지까지 깊이 있게 다룬다.

---

## 배경: Skills가 해결하는 문제

Claude Code에는 이미 `CLAUDE.md`가 있다. 프로젝트의 컨벤션, 빌드 명령어, 주의사항 등을 적어두면 Claude가 매 요청마다 참고한다. 그런데 이 방식에는 한계가 있다.

**CLAUDE.md의 한계:**
- **항상 로드된다.** API 스타일 가이드, 배포 절차, 코드 리뷰 체크리스트를 전부 넣으면 컨텍스트 윈도우를 빠르게 채운다.
- **조건부 로딩이 안 된다.** 배포할 때만 필요한 내용이 코드 작성 중에도 매번 로드된다.
- **호출이 안 된다.** "이 절차대로 해줘"라고 따로 부를 수 없다. 항상 배경 지식으로만 존재한다.

Commands(`.claude/commands/`)도 있었지만, 이건 사용자가 `/이름`으로 직접 호출해야만 동작했다. Claude가 "지금 이 상황에 이 워크플로우가 필요하겠다"고 판단해서 자동으로 꺼내 쓸 수는 없었다.

**Skills는 이 두 가지 문제를 동시에 해결한다:**

1. 평소에는 description(한 줄 설명)만 로드해서 컨텍스트 비용을 최소화한다.
2. 필요할 때만 전체 내용을 로드한다 — 사용자가 직접 호출하거나, Claude가 자동 판단하거나.

---

## 핵심 구조: 이중 로딩 아키텍처

Skills의 핵심 설계는 **"설명은 항상, 본문은 필요할 때만"**이라는 이중 로딩 구조다.

### 파일 구조

```
.claude/skills/my-skill/
├── SKILL.md           # 필수: 메인 지시사항
├── examples/          # 선택: 예시 파일
└── scripts/           # 선택: 실행 스크립트
```

`SKILL.md`의 내부는 두 파트로 나뉜다:

```yaml
---
name: review-code
description: 코드 리뷰를 수행합니다. 코드 변경 후 품질, 보안, 모범 사례를 점검할 때 사용.
allowed-tools: Read, Grep, Glob
---

# 코드 리뷰 절차

1. git diff로 변경사항 확인
2. 보안 취약점 점검
3. 네이밍 컨벤션 확인
...
```

- **Frontmatter** (YAML 블록): 메타데이터. `description`이 핵심이다.
- **본문** (마크다운): Claude에게 주는 실제 지시사항. 프롬프트와 사실상 같다.

### 로딩 흐름

세션이 시작되면 Claude Code는 모든 스킬 파일을 탐색한다. 하지만 **전부 읽지는 않는다.**

```
세션 시작
  │
  ▼
모든 스킬의 frontmatter만 파싱
  │
  ├─ description → Claude의 컨텍스트에 주입 (~50바이트/스킬)
  └─ 본문 → 디스크에 캐시 (아직 로드 안 함)
  │
  ▼
사용자가 대화 시작
  │
  ├─ 사용자가 "/review-code" 입력 → 해당 스킬 본문 로드
  │
  └─ Claude가 대화 맥락과 description 매칭 → 자동으로 본문 로드
```

50개 스킬이 있어도 description만 로드하면 약 2.5KB다. 반면 50개 본문을 전부 로드하면 250KB 이상. 이 차이가 이중 로딩의 존재 이유다.

### 자동 호출은 어떻게 동작하는가

Claude는 매 요청마다 이미 로드된 description들을 본다. 사용자의 요청과 description이 의미적으로 매칭되면, 해당 스킬의 전체 본문을 로드하고 실행한다.

```
사용자: "이 코드 좀 봐줘"
  │
  ▼
Claude가 보유한 description 목록:
  - "코드 리뷰를 수행합니다. 코드 변경 후 품질, 보안..." ← 매칭!
  - "배포를 실행합니다..."
  - "Jira 티켓을 생성합니다..."
  │
  ▼
review-code 스킬 본문 로드 → 실행
```

**이것이 CLAUDE.md와의 결정적 차이다.** CLAUDE.md는 항상 전부 로드되지만, Skills는 필요할 때만 로드된다.

---

## Frontmatter 필드 상세

frontmatter의 각 필드가 스킬의 동작을 제어한다.

| 필드 | 역할 | 기본값 |
|------|------|--------|
| `name` | 슬래시 커맨드 이름 (`/name`으로 호출) | 디렉토리명 |
| `description` | Claude의 자동 호출 판단 기준. 항상 컨텍스트에 로드됨 | - |
| `allowed-tools` | 스킬 실행 중 허용할 도구 제한 | 전체 허용 |
| `disable-model-invocation` | `true`면 Claude가 자동 호출 불가. 사용자만 호출 가능 | `false` |
| `user-invocable` | `false`면 `/` 메뉴에 표시 안 됨. Claude만 사용 | `true` |
| `context` | `fork`면 격리된 서브에이전트에서 실행 | 메인 컨텍스트 |
| `agent` | `context: fork` 시 서브에이전트 타입 지정 | `general-purpose` |
| `model` | 스킬 실행 시 사용할 모델 | 세션 모델 |

### disable-model-invocation vs user-invocable

이 둘은 헷갈리기 쉽다:

```yaml
# 케이스 1: 배포처럼 부작용이 있는 스킬
disable-model-invocation: true
# → description이 컨텍스트에 안 올라감
# → Claude가 절대 자동 실행 불가, 오직 /deploy로만 호출

# 케이스 2: 배경 지식으로만 쓰이는 스킬
user-invocable: false
# → description은 컨텍스트에 올라감 (Claude가 인지)
# → / 메뉴에는 안 보임 (사용자가 직접 호출 불가)
# → Claude가 필요할 때 자동으로 로드
```

실수로 실행되면 안 되는 스킬(배포, 메시지 전송)은 `disable-model-invocation: true`, 참고 자료형 스킬(API 가이드, 컨벤션 문서)은 `user-invocable: false`가 적절하다.

---

## Skills vs Commands vs CLAUDE.md

이 세 가지는 모두 "Claude의 동작을 커스터마이징"하지만, 용도가 다르다.

| | CLAUDE.md | Commands | Skills |
|---|---|---|---|
| **위치** | 프로젝트 루트 | `.claude/commands/` | `.claude/skills/` |
| **로딩** | 항상 전부 로드 | 사용자 호출 시 | description만 항상 + 본문은 필요 시 |
| **자동 호출** | 불가 (항상 배경) | 불가 (수동만) | 가능 (description 매칭) |
| **수동 호출** | 불가 | `/이름` | `/이름` |
| **보조 파일** | 불가 | 단일 .md | 디렉토리 구조 지원 |
| **적합한 용도** | 항상 적용되는 규칙 | 단순 수동 워크플로우 | 조건부 지식 + 재사용 워크플로우 |

### 언제 뭘 써야 하나

**CLAUDE.md**: "항상 알고 있어야 하는 것"
- 빌드 명령어, 코딩 컨벤션, 아키텍처 개요
- 200줄 이내 권장

**Commands**: "내가 부를 때만 실행하는 것"
- 간단한 수동 워크플로우
- 자동 호출이 필요 없는 경우

**Skills**: "상황에 따라 필요한 것"
- API 스타일 가이드, 코드 리뷰 체크리스트
- 도구 제한이 필요한 워크플로우
- 보조 파일(템플릿, 스크립트)이 필요한 경우

---

## 스킬 스코프: 4개 레이어

스킬은 적용 범위에 따라 4단계로 나뉜다. 같은 이름의 스킬이 여러 레벨에 있으면 높은 우선순위가 이긴다.

```
우선순위:  1 (최고)        2            3           4 (최저)
스코프:    Enterprise  →  Personal  →  Project  →  Plugin
위치:      시스템 디렉토리   ~/.claude/    .claude/    플러그인 패키지
적용 범위: 전 사용자        내 모든 프로젝트  현재 프로젝트   활성화된 곳
```

- **Enterprise**: IT 관리자가 설치. 보안 정책, 컴플라이언스 규칙.
- **Personal**: `~/.claude/skills/`. 내 모든 프로젝트에 적용되는 개인 워크플로우.
- **Project**: `.claude/skills/`. git에 커밋해서 팀과 공유.
- **Plugin**: 마켓플레이스나 외부 패키지로 배포.

---

## 고급 패턴

### 동적 컨텍스트 주입

스킬 본문에서 `` !`명령어` `` 구문을 쓰면, Claude가 스킬을 읽기 **전에** 명령어가 실행되고 결과가 삽입된다.

```yaml
---
name: pr-context
description: 현재 PR의 맥락을 파악합니다
---

## 변경된 파일
!`git diff --name-only`

## 최근 커밋
!`git log --oneline -5`

위 맥락을 기반으로 분석해주세요.
```

Claude가 이 스킬을 로드하면, 이미 `git diff`와 `git log`의 결과가 삽입된 상태로 받는다.

### 인자 치환

`$ARGUMENTS`, `$0`, `$1` 등으로 사용자 입력을 받을 수 있다.

```yaml
---
name: fix-issue
description: GitHub 이슈를 수정합니다
argument-hint: "[이슈번호]"
---

GitHub 이슈 $0 을 분석하고 수정하세요.
```

```
/fix-issue 42
→ "GitHub 이슈 42 를 분석하고 수정하세요."
```

### 서브에이전트 격리

`context: fork`를 쓰면 별도 컨텍스트에서 실행된다. 50개 파일을 탐색하는 리서치 작업이 메인 대화를 오염시키지 않는다.

```yaml
---
name: deep-research
description: 코드베이스를 깊이 조사합니다
context: fork
agent: Explore
---

$ARGUMENTS 에 대해 코드베이스를 조사하고 요약해주세요.
```

서브에이전트가 탐색을 마치면 요약만 메인 대화로 돌아온다.

---

## 실전 예시: 이 블로그의 Skills 구성

이 블로그 프로젝트에서 실제로 사용 중인 구성을 예로 들면:

```
.claude/
├── skills/
│   └── feynman-learning.md     # 파인만 학습법 튜터 (자동 호출)
└── commands/
    ├── feynman.md              # /feynman: 학습 세션 시작
    ├── feynman-preview.md      # /feynman-preview: 블로그 미리보기
    └── feynman-publish.md      # /feynman-publish: 블로그 발행
```

- `feynman-learning.md`는 **Skills**다. description에 "파인만 학습법 튜터"라고 적혀 있어, 학습 관련 대화가 시작되면 Claude가 자동으로 로드한다.
- `feynman.md` 등은 **Commands**다. 사용자가 `/feynman`을 입력해야만 실행된다. 블로그 발행처럼 부작용이 있는 작업은 자동 호출되면 안 되기 때문이다.

---

## 마무리

Skills의 핵심을 한 문장으로 정리하면: **"description은 항상 보여주되, 본문은 필요할 때만 로드하는 조건부 프롬프트"**다.

CLAUDE.md가 "항상 알고 있어야 하는 규칙"이라면, Skills는 "필요할 때 꺼내 쓰는 매뉴얼"이다. 이 구분을 이해하면 컨텍스트 윈도우를 효율적으로 쓰면서도 Claude의 동작을 세밀하게 제어할 수 있다.

---

*이 글은 파인만 학습법을 활용하여 깊이 있게 학습한 내용을 정리한 것입니다.*
