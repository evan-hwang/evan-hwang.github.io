---
layout: default
title: 학습 기록
nav_order: 3
---

# 일일 학습 기록

Claude Code와 함께 공부한 내용을 날짜별로 정리한 기록입니다.

---

{% for post in site.posts %}
## [{{ post.title }}]({{ post.url | relative_url }})

<span class="text-grey-dk-000">{{ post.date | date: "%Y년 %m월 %d일" }}</span>

{% if post.tags.size > 0 %}
{% for tag in post.tags %}
<span class="label label-blue">{{ tag }}</span>
{% endfor %}
{% endif %}

{{ post.excerpt | strip_html | truncate: 300 }}

---
{% endfor %}

{% if site.posts.size == 0 %}
아직 작성된 학습 기록이 없습니다. `/publish-today` 명령으로 오늘의 기록을 생성해보세요!
{% endif %}
