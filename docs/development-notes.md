# Development Notes

이 문서는 `python-krforest-api` 로컬 개발 중 반복해서 발생한 환경 이슈와 우회 방법을
기록한다. 경로를 쓸 때는 항상 프로젝트 루트 기준 상대 경로를 사용한다.

## PowerShell 명령

이 환경에서는 `rg` 실행이 권한 문제로 막힐 수 있다. `rg`가 실패하면 같은 명령을
반복하지 말고 PowerShell 기본 명령으로 우회한다.

```powershell
# 파일 목록
Get-ChildItem -Recurse -File

# Python 파일 목록
Get-ChildItem -Recurse -File -Filter *.py

# 텍스트 검색
Select-String -Path src\krforest\*.py,tests\*.py -Pattern "ForestClient"
```

## UTF-8 문서 출력

문서는 UTF-8로 저장한다. 다만 PowerShell 기본 출력 인코딩 때문에 `AGENTS.md`,
`README.md`, `docs/forest-api.md` 같은 한글 문서가 터미널에서 깨져 보일 수 있다.
이 경우 파일이 손상됐다고 판단하기 전에 인코딩을 명시해서 다시 읽는다.

```powershell
Get-Content -Encoding utf8 AGENTS.md
Get-Content -Encoding utf8 README.md
Get-Content -Encoding utf8 docs\forest-api.md
```

PowerShell로 파일을 새로 쓰거나 변환해야 한다면 인코딩을 명시한다.

```powershell
Set-Content -Encoding utf8 -Path docs\development-notes.md -Value $content
```

한글이 실제로 깨졌는지 확인해야 할 때는 Python으로 읽어 터미널 표시 문제와 파일
내용 문제를 구분한다.

```powershell
@'
from pathlib import Path
print(Path("AGENTS.md").read_text(encoding="utf-8")[:200])
'@ | python -
```

## 문서 작성 기준

- 저장소 문서의 파일 위치 정보는 `src/krforest/client.py`처럼 프로젝트 기준 상대
  경로로 작성한다.
- Python 내부 문서, 즉 모듈/클래스/함수/메서드 docstring과 설명 주석은 한글로
  작성한다.
- provider 원문, API 필드명, 코드 식별자는 원문을 보존한다.
