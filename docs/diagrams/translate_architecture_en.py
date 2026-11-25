"""영어판 architecture.en.svg 만들기 (v5부터 한국어 · 영어 글자를 make_architecture.py 안에 T("한글", "English") 한 쌍으로 둠)
python3 translate_architecture_en.py && node render.js architecture.en.svg architecture.en.png 2
예전처럼 한국어 SVG 글자를 바꿔 치기하지 않고, 같은 레이아웃을 영어 글자 폭으로 다시 그린다.
"""
import re
import subprocess
import sys
from pathlib import Path

d = Path(__file__).parent
subprocess.run([sys.executable, str(d / "make_architecture.py"), "en"], check=True)
s = (d / "architecture.en.svg").read_text(encoding="utf-8")
left = sorted(set(x for x in re.findall(r"<text[^>]*>([^<]*)</text>", s) if re.search("[가-힣]", x)))
print("architecture.en.svg · untranslated:", left)
