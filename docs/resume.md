# Resume

현재 `python-krforest-api` 프로젝트의 진척도와 이어서 할 작업을 기록합니다. 새 세션이나 작업 재개 시 이 문서를 가장 먼저 확인하세요.

## 현재 진척도 (2026-05-31)

- **`python-kraddr-base` 의존성 완전 제거.** 좌표는 `latitude: float | None` / `longitude: float | None`, 주소는 `address: str | None`로 평탄화되어 외부 도메인 패키지 없이 동작함. ADR-008.
- `_convert.py`에 `extract_coordinate(row)` / `extract_address(row)` 헬퍼 추가. 결측 sentinel(-99, -999, 0)을 일관 처리.
- `__version__`을 `0.2.0`으로 올림(파괴적 변경). 호환성 부담 의도적으로 단절.
- `pytest` 36 passed / `ruff check` clean / `mypy --strict` clean. mypy 외부 경로 설정도 함께 제거.
- 이전 작업(2026-05-24)에서 정착한 문서 방법론(`SKILL.md`, ADR, journal, resume, tasks)은 그대로 유지하며 ADR-008 추가.
- 에이전트 작업 규칙에 Windows Git(`C:\Program Files\Git\cmd\git.exe`) 사용 원칙을 명시했고, `.codegraph`는 gitignore 대상임을 다시 고정했다.

## 다음 해야 할 작업 (Next Task)

- [ ] PR 본문에 ADR-008 링크와 마이그레이션 가이드(필드명 변경) 정리 후 main에 머지.
- [ ] (백로그) 데이터 반환 스키마 최적화 및 fixture 보강 — `docs/tasks.md` 참조.
- [ ] (백로그) 신규 파일데이터 endpoint 카탈로그 등록.
- [ ] (백로그) `_convert.extract_address`가 주소 문자열만 다루므로, 도로명/지번 분리가 필요한 사용자 시나리오가 생기면 별도 헬퍼 검토.
