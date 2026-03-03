---
layout: default
title: "파인만 학습: Claude Code Skills의 개념과 구조"
parent: 파인만 학습
nav_order: 20260303
date: 2026-03-03
tags: [feynman, claude-code-skills]
---

# 파인만 학습: Claude Code Skills의 개념과 구조

## 학습 개요

| 항목 | 내용 |
|------|------|
| **주제** | Claude Code Skills의 개념과 구조 |
| **학습 일시** | 2026년 03월 03일 |
| **최종 이해도** | 82점 / 100점 |
| **마스터한 개념** | Skills의 본질, 파일 위치, description 기반 자동 호출, frontmatter 구조 |
| **복습 필요** | Skills vs Commands 세부 차이, allowed-tools 문법, MCP 도구 연동 |

---

## 나의 설명

> 파인만 학습법의 핵심: 12살 아이에게 설명하듯이

Claude Code라는건 마치 아주 똑똑한 로봇에게 컴퓨터 타자로 또는 사진으로 무언가 시킬 수 있는 창구라고 생각하면 된다. 스킬이라는건 마치 게임에서 용사가 사용할 수 있는 파이어볼 스킬처럼, 자주 사용하는 동작을 이 로봇에게 장착시켜주는 거라고 보면 돼. 미리 운영자가 만들어놓은 스킬이 있고, 내가 장착해주는 커스텀 스킬이라는 게 있어.

Claude Code Skills는 Claude라는 로봇이 뭔가를 결정할 때 또는 수행할 때 사용할 수 있는 스킬을 사용자가 미리 지정해주는 거야. `.claude/skills/스킬이름/SKILL.md` 위치에 두고, 그 안에 description 섹션에 어떤 때 나를 쓰라고 명시해두면 클로드가 보고 결정하는 거야!

---

## Q&A 세션

### Q1: 직접 부르는 스킬도 있는 거 아니에요? 로봇이 알아서 고르는 것과 뭐가 달라요?

**나의 답변:**
> 직접 부르는 스킬은 커맨드라고 명령어로 따로 부르는걸로 알고 있는데 확실치 않아. 스킬과 커맨드가 어떻게 구성되는지 이해하긴 어렵지만 둘 다 클로드가 직접 사용하거나 사용자가 직접 호출할 수 있다고 하네?

**피드백:**
거의 맞았다! Commands는 Skills의 단순한 형태다. 둘 다 `/이름`으로 부를 수 있지만, Skills만 Claude가 자동으로 꺼내 쓸 수 있다. Commands(`.claude/commands/`)는 사용자만 호출 가능.

### Q2: .md 파일 안에 뭘 채워넣는 거예요?

**나의 답변:**
> 잘 모르겠어...! 그냥 프롬프트랑 뭐가 다른건지.

**피드백:**
사실 거의 프롬프트가 맞다! 하지만 윗부분에 frontmatter(메타데이터)가 붙는다. `description`(스킬 설명), `allowed-tools`(허용 도구) 등의 설정 정보 + 아래에 실제 지시사항(프롬프트)이 합쳐진 구조.

### Q3: .md 파일은 아무 데나 놓으면 되는 거예요?

**나의 답변:**
> 내가 알기론 skills 하위에 두면 된다고 하던데.

**피드백:**
맞다! Skills는 `.claude/skills/스킬이름/SKILL.md`, Commands는 `.claude/commands/이름.md`에 둔다.

### Q4: Claude가 자동으로 스킬을 고르는 건 어떻게 하는 거예요?

**나의 답변:**
> 사용자가 치는건 `/select-icecream` 하면 되는 거 같은데, 로봇이 알아서 선택하는 건 어떻게 하는지 모르겠네? CLAUDE.md 같은 데 적어둬야 하나?

**피드백:**
CLAUDE.md에 따로 적을 필요 없다! Claude는 모든 스킬의 `description`을 항상 미리 읽어두고 있다. 대화 중 상황이 description과 맞으면 알아서 판단해서 호출한다. 반대로 자동 호출을 막으려면 `disable-model-invocation: true`를 설정.

### Q5: MCP 도구도 allowed-tools에 적는 건가요?

**나의 답변:**
> allowed-tools 같은 거 적을 수 있다던데, Jira MCP 사용하는 스킬도 있던데 MCP도 allowed-tools에 적는 건지 프롬프트 내용에 써야 하는 건지 모르겠네.

**피드백:**
`allowed-tools`에는 Claude Code 기본 도구(Read, Write, Grep 등)만 지정 가능. MCP 도구(Jira, Slack 등)는 프롬프트 본문에 지시사항으로 적어야 한다.

---

## 나만의 비유

> "Claude Code Skills는 마치 식당 요리사들의 행동지침과 비슷하다. 10시가 되면 해야할 일을 미리 스킬처럼 지침화한다. 이 시간엔 요리 재료를 준비해야 하고, 숟가락을 세팅하고 식탁을 닦으세요. 그리고 12시가 되면 손님 맞이 스킬을 지침화한다. 환하게 웃고 문에 가까운 자리부터 안내하세요. 메뉴판은 무릎꿇고 대접하듯 설명해주세요. 이런 것들을 내가 매니저에게 스킬화해서 전달하면 매니저는 실제 수행 시에 동작 전 스킬들을 확인하면서 골라서 지침을 확인하고 동작하게 된다."

**비유 평가:**
매우 적절한 비유! 매니저(Claude)가 상황에 맞는 지침(Skills)을 알아서 꺼내 보고 행동하는 구조가 정확히 매칭된다. 특히 "10시엔 준비 지침, 12시엔 손님맞이 지침"이라는 부분이 description 기반의 상황별 자동 매칭을 잘 표현했다.

---

## 학습 정리

### 핵심 요약
- **Skills는** 사용자가 Claude에게 장착시키는 재사용 가능한 지시사항으로, `.md` 파일에 메타데이터(frontmatter) + 프롬프트를 작성하는 구조다.
- **자동 호출의 핵심은 `description`**: Claude는 모든 스킬의 description을 미리 읽고, 대화 맥락에 맞으면 알아서 해당 스킬을 호출한다.
- **Skills vs Commands**: Skills(`.claude/skills/`)는 자동+수동 호출 모두 가능, Commands(`.claude/commands/`)는 사용자 수동 호출만 가능.
- **allowed-tools로 도구를 제한**할 수 있지만, MCP 도구는 프롬프트 본문에 지시사항으로 작성해야 한다.

### 다음 학습 추천
- **Custom Skill 직접 만들어보기**: 실제로 `.claude/skills/`에 스킬을 만들고 자동 호출이 되는지 테스트
- **Hooks와 Skills의 차이**: 둘 다 Claude 동작을 제어하지만, Hooks는 이벤트 기반 쉘 명령, Skills는 프롬프트 기반

---

*이 포스트는 파인만 학습법을 활용하여 Claude Code와 함께 학습한 내용입니다.*
