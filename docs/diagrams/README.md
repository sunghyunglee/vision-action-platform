# Diagrams

`docs/images/` 의 그림을 만드는 소스입니다. Python 이 SVG 를 쓰고, Playwright(Chromium)가 PNG 로 렌더링합니다. 한국어 · 영어 글자는 `T("한국어", "English")` 로 한 곳에 같이 둡니다.

| 그림 | 생성기 | 출력 |
|---|---|---|
| Architecture (노드 ①~⑫ · 버튼 흐름 · 주소 표) | `make_architecture.py` | `architecture.svg` · `architecture.en.svg` |
| Pipeline (설정 → 시작 → 입력 → 추론 → 저장 → 검증) | `make_pipeline.py` | `pipeline.svg` · `pipeline.en.svg` |
| 백엔드 분석 그래프 (B4 · B8 · B7) | `make_backend_chart.py` | `backend_analysis.svg` · `backend_analysis.en.svg` |

```bash
python3 make_architecture.py        # 한국어
python3 make_architecture.py en     # 영어 (translate_architecture_en.py 는 영어판을 만들고 남은 한글을 보고)
node render.js architecture.svg ../images/architecture.png 2
```

필요: Python 3 · Node.js + `playwright` · 한글 글꼴 Noto Sans CJK. 글자가 칸을 넘치면 `overflow?` 경고를 출력합니다.
그림 속 파일 · 함수 · 줄 번호는 `main` 40d3916 기준입니다. 코드를 바꾸면 그림도 다시 만듭니다.

README 의 작동 화면 합성(`screens*.png` · `evidence*.png`)은 원본 캡처를 잘라 붙인 이미지라 생성기를 넣지 않았습니다.
