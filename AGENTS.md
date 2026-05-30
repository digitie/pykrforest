# AGENTS.md

이 문서는 `python-krforest-api`에서 에이전트가 작업할 때의 진입점(Entrypoint)이다.

## 문서 언어 정책

이 저장소의 모든 Markdown/RST 문서는 한글로 작성한다. 공식 API 필드명, 코드 식별자, 명령어, URL, provider 원문처럼 그대로 보존해야 하는 값만 영어를 유지한다.

## 읽어야 할 문서 (순서대로)

1. `SKILL.md` — 정체성, 빠른 시작, 절대 규칙(DO NOT), 책임 모듈 경계, 작업 후 체크리스트
2. `docs/resume.md` — 현재 진척도와 이어서 해야 할 "다음 작업"
3. `docs/tasks.md` — 프로젝트 백로그(TODO/DONE)
4. `docs/decisions.md` — ADR 표준 형식과 누적 의사결정
5. `docs/journal.md` — 작업 변경 이력(역시간순)
6. `README.md` — 사용자 가이드 및 패키지 개요

## 우선순위

1. 사용자 요청
2. `AGENTS.md` 및 `SKILL.md`의 절대 규칙
3. `docs/decisions.md`의 ADR
4. `docs/forest-api.md`, `README.md` 등 도메인 문서
5. 기존 코드와 테스트 패턴
6. 최소 범위의 되돌리기 쉬운 변경

## 개발 환경 정책

- **에이전트별 고정 worktree**: ChatGPT Codex는 `F:\dev\python-krforest-api-codex`, Claude Code는 `F:\dev\python-krforest-api-claude`, Google Antigravity 2.0은 `F:\dev\python-krforest-api-antigravity`를 사용한다. 작업마다 브랜치만 새로 만들고, CodeGraph는 worktree마다 1회 `codegraph init -i` 후 `codegraph sync`로 유지한다.

세부 개발 규칙은 `SKILL.md`를 최우선으로 따른다.
