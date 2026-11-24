// 분석 화면: 입력 방식 전환 → POST /api/v1/analyses/ → 작업 ID로 상태 폴링 → 완료 시 결과 표시
// 주소는 하드코딩하지 않고 index.html의 data-*-url(Django {% url %})에서 읽는다.
(() => {
  const form = document.getElementById("analysis-form");
  if (!form) return;

  const POLL_MS = 2000;
  // 이 시간이 지나도 끝나지 않으면 조회를 멈춘다(Worker·Redis가 죽었을 때 화면이 영원히 '대기'가 되지 않게)
  const POLL_TIMEOUT_MS = (Number(form.dataset.pollTimeout) || 600) * 1000;
  // "/api/v1/analyses/0/" 같은 템플릿 주소의 0을 실제 작업 id로 바꾼다
  const withId = (template, id) => template.replace("/0/", `/${id}/`);
  const urls = {
    list: form.dataset.listUrl,
    detailApi: (id) => withId(form.dataset.detailApiUrl, id),
    status: (id) => withId(form.dataset.statusUrl, id),
    detailPage: (id) => withId(form.dataset.detailPageUrl, id),
  };
  const lowConf = JSON.parse(document.getElementById("low-conf").textContent);
  const csrf = form.querySelector("[name=csrfmiddlewaretoken]").value;
  const inputType = form.querySelector("[name=input_type]");
  const startBtn = document.getElementById("start-btn");
  const panel = document.getElementById("job-panel");
  const msg = document.getElementById("job-message");
  const table = document.getElementById("result-table");
  const detailLink = document.getElementById("detail-link");
  let timer = null;

  // 1) 탭 전환
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
      inputType.value = tab.dataset.input;
      document.querySelectorAll(".pane").forEach((p) => p.classList.toggle("hidden", p.dataset.pane !== tab.dataset.input));
    });
  });

  // 2) 분석 시작
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = new FormData(form);
    if (inputType.value === "UPLOAD") {
      data.delete("camera_index");
      if (!form.video_file.files.length) return showError("분석할 영상 파일을 선택하세요.");
    } else {
      data.delete("video_file");
    }

    startBtn.disabled = true;
    resetPanel();
    try {
      const res = await fetch(urls.list, {
        method: "POST", body: data, headers: { "X-CSRFToken": csrf }, credentials: "same-origin",
      });
      const body = await res.json().catch(() => ({}));
      if (res.status !== 202) throw new Error(flattenErrors(body) || `요청 실패 (${res.status})`);
      document.getElementById("job-id").textContent = `#${body.id}`;
      msg.textContent = inputType.value === "WEBCAM"
        ? "작업이 등록되었습니다. 곧 카메라 수집이 시작되니 카메라 앞에서 동작하세요."
        : "작업이 등록되었습니다. 결과를 기다리는 중…";
      poll(body.id);
    } catch (err) {
      showError(err.message);
      startBtn.disabled = false;
    }
  });

  // 3) 상태 폴링
  function stopPolling(id, text) {
    clearInterval(timer);
    startBtn.disabled = false;
    showError(text);
    detailLink.href = urls.detailPage(id);
    detailLink.hidden = false;
  }

  function poll(id) {
    clearInterval(timer);
    const startedAt = Date.now();
    const limitText = POLL_TIMEOUT_MS >= 60000 ? `${Math.round(POLL_TIMEOUT_MS / 60000)}분` : `${POLL_TIMEOUT_MS / 1000}초`;
    const tick = async () => {
      if (Date.now() - startedAt > POLL_TIMEOUT_MS) {
        stopPolling(id, `${limitText}이 지나도 분석이 끝나지 않아 상태 확인을 멈췄습니다. ` +
          "Celery Worker와 Redis가 켜져 있는지 확인하세요. 나중에 상세 결과 화면에서 다시 볼 수 있습니다.");
        return;
      }
      try {
        const res = await fetch(urls.status(id), { credentials: "same-origin" });
        if (!res.ok) throw new Error(`상태 조회 실패 (${res.status})`);
        const s = await res.json();
        setStep(s.status);
        if (s.status === "STARTED") msg.textContent = "처리 중입니다… (영상 확보 → AI 추론)";
        if (s.is_stale) {
          stopPolling(id, "작업이 멈춘 것 같습니다(Worker가 가져가지 않음). 이 작업은 이력에서 삭제하고 다시 시도하세요.");
          return;
        }
        if (s.is_finished) {
          clearInterval(timer);
          startBtn.disabled = false;
          if (s.status === "SUCCESS") await showResult(id);
          else showError(s.error_message || "분석에 실패했습니다.");
          detailLink.href = urls.detailPage(id);
          detailLink.hidden = false;
        }
      } catch (err) {
        clearInterval(timer);
        startBtn.disabled = false;
        showError(err.message);
      }
    };
    tick();
    timer = setInterval(tick, POLL_MS);
  }

  // 4) 결과 표시
  async function showResult(id) {
    const res = await fetch(urls.detailApi(id), { credentials: "same-origin" });
    const job = await res.json();
    const tbody = table.querySelector("tbody");
    tbody.innerHTML = "";
    if (!job.predictions.length) {
      msg.textContent = job.result_message || "영상에서 사람을 찾지 못했습니다.";
      return;
    }
    job.predictions.forEach((p) => {
      const tr = document.createElement("tr");
      const uncertain = p.confidence < lowConf;
      [p.track_id, `${p.action_label} (${p.action_display})`, p.confidence.toFixed(3), p.window_count].forEach((v) => {
        const td = document.createElement("td"); td.textContent = v; tr.appendChild(td);
      });
      const td = document.createElement("td");
      td.innerHTML = uncertain ? '<span class="badge warn">판단 불확실</span>' : '<span class="badge ok">신뢰</span>';
      tr.appendChild(td);
      tbody.appendChild(tr);
    });
    table.hidden = false;
    const secs = job.processing_ms ? ` · AI 추론 ${(job.processing_ms / 1000).toFixed(1)}초` : "";
    msg.textContent = `완료: ${job.predictions.length}명 예측${secs}`;
    prependRecent(job);
  }

  function prependRecent(job) {
    const body = document.getElementById("recent-body");
    const empty = body.querySelector("td[colspan]");
    if (empty) empty.parentElement.remove();
    const tr = document.createElement("tr");
    const preds = job.predictions.map((p) => `#${p.track_id} ${p.action_label} (${p.confidence.toFixed(2)})`).join(", ") || "-";
    const cells = [job.id, job.title || "-", job.input_type_display, job.status_display, preds, "방금"];
    cells.forEach((v, i) => {
      const td = document.createElement("td");
      if (i === 0) { const a = document.createElement("a"); a.href = urls.detailPage(job.id); a.textContent = v; td.appendChild(a); }
      else td.textContent = v;
      tr.appendChild(td);
    });
    body.prepend(tr);
  }

  function setStep(status) {
    document.querySelectorAll("#steps li").forEach((li) => li.className = "");
    const [pending, started, done] = document.querySelectorAll("#steps li");
    if (status === "PENDING") pending.className = "active";
    if (status === "STARTED") { pending.className = "done"; started.className = "active"; }
    if (status === "SUCCESS") { pending.className = started.className = done.className = "done"; }
    if (status === "FAILURE") { pending.className = started.className = "done"; done.className = "fail"; }
  }

  function resetPanel() {
    panel.hidden = false; table.hidden = true; detailLink.hidden = true;
    msg.className = "muted"; msg.textContent = "요청을 보내는 중…";
    document.getElementById("job-id").textContent = "";
    setStep("PENDING");
  }

  function showError(text) {
    panel.hidden = false;
    msg.className = "error";
    msg.textContent = text;
  }

  function flattenErrors(body) {
    if (!body || typeof body !== "object") return "";
    if (body.detail) return body.detail;
    return Object.values(body).flat().join(" ");
  }
})();
