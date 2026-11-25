"""README 백엔드 분석 그래프: job 1건 시간 분해 · 같은 영상 6회 · 장애 주입 비교 (값은 산출물/백엔드_분석_기록.md B4·B7·B8)
python3 make_backend_chart.py [en]  ->  backend_analysis(.en).svg
"""
import sys
from pathlib import Path
EN = len(sys.argv) > 1 and sys.argv[1] == "en"
T = (lambda ko, en: en) if EN else (lambda ko, en: ko)
FONT = "Noto Sans CJK KR, Malgun Gothic, sans-serif"
INK, SUB, LINE = "#0F172A", "#475569", "#E2E8F0"
BLUE, PURPLE, TEAL, GRAY, GREEN, AMBER, RED = "#2563EB", "#7C3AED", "#0F766E", "#94A3B8", "#16A34A", "#D97706", "#DC2626"
W, H = 1680, 560
o = []
a = o.append
a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">')
a(f'<rect width="{W}" height="{H}" fill="#fff"/>')

def panel(x, w, title, sub):
    a(f'<rect x="{x}" y="20" width="{w}" height="{H - 40}" rx="12" fill="#F8FAFC" stroke="{LINE}" stroke-width="1.5"/>')
    a(f'<text x="{x + 24}" y="58" font-size="20" font-weight="700" fill="{INK}">{title}</text>')
    a(f'<text x="{x + 24}" y="84" font-size="13.5" fill="{SUB}">{sub}</text>')

# ① job 12 시간 분해
x0, pw = 20, 560
panel(x0, pw, T("① 요청 1건 3.78초는 어디서 걸렸나", "① Where 3.78 s of one request goes"), T("job 12 · task ID 로 로그 3개 + DB 시각 3개를 이어 붙임 (B4)", "job 12 · 3 logs + 3 DB timestamps joined by task ID (B4)"))
segs = [(T("대기열", "Queue"), 0.027, GRAY), (T("Worker 준비", "Worker prep"), 0.114, PURPLE), (T("AI 추론", "AI inference"), 3.625, BLUE), (T("저장", "Save"), 0.017, GREEN)]
bx, bw, by = x0 + 30, pw - 60, 150
tot = sum(s[1] for s in segs)
cx = bx
for name, v, c in segs:
    w = max(bw * v / tot, 4)
    a(f'<rect x="{cx}" y="{by}" width="{w}" height="54" fill="{c}"/>')
    cx += w
a(f'<text x="{bx + bw * 0.55}" y="{by + 35}" font-size="19" font-weight="700" fill="#fff" text-anchor="middle">{T("AI 추론 3.625초 (96%)", "AI inference 3.625 s (96%)")}</text>')
rows = [(T("접수 → Worker 수신", "Accepted → Worker received"), "0.027 s", GRAY), (T("STARTED 저장 · 영상 전송", "STARTED saved · video sent"), "0.114 s", PURPLE),
        (T("YOLO Pose + RandomForest", "YOLO Pose + RandomForest"), "3.625 s", BLUE), (T("bulk_create · SUCCESS 저장", "bulk_create · SUCCESS saved"), "0.017 s", GREEN)]
for k, (n, v, c) in enumerate(rows):
    y = 252 + k * 46
    a(f'<rect x="{bx}" y="{y - 15}" width="18" height="18" rx="3" fill="{c}"/>')
    a(f'<text x="{bx + 30}" y="{y}" font-size="16" fill="{INK}">{n}</text>')
    a(f'<text x="{bx + bw}" y="{y}" font-size="16" font-weight="700" fill="{INK}" text-anchor="end">{v}</text>')
a(f'<line x1="{bx}" y1="{442}" x2="{bx + bw}" y2="{442}" stroke="{LINE}" stroke-width="2"/>')
a(f'<text x="{bx}" y="472" font-size="15" fill="{SUB}">{T("웹 · 큐 · DB 는 합쳐서 약 0.16초", "Web · queue · DB together ≈ 0.16 s")}</text>')
a(f'<text x="{bx}" y="498" font-size="15" fill="{SUB}">{T("→ 병목은 AI 추론 하나", "→ the only bottleneck is AI inference")}</text>')

# ② 같은 영상 6회
x1 = x0 + pw + 20
panel(x1, pw, T("② 같은 영상 6회 · AI 추론 시간", "② Same video × 6 · inference time"), T("wave.mp4 5.04초 · 1명 · i7-12700 CPU · 첫 회는 워밍업 (B8)", "wave.mp4 5.04 s · 1 person · i7-12700 CPU · run 1 = warm-up (B8)"))
vals = [4645, 3295, 3331, 3312, 3345, 3331]
gx, gy, gw, gh = x1 + 70, 120, pw - 100, 330
vmax = 5000
for t in range(0, 5001, 1000):
    y = gy + gh - gh * t / vmax
    a(f'<line x1="{gx}" y1="{y}" x2="{gx + gw}" y2="{y}" stroke="{LINE}"/>')
    a(f'<text x="{gx - 10}" y="{y + 5}" font-size="13" fill="{SUB}" text-anchor="end">{t:,}</text>')
