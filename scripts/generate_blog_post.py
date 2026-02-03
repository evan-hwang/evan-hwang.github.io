#!/usr/bin/env python3
"""
OpenAI 호환 API를 사용하여 대화 내용을 블로그 글로 변환하는 스크립트
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    print("[오류] openai 패키지가 설치되지 않았습니다.")
    print("실행: pip install openai")
    raise

from dotenv import load_dotenv

from .collect_conversations import ConversationCollector, Conversation

# .env 파일 로드
load_dotenv()


class BlogPostGenerator:
    """대화 내용을 블로그 포스트로 변환하는 클래스"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Args:
            api_key: OpenAI 호환 API 키 (없으면 환경변수에서 로드)
            base_url: API 엔드포인트 URL (없으면 환경변수에서 로드)
        """
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.base_url = base_url or os.environ.get('OPENAI_BASE_URL')
        self.model = os.environ.get('OPENAI_MODEL', 'gpt-4o')

        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY가 설정되지 않았습니다.\n"
                "환경변수로 설정하거나 .env 파일에 추가해주세요."
            )

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.blog_dir = Path(__file__).parent.parent
        self.posts_dir = self.blog_dir / "docs" / "learning-records"
        self.docs_dir = self.blog_dir / "docs"

    def generate_post(
        self,
        conversations: list[Conversation],
        target_date: datetime
    ) -> str:
        """
        대화 내용을 블로그 포스트로 변환

        Args:
            conversations: 변환할 대화 리스트
            target_date: 포스트 날짜

        Returns:
            마크다운 형식의 블로그 포스트
        """
        collector = ConversationCollector()
        formatted_content = collector.format_for_summary(conversations)
        stats = collector.get_statistics(conversations)

        # 프로젝트 목록 추출
        project_names = [Path(p).name for p in stats['projects']]

        prompt = f"""다음은 오늘 ({target_date.strftime('%Y년 %m월 %d일')}) Claude Code로 작업한 대화 기록입니다.
이 대화들을 분석하여 Jekyll 블로그 포스트 (Just the Docs 테마)로 작성해주세요.

## 요청사항:
1. 오늘 학습하거나 작업한 내용을 주제별로 정리해주세요
2. 각 주제에 대해 핵심 개념과 배운 점을 요약해주세요
3. 코드 예시가 있다면 중요한 부분만 포함해주세요
4. 한국어로 작성해주세요
5. 마크다운 형식을 사용해주세요

## 출력 형식:
YAML 프론트매터로 시작하고, 그 다음 본문 내용을 작성해주세요.

프론트매터 예시:
```
---
layout: default
title: "제목"
parent: 학습 기록
nav_order: 1
---

# 제목

본문 내용...
```

## 통계:
- 총 대화 세션: {stats['total_conversations']}개
- 총 메시지: {stats['total_messages']}개 (사용자 {stats['user_messages']}개, Claude {stats['assistant_messages']}개)
- 작업한 프로젝트: {', '.join(project_names)}

## 대화 내용:
{formatted_content[:80000]}

## 주의사항:
- 코드 블록에는 적절한 언어 표시를 해주세요
- 너무 길거나 반복적인 내용은 요약해주세요
- 핵심 학습 포인트를 강조해주세요
- 실제로 배운 내용이나 해결한 문제 위주로 정리해주세요
"""

        print(f"[정보] {self.model} API로 블로그 글 생성 중...")

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content

    def generate_title_and_tags(
        self,
        content: str,
        target_date: datetime
    ) -> tuple[str, list[str]]:
        """
        콘텐츠에서 제목과 태그 추출

        Args:
            content: 블로그 포스트 내용
            target_date: 포스트 날짜

        Returns:
            (제목, 태그 리스트) 튜플
        """
        prompt = f"""다음 블로그 포스트의 내용을 분석하여 적절한 제목과 태그를 추천해주세요.

