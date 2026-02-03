#!/usr/bin/env python3
"""
Claude Code 대화 기록 수집 스크립트

대화 기록 위치:
- 글로벌 기록: ~/.claude/history.jsonl
  - 형식: {"display": "메시지", "timestamp": 밀리초, "project": "경로", "sessionId": "uuid"}
- 프로젝트별 상세 기록: ~/.claude/projects/{encoded-path}/agent-{agentId}.jsonl
  - 형식: 완전한 대화 내용 (user, assistant 메시지 포함)
  - timestamp는 ISO 8601 형식
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Message:
    """단일 메시지를 나타내는 데이터 클래스"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    project: str
    session_id: str


@dataclass
class Conversation:
    """하나의 대화 세션을 나타내는 데이터 클래스"""
    project: str
    session_id: str
    agent_id: str = ""
    messages: list[Message] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class ConversationCollector:
    """Claude Code 대화 기록을 수집하는 클래스"""

    def __init__(self):
        self.claude_dir = Path.home() / ".claude"
        self.history_file = self.claude_dir / "history.jsonl"
        self.projects_dir = self.claude_dir / "projects"

    def get_today_sessions(self, target_date: datetime) -> dict[str, set[str]]:
        """
        history.jsonl에서 특정 날짜의 세션 ID들을 프로젝트별로 수집

        Args:
            target_date: 수집할 날짜

        Returns:
            dict[project_path, set[session_ids]]
        """
        sessions_by_project: dict[str, set[str]] = {}

        if not self.history_file.exists():
            print(f"[경고] history.jsonl 파일이 없습니다: {self.history_file}")
            return sessions_by_project

        # 타겟 날짜의 시작/끝 타임스탬프 (밀리초)
        day_start = datetime.combine(target_date.date(), datetime.min.time())
        day_end = day_start + timedelta(days=1)
        start_ts = int(day_start.timestamp() * 1000)
        end_ts = int(day_end.timestamp() * 1000)

        with open(self.history_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    ts = entry.get('timestamp', 0)
                    if start_ts <= ts < end_ts:
                        project = entry.get('project', '')
                        session_id = entry.get('sessionId', '')
                        if project and session_id:
                            if project not in sessions_by_project:
                                sessions_by_project[project] = set()
                            sessions_by_project[project].add(session_id)
                except json.JSONDecodeError:
                    continue

        return sessions_by_project

    def encode_project_path(self, project_path: str) -> str:
        """프로젝트 경로를 Claude 디렉토리 형식으로 인코딩"""
        # Claude는 '/'를 '-'로 변환하여 디렉토리명으로 사용
        return project_path.replace('/', '-')

    def collect_project_conversations(
        self,
        project_path: str,
        session_ids: set[str],
        target_date: datetime
    ) -> list[Conversation]:
        """
        특정 프로젝트의 agent-*.jsonl 파일에서 대화 수집

        Args:
            project_path: 프로젝트 절대 경로
            session_ids: 수집할 세션 ID 세트
            target_date: 대상 날짜

        Returns:
            수집된 Conversation 리스트
        """
        conversations: list[Conversation] = []
        encoded_path = self.encode_project_path(project_path)
        project_dir = self.projects_dir / encoded_path

        if not project_dir.exists():
            print(f"[경고] 프로젝트 디렉토리가 없습니다: {project_dir}")
            return conversations

        # 타겟 날짜 범위 (UTC 기준)
        day_start = datetime.combine(target_date.date(), datetime.min.time())
        day_end = day_start + timedelta(days=1)

        # agent-*.jsonl 파일들 처리
        for agent_file in project_dir.glob("agent-*.jsonl"):
            agent_id = agent_file.stem.replace('agent-', '')
            conversation = Conversation(
                project=project_path,
                session_id="",
                agent_id=agent_id
            )

            try:
                with open(agent_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line)

                            # 세션 ID 추출
                            entry_session = entry.get('sessionId', '')
                            if not conversation.session_id and entry_session:
                                conversation.session_id = entry_session

                            # 타임스탬프 파싱 (ISO 8601 형식)
                            ts_str = entry.get('timestamp', '')
                            if not ts_str:
                                continue

                            # ISO 8601 파싱
                            ts = self._parse_timestamp(ts_str)
                            if ts is None:
                                continue

                            # 타겟 날짜 필터링 (로컬 시간 기준)
                            ts_local = ts.replace(tzinfo=None)
                            if not (day_start <= ts_local < day_end):
                                continue

                            # 메시지 타입 확인
                            msg_type = entry.get('type', '')
                            message_data = entry.get('message', {})

                            if msg_type in ('user', 'assistant'):
                                role = message_data.get('role', msg_type)
                                content_parts = message_data.get('content', [])

                                # 텍스트 콘텐츠 추출
                                text_content = self._extract_text_content(content_parts)

                                if text_content and len(text_content.strip()) > 0:
                                    msg = Message(
                                        role=role,
                                        content=text_content,
                                        timestamp=ts,
                                        project=project_path,
                                        session_id=entry_session
                                    )
                                    conversation.messages.append(msg)

                        except (json.JSONDecodeError, KeyError, ValueError) as e:
                            continue

            except IOError as e:
                print(f"[경고] 파일 읽기 오류: {agent_file}: {e}")
                continue

            if conversation.messages:
                conversation.messages.sort(key=lambda m: m.timestamp)
                conversation.start_time = conversation.messages[0].timestamp
                conversation.end_time = conversation.messages[-1].timestamp
                conversations.append(conversation)

        return conversations

    def _parse_timestamp(self, ts_str: str) -> Optional[datetime]:
        """ISO 8601 타임스탬프 파싱"""
        try:
            # 'Z' 를 '+00:00'으로 변환
            ts_str = ts_str.replace('Z', '+00:00')
            return datetime.fromisoformat(ts_str)
        except ValueError:
            return None

    def _extract_text_content(self, content_parts) -> str:
        """메시지 content에서 텍스트만 추출"""
        if isinstance(content_parts, str):
            return content_parts

        if not isinstance(content_parts, list):
            return ""

        texts = []
        for part in content_parts:
            if isinstance(part, dict):
                if part.get('type') == 'text':
                    text = part.get('text', '')
                    if text:
                        texts.append(text)
            elif isinstance(part, str):
                texts.append(part)

        return '\n'.join(texts)

    def collect_all(self, target_date: datetime) -> list[Conversation]:
        """
        특정 날짜의 모든 대화 수집

        Args:
            target_date: 수집할 날짜

        Returns:
            모든 프로젝트의 Conversation 리스트
        """
        all_conversations: list[Conversation] = []

        # history.jsonl에서 오늘 세션 정보 수집
        sessions_by_project = self.get_today_sessions(target_date)

        print(f"[정보] {len(sessions_by_project)}개 프로젝트에서 대화 발견")

        for project_path, session_ids in sessions_by_project.items():
            print(f"  - {Path(project_path).name}: {len(session_ids)}개 세션")
            conversations = self.collect_project_conversations(
                project_path, session_ids, target_date
            )
            all_conversations.extend(conversations)

        # 시작 시간순 정렬
        all_conversations.sort(key=lambda c: c.start_time or datetime.min)

        return all_conversations

    def format_for_summary(self, conversations: list[Conversation]) -> str:
        """
        AI 요약을 위한 텍스트 포맷

        Args:
            conversations: 포맷할 Conversation 리스트

        Returns:
            포맷된 문자열
        """
        output_parts = []

        for conv in conversations:
            project_name = Path(conv.project).name
            start_str = conv.start_time.strftime('%H:%M') if conv.start_time else 'N/A'
            end_str = conv.end_time.strftime('%H:%M') if conv.end_time else 'N/A'

            output_parts.append(f"\n## 프로젝트: {project_name}")
            output_parts.append(f"시간: {start_str} ~ {end_str}")
            output_parts.append(f"메시지 수: {len(conv.messages)}개")
            output_parts.append("-" * 50)

            for msg in conv.messages:
                role_label = "사용자" if msg.role == 'user' else "Claude"
                # 너무 긴 메시지는 잘라서 표시
                content = msg.content[:3000] if len(msg.content) > 3000 else msg.content
                output_parts.append(f"\n### {role_label}:")
                output_parts.append(content)

        return '\n'.join(output_parts)

    def get_statistics(self, conversations: list[Conversation]) -> dict:
        """대화 통계 생성"""
        total_messages = sum(len(c.messages) for c in conversations)
        user_messages = sum(
            sum(1 for m in c.messages if m.role == 'user')
            for c in conversations
        )
        assistant_messages = total_messages - user_messages

        projects = list(set(c.project for c in conversations))

        return {
            'total_conversations': len(conversations),
            'total_messages': total_messages,
            'user_messages': user_messages,
            'assistant_messages': assistant_messages,
            'projects': projects,
            'project_count': len(projects),
        }


def main():
    """테스트용 메인 함수"""
    from datetime import datetime

    collector = ConversationCollector()
    today = datetime.now()

    print(f"=== {today.strftime('%Y-%m-%d')} 대화 수집 ===\n")

    conversations = collector.collect_all(today)

    if not conversations:
        print("오늘 대화 기록이 없습니다.")
        return

    stats = collector.get_statistics(conversations)
    print(f"\n=== 통계 ===")
    print(f"총 대화 세션: {stats['total_conversations']}개")
    print(f"총 메시지: {stats['total_messages']}개")
    print(f"  - 사용자: {stats['user_messages']}개")
    print(f"  - Claude: {stats['assistant_messages']}개")
    print(f"프로젝트: {stats['project_count']}개")

    # 포맷된 내용 미리보기
    formatted = collector.format_for_summary(conversations)
    print(f"\n=== 포맷된 내용 (처음 2000자) ===")
    print(formatted[:2000])


if __name__ == '__main__':
    main()
