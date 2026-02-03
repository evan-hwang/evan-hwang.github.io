---
layout: default
title: Home
nav_order: 1
---

# Evan의 학습 기록

Claude Code와 함께 매일 공부한 내용을 정리하는 블로그입니다.
{: .fs-6 .fw-300 }

---

## 최근 학습 기록

{% for post in site.posts limit:5 %}
### [{{ post.title }}]({{ post.url | relative_url }})
<span class="text-grey-dk-000">{{ post.date | date: "%Y년 %m월 %d일" }}</span>

{{ post.excerpt | strip_html | truncate: 200 }}

---
{% endfor %}

[모든 학습 기록 보기](/posts/){: .btn .btn-primary }

---

## 주제별 문서

| 카테고리 | 설명 |
|:---------|:-----|
| [AI / ML](/docs/ai/) | 인공지능, 머신러닝, LLM 관련 학습 |
| [Kubernetes](/docs/kubernetes/) | 컨테이너 오케스트레이션, K8s 관련 |
| [Python](/docs/python/) | Python 프로그래밍, 라이브러리 |
| [DevOps](/docs/devops/) | 인프라, CI/CD, 자동화 |

---

## About

이 블로그는 [Claude Code](https://claude.com/claude-code)를 사용하여 일일 학습 내용을 자동으로 수집하고 정리합니다.

매일 밤 AI가 오늘의 대화 내용을 분석하여 주제별로 요약한 후 자동으로 게시됩니다.