## 포스트 내용 (처음 3000자):
{content[:3000]}

## 요청:
1. 포스트의 핵심 주제를 반영한 간결한 한국어 제목 (20자 이내)
2. 관련 기술 태그 3-5개 (영문, 소문자, 하이픈 사용)

## 출력 형식 (JSON):
{{"title": "제목", "tags": ["tag1", "tag2", "tag3"]}}

JSON만 출력해주세요.
"""

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        import json
        try:
            result = json.loads(response.choices[0].message.content)
            return result.get('title', f'{target_date.strftime("%Y-%m-%d")} 학습 기록'), result.get('tags', [])
        except json.JSONDecodeError:
            return f'{target_date.strftime("%Y-%m-%d")} 학습 기록', ['til', 'claude-code']

    def ensure_frontmatter(
        self,
        content: str,
        target_date: datetime,
        title: Optional[str] = None,
        tags: Optional[list[str]] = None
    ) -> str:
        """
        프론트매터가 있는지 확인하고, 없으면 추가

        Args:
            content: 블로그 포스트 내용
            target_date: 포스트 날짜
            title: 포스트 제목 (선택)
            tags: 포스트 태그 (선택)

        Returns:
            프론트매터가 포함된 콘텐츠
        """
        if content.strip().startswith('---'):
            return content

        if not title:
            title = f"{target_date.strftime('%Y년 %m월 %d일')} 학습 기록"

        if not tags:
            tags = ['til', 'claude-code']

        tags_str = ', '.join(tags)
        frontmatter = f"""---
layout: default
title: "{title}"
parent: 학습 기록
date: {target_date.strftime('%Y-%m-%d')}
tags: [{tags_str}]
---

"""
        return frontmatter + content

    def save_post(
        self,
        content: str,
        target_date: datetime,
        filename: Optional[str] = None
    ) -> Path:
        """
        블로그 포스트를 파일로 저장

        Args:
            content: 저장할 콘텐츠
            target_date: 포스트 날짜
            filename: 파일명 (선택, 기본값: YYYY-MM-DD-daily-learning.md)

        Returns:
            저장된 파일 경로
        """
        self.posts_dir.mkdir(exist_ok=True)

        if not filename:
            filename = f"{target_date.strftime('%Y-%m-%d')}-daily-learning.md"

        filepath = self.posts_dir / filename

        # 프론트매터 확인 및 추가
        content = self.ensure_frontmatter(content, target_date)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"[정보] 포스트 저장됨: {filepath}")
        return filepath

    def save_to_docs(
        self,
        content: str,
        category: str,
        title: str
    ) -> Path:
        """
        주제별 문서로 저장

        Args:
            content: 저장할 콘텐츠
            category: 카테고리 (ai, kubernetes, python, devops 등)
            title: 문서 제목

        Returns:
            저장된 파일 경로
        """
        category_dir = self.docs_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)

        # 파일명 생성 (제목에서 추출)
        safe_title = title.lower()
        safe_title = safe_title.replace(' ', '-').replace('/', '-')
        safe_title = ''.join(c for c in safe_title if c.isalnum() or c == '-')
        filepath = category_dir / f"{safe_title}.md"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"[정보] 문서 저장됨: {filepath}")
        return filepath


def main():
    """테스트용 메인 함수"""
    from datetime import datetime
    from .collect_conversations import ConversationCollector

    collector = ConversationCollector()
    today = datetime.now()

    print(f"=== {today.strftime('%Y-%m-%d')} 블로그 포스트 생성 테스트 ===\n")

    # 대화 수집
    conversations = collector.collect_all(today)

    if not conversations:
        print("오늘 대화 기록이 없습니다.")
        return

    # 블로그 포스트 생성
    generator = BlogPostGenerator()
    post_content = generator.generate_post(conversations, today)

    print("\n=== 생성된 포스트 (처음 2000자) ===")
    print(post_content[:2000])


if __name__ == '__main__':
    main()