bwid = gw / len(vals)
for i, v in enumerate(vals):
    h = gh * v / vmax
    x = gx + i * bwid + bwid * 0.18
    c = GRAY if i == 0 else BLUE
    a(f'<rect x="{x}" y="{gy + gh - h}" width="{bwid * 0.64}" height="{h}" rx="4" fill="{c}"/>')
    a(f'<text x="{x + bwid * 0.32}" y="{gy + gh - h - 8}" font-size="13.5" font-weight="700" fill="{INK}" text-anchor="middle">{v:,}</text>')
    a(f'<text x="{x + bwid * 0.32}" y="{gy + gh + 22}" font-size="13" fill="{SUB}" text-anchor="middle">{T("워밍업", "warm-up") if i == 0 else f"{i + 1}{T("회", "")}"}</text>')
p50y = gy + gh - gh * 3331 / vmax
a(f'<line x1="{gx}" y1="{p50y}" x2="{gx + gw}" y2="{p50y}" stroke="{AMBER}" stroke-width="2" stroke-dasharray="6 5"/>')
a(f'<text x="{gx + gw}" y="{p50y - 30}" font-size="14" font-weight="700" fill="{AMBER}" text-anchor="end">p50 3,331 ms (±0.8%)</text>')
a(f'<text x="{gx - 40}" y="{gy + gh + 52}" font-size="15" fill="{SUB}">{T("5초 영상을 3.3초에 처리 · 전체 시간의 99.3% 가 추론", "5 s video in 3.3 s · 99.3% of total time is inference")}</text>')

# ③ 장애 주입
x2 = x1 + pw + 20
pw2 = W - x2 - 20
panel(x2, pw2, T("③ 서비스를 하나씩 꺼 보기", "③ Stopping one service at a time"), T("개선 전 결과 (B7) → 찾은 문제를 코드로 고침", "Before the fix (B7) → problems fixed in code"))
cards = [
    ("Celery Worker", T("202 즉시 · 복구 후 SUCCESS", "202 at once · SUCCESS after restart"), T("Redis 가 작업 보관 → 유실 0", "Redis kept the job → nothing lost"), AMBER, T("지연", "Delay")),
    ("FastAPI", T("4.0초 만에 FAILURE + 이유", "FAILURE + reason in 4.0 s"), T("사용자에게 원인 바로 안내", "Cause shown to the user at once"), GREEN, T("정상 처리", "Handled")),
    ("Redis", T("105.2초 대기 후 500", "500 after 105.2 s"), T("작업이 영구 PENDING 으로 남음", "Job stuck in PENDING forever"), RED, T("취약 → 개선", "Weak → fixed")),
]
for k, (name, l1, l2, c, tag) in enumerate(cards):
    y = 112 + k * 112
    a(f'<rect x="{x2 + 24}" y="{y}" width="{pw2 - 48}" height="96" rx="10" fill="#fff" stroke="{c}" stroke-width="2.4"/>')
    a(f'<rect x="{x2 + 24}" y="{y}" width="8" height="96" rx="3" fill="{c}"/>')
    a(f'<text x="{x2 + 48}" y="{y + 32}" font-size="18" font-weight="700" fill="{INK}">{name}</text>')
    tw = 16 + len(tag) * (9 if EN else 15)
    a(f'<rect x="{x2 + pw2 - 40 - tw}" y="{y + 14}" width="{tw}" height="26" rx="13" fill="{c}"/>')
    a(f'<text x="{x2 + pw2 - 40 - tw / 2}" y="{y + 32}" font-size="13.5" font-weight="700" fill="#fff" text-anchor="middle">{tag}</text>')
    a(f'<text x="{x2 + 48}" y="{y + 60}" font-size="15.5" fill="{INK}">{l1}</text>')
    a(f'<text x="{x2 + 48}" y="{y + 82}" font-size="14.5" fill="{SUB}">{l2}</text>')
a(f'<text x="{x2 + 24}" y="{472}" font-size="15" font-weight="700" fill="{INK}">{T("고친 것", "Fixed")}</text>')
a(f'<text x="{x2 + 24}" y="{498}" font-size="14.5" fill="{SUB}">{T("등록 재시도 2회 → 실패 즉시 FAILURE 저장 · 503 · 폴링 최대 10분", "2 enqueue retries → FAILURE + 503 at once · polling capped at 10 min")}</text>')
a('</svg>')
Path(__file__).with_name("backend_analysis.en.svg" if EN else "backend_analysis.svg").write_text("\n".join(o), encoding="utf-8")
print("ok")
