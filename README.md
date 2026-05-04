# Image / SVG / PDF / Markdown Viewer

PySide6로 만든 간단한 데스크톱 뷰어입니다. PNG, JPG, SVG, PDF, Markdown 파일을 열어서 볼 수 있고, 마우스와 상단 패널 버튼으로 확대/축소와 이동을 할 수 있습니다.

빌드 결과 실행 파일 이름은 `svgvv.exe`입니다.

## 주요 기능

- PNG, JPG, JPEG 이미지 열기
- SVG 파일 열기
- PDF 파일 열기
- Markdown(.md) 파일 미리보기
- 파일 열기 버튼 또는 Drag & Drop으로 로드
- 마우스 휠로 Zoom
- 상단 `+`, `-`, `Reset` 버튼으로 Zoom
- 현재 Zoom 비율 표시
- 마우스 드래그로 Pan
- 상단 `↑`, `↓`, `←`, `→` 버튼으로 Pan
- PDF 페이지 `Prev`, `Next` 이동
- Markdown 스크롤 페이지 `Prev`, `Next` 이동
- PDF와 Markdown에서 `PgUp`, `PgDn`으로 이전/다음 페이지 이동
- SVG는 벡터 렌더링으로 확대 시 선명도 유지
- PDF는 `QPdfView` 기반 표시로 확대 시 선명도 유지
- Markdown은 텍스트 폰트 크기를 직접 조정해서 확대 시 선명도 유지

## 프로젝트 구조

```text
.
├── pyproject.toml
├── app.spec
├── README.md
├── src/
│   └── my_app/
│       ├── assets/
│       │   ├── app_icon.ico
│       │   └── app_icon.svg
│       ├── __init__.py
│       ├── clean.py
│       └── main.py
└── tests/
    ├── conftest.py
    └── test_main.py
```

## 개발 환경

- Python 3.12
- uv
- PySide6
- PyInstaller
- ruff
- mypy strict
- pytest

## 설치

의존성은 `uv`가 관리합니다. 프로젝트 폴더에서 아래 명령을 실행하면 필요한 패키지가 설치됩니다.

```powershell
uv sync
```

개발 도구까지 포함해서 동기화하려면:

```powershell
uv sync --dev
```

## 앱 실행

개발 모드에서 바로 실행:

```powershell
uv run my-app
```

또는 Python 모듈로 실행:

```powershell
uv run python -m my_app.main
```

## 사용 방법

1. `Open` 버튼을 눌러 PNG, JPG, SVG, PDF, Markdown 파일을 선택합니다.
2. 파일을 앱 창 위로 Drag & Drop해도 열 수 있습니다.
3. 마우스 휠 또는 상단 `+`, `-` 버튼으로 확대/축소합니다.
4. `Reset` 버튼으로 Zoom을 100%로 되돌립니다.
5. 화면을 마우스로 드래그하거나 `↑`, `↓`, `←`, `→` 버튼으로 이동합니다.
6. PDF 파일은 상단의 `Prev`, `Next` 버튼 또는 `PgUp`, `PgDn`으로 페이지를 이동합니다.
7. Markdown 파일은 상단의 `Prev`, `Next` 버튼 또는 `PgUp`, `PgDn`으로 화면 단위 이동합니다.

## 실행 파일 빌드

PyInstaller spec 파일은 `app.spec`입니다. onefile, console 비표시 설정으로 빌드됩니다.

```powershell
uv run pyinstaller app.spec
```

빌드가 끝나면 실행 파일이 아래 경로에 생성됩니다.

```text
dist/svgvv.exe
```

## 정리

빌드 중간 산출물과 검사 캐시를 정리하려면:

```powershell
uv run clean
```

기본 정리에서는 `dist/svgvv.exe`를 보존합니다. 실행 파일까지 지우고 싶으면:

```powershell
uv run clean --dist
```

삭제될 항목만 미리 보려면:

```powershell
uv run clean --dry-run
```

## 품질 검사

ruff:

```powershell
uv run ruff check .
```

mypy strict:

```powershell
uv run mypy
```

pytest:

```powershell
uv run pytest
```

전체 확인 예시:

```powershell
uv run ruff check .
uv run mypy
uv run pytest
```

## 참고

- 앱 창 제목은 `Image / SVG / PDF / Markdown Viewer`입니다.
- 앱 아이콘 원본은 `src/my_app/assets/app_icon.svg`이고, Windows 실행 파일용 아이콘은 `src/my_app/assets/app_icon.ico`입니다.
- PyInstaller 결과 파일명은 `app.spec`의 `name="svgvv"` 설정으로 정해집니다.
- PDF 표시는 PySide6의 `QPdfView`를 사용합니다.
- SVG 표시는 `QGraphicsSvgItem`을 사용합니다.
