---
description: 오늘의 Claude Code 대화를 블로그 글로 발행합니다
allowed-tools: Bash(python3:*), Bash(pip:*), Bash(git:*)
---

# 오늘의 학습 기록 발행

오늘 Claude Code로 공부한 내용을 자동으로 정리하여 Jekyll 블로그에 게시합니다.

## 실행 단계:
1. 오늘의 대화 기록 수집
2. AI가 주제별로 요약 및 정리
3. Jekyll 블로그 포스트 생성
4. Git 커밋 및 GitHub Pages 배포

## 실행

```bash
cd /Users/evanhwang/my-github/project/recoblog && source .venv/bin/activate && python3 -m scripts.publish --date today
```

## 참고
- `--dry-run` 옵션으로 미리보기만 할 수 있습니다
- `--no-git` 옵션으로 Git 커밋/푸시를 건너뛸 수 있습니다
- 어제 기록을 발행하려면 `--date yesterday`를 사용하세요
