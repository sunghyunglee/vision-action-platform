// 관리자 대시보드: Django ORM 집계(json_script)를 Chart.js로 그린다.
(() => {
  const data = JSON.parse(document.getElementById("chart-data").textContent);
  const palette = ["#2f6fed", "#1f9d55", "#d97706", "#9333ea", "#0891b2", "#dc2626"];
  const statusColors = { PENDING: "#9ca3af", STARTED: "#3b82f6", SUCCESS: "#16a34a", FAILURE: "#dc2626" };
  const intOpts = { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } };

  // 필수 1) 6개 Action별 예측 건수
  new Chart(document.getElementById("action-chart"), {
    type: "bar",
    data: { labels: data.actions.labels, datasets: [{ label: "예측 건수", data: data.actions.counts, backgroundColor: palette }] },
    options: intOpts,
  });

  // 필수 2) 작업 상태별 건수
  new Chart(document.getElementById("status-chart"), {
    type: "doughnut",
    data: {
      labels: data.statuses.labels,
      datasets: [{ data: data.statuses.counts, backgroundColor: data.statuses.labels.map((s) => statusColors[s]) }],
    },
    options: { responsive: true },
  });

  // 선택) 입력 방식 비율
  new Chart(document.getElementById("input-chart"), {
    type: "pie",
    data: { labels: data.inputs.labels, datasets: [{ data: data.inputs.counts, backgroundColor: ["#2f6fed", "#d97706"] }] },
    options: { responsive: true },
  });

  // 선택) 입력 방식별 평균 AI 추론 시간(ms)
  const avgLabels = Object.keys(data.avg_ms);
  new Chart(document.getElementById("time-chart"), {
    type: "bar",
    data: { labels: avgLabels, datasets: [{ label: "평균 ms", data: avgLabels.map((k) => data.avg_ms[k]), backgroundColor: "#0891b2" }] },
    options: intOpts,
  });
})();
