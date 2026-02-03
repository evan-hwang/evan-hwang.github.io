#!/usr/bin/env python3
"""
메인 발행 스크립트 - 대화 수집부터 블로그 발행까지 전체 파이프라인 실행

사용법:
    python3 scripts/publish.py --date today
    python3 scripts/publish.py --date yesterday
    python3 scripts/publish.py --date 2026-02-01
    python3 scripts/publish.py --dry-run
    python3 scripts/publish.py --no-git
"""

import argparse
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 스크립트 디렉토리를 path에 추가
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir.parent))

from scripts.collect_conversations import ConversationCollector
from scripts.generate_blog_post import BlogPostGenerator


def parse_date(date_str: str) -> datetime:
    """날짜 문자열 파싱"""
    if date_str == 'today':
        return datetime.now()
    elif date_str == 'yesterday':
        return datetime.now() - timedelta(days=1)
    elif date_str == 'week':
        # 주간 요약은 일주일 전부터 오늘까지
        return datetime.now()
    else:
        return datetime.strptime(date_str, '%Y-%m-%d')


def git_commit_and_push(blog_dir: Path, target_date: datetime) -> bool:
    """Git 커밋 및 푸시"""
    try:
        # 변경사항 확인
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=blog_dir,
            capture_output=True,
            text=True
        )

        if not result.stdout.strip():
            print("[정보] 커밋할 변경사항이 없습니다.")
            return True

        # 스테이징
        subprocess.run(['git', 'add', '.'], cwd=blog_dir, check=True)

        # 커밋
        commit_msg = f"Add daily learning post: {target_date.strftime('%Y-%m-%d')}"
        subprocess.run(
            ['git', 'commit', '-m', commit_msg],
            cwd=blog_dir,
            check=True
        )

        # 푸시
        subprocess.run(['git', 'push'], cwd=blog_dir, check=True)

        print("[성공] Git 커밋 및 푸시 완료!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"[오류] Git 작업 실패: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Claude Code 대화를 블로그로 발행',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
    python3 publish.py --date today       # 오늘 대화 발행
    python3 publish.py --date yesterday   # 어제 대화 발행
    python3 publish.py --date 2026-02-01  # 특정 날짜 발행
    python3 publish.py --dry-run          # 미리보기만 (저장 안함)
    python3 publish.py --no-git           # Git 커밋/푸시 생략
        """
    )
    parser.add_argument(
        '--date',
        default='today',
        help='발행할 날짜 (today, yesterday, YYYY-MM-DD)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='실제 저장/커밋 없이 미리보기만'
    )
    parser.add_argument(
        '--no-git',
        action='store_true',
        help='Git 커밋/푸시 건너뛰기'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='상세 출력'
    )
    args = parser.parse_args()

    # 날짜 파싱
    try:
        target_date = parse_date(args.date)
    except ValueError:
        print(f"[오류] 잘못된 날짜 형식: {args.date}")
        print("올바른 형식: today, yesterday, YYYY-MM-DD")
        sys.exit(1)

    blog_dir = Path(__file__).parent.parent

    print("=" * 60)
    print(f"  Claude Code 대화 → 블로그 발행")
    print(f"  날짜: {target_date.strftime('%Y년 %m월 %d일')}")
    print("=" * 60)

    # Step 1: 대화 수집
    print(f"\n[1/4] 대화 기록 수집 중...")

    collector = ConversationCollector()
    conversations = collector.collect_all(target_date)

    if not conversations:
        print("\n[완료] 해당 날짜에 대화 기록이 없습니다.")
        sys.exit(0)

    stats = collector.get_statistics(conversations)
    print(f"  - {stats['total_conversations']}개 세션 발견")
    print(f"  - {stats['total_messages']}개 메시지")
    print(f"  - {stats['project_count']}개 프로젝트")

    if args.verbose:
        for project in stats['projects']:
            print(f"    - {Path(project).name}")

    # Step 2: 블로그 포스트 생성
    print(f"\n[2/4] 블로그 포스트 생성 중...")

    try:
        generator = BlogPostGenerator()
    except ValueError as e:
        print(f"\n[오류] {e}")
        sys.exit(1)

    post_content = generator.generate_post(conversations, target_date)

    if args.dry_run:
        print("\n" + "=" * 60)
        print("  [미리보기 모드] 생성된 포스트:")
        print("=" * 60)
        print(post_content[:3000])
        if len(post_content) > 3000:
            print(f"\n... (총 {len(post_content)}자, 생략됨)")
        print("\n" + "=" * 60)
        print("[완료] 미리보기 모드 - 파일이 저장되지 않았습니다.")
        sys.exit(0)

    # Step 3: 포스트 저장
    print(f"\n[3/4] 포스트 저장 중...")

    filepath = generator.save_post(post_content, target_date)
    print(f"  저장됨: {filepath}")

    # Step 4: Git 커밋 및 푸시
    if not args.no_git:
        print(f"\n[4/4] Git 커밋 및 푸시 중...")
        success = git_commit_and_push(blog_dir, target_date)
        if not success:
            print("[경고] Git 작업에 실패했습니다. 파일은 저장되었습니다.")
    else:
        print(f"\n[4/4] Git 커밋/푸시 건너뜀 (--no-git)")

    # 완료 메시지
    print("\n" + "=" * 60)
    print(f"  [완료] 블로그 포스트 발행 완료!")
    print(f"  파일: {filepath}")
    if not args.no_git:
        print(f"  URL: https://evan-hwang.github.io/posts/{target_date.strftime('%Y/%m/%d')}/daily-learning/")
    print("=" * 60)


if __name__ == '__main__':
    main()
