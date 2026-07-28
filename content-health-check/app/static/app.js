/* Biz Content Health Check — form → poll → render printout. No frameworks. */
(function () {
  "use strict";

  var form = document.getElementById("checkup-form");
  var formSection = document.getElementById("form-section");
  var loadingSection = document.getElementById("loading-section");
  var resultSection = document.getElementById("result-section");
  var submitBtn = document.getElementById("submit-btn");
  var formError = document.getElementById("form-error");

  var LOADING_STAGES = [
    ["กำลังสแกนบัญชีของคุณ…", "ดึงโพสต์ล่าสุด, engagement, ข้อมูลโปรไฟล์จริง"],
    ["กำลังส่องคู่แข่ง… 🤫", "เทียบตัวเลขแบบที่ตาเปล่ามองไม่เห็น"],
    ["AI กำลังวิเคราะห์ธุรกิจของคุณ…", "อ่าน bio + คอนเทนต์ แล้วให้คะแนน 7 ด้าน"],
    ["กำลังพิมพ์ใบรายงานผล…", "เกือบเสร็จแล้ว"]
  ];

  var STATUS_BANDS = {
    bad: { max: 3, label: "ต้องรีบแก้" },
    warn: { max: 6, label: "ยังไม่ปลอดภัย" },
    good: { max: 10, label: "แข็งแรง" }
  };

  function bandOf(score) {
    if (score <= STATUS_BANDS.bad.max) return "bad";
    if (score <= STATUS_BANDS.warn.max) return "warn";
    return "good";
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  var loadTimer = null, pollTimer = null;

  function startLoadingTheater() {
    var i = 0, fill = document.getElementById("loadbar-fill");
    var msg = document.getElementById("loading-msg"), sub = document.getElementById("loading-sub");
    function tick() {
      var stage = LOADING_STAGES[Math.min(i, LOADING_STAGES.length - 1)];
      msg.textContent = stage[0];
      sub.textContent = stage[1];
      fill.style.width = Math.min(10 + i * 22, 92) + "%";
      i++;
    }
    tick();
    loadTimer = setInterval(tick, 7000);
  }

  function stopLoadingTheater() {
    if (loadTimer) clearInterval(loadTimer);
    if (pollTimer) clearTimeout(pollTimer);
  }

  function showError(text) {
    formError.textContent = text;
    formError.hidden = false;
    submitBtn.disabled = false;
    loadingSection.hidden = true;
    formSection.hidden = false;
    stopLoadingTheater();
    formSection.scrollIntoView({ behavior: "smooth" });
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    formError.hidden = true;

    var data = {};
    new FormData(form).forEach(function (v, k) { data[k] = String(v).trim() || null; });

    if (!data.ig_handle && !data.tiktok_handle && !data.fb_handle) {
      return showError("กรอก social handle ของธุรกิจอย่างน้อย 1 ช่องทางก่อนนะ");
    }
    if (!data.email && !data.line_id) {
      return showError("กรอกอีเมลหรือ LINE ID อย่างน้อย 1 ช่อง เพื่อรับผลตรวจ");
    }

    submitBtn.disabled = true;
    formSection.hidden = true;
    loadingSection.hidden = false;
    window.scrollTo({ top: 0, behavior: "smooth" });
    startLoadingTheater();

    fetch("/api/checkup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, status: r.status, body: j }; }); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.body.detail || "ส่งข้อมูลไม่สำเร็จ ลองใหม่อีกครั้ง");
        poll(res.body.run_id, 0);
      })
      .catch(function (err) { showError(err.message); });
  });

  function poll(runId, attempt) {
    if (attempt > 90) return showError("ใช้เวลานานผิดปกติ ลองใหม่อีกครั้ง หรือทักหาเราทาง LINE ได้เลย");
    fetch("/api/checkup/" + runId)
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j.status === "done" && j.result) return render(j.result);
        if (j.status === "error") return showError(j.detail || "ระบบขัดข้องชั่วคราว ลองใหม่อีกครั้ง");
        pollTimer = setTimeout(function () { poll(runId, attempt + 1); }, 2500);
      })
      .catch(function () {
        pollTimer = setTimeout(function () { poll(runId, attempt + 1); }, 4000);
      });
  }

  function render(result) {
    stopLoadingTheater();
    loadingSection.hidden = true;
    resultSection.hidden = false;

    document.getElementById("r-bizname").textContent = result.business_name || "ธุรกิจของคุณ";
    document.getElementById("r-date").textContent =
      new Date((result.generated_at || Date.now() / 1000) * 1000).toLocaleDateString("th-TH", {
        year: "numeric", month: "long", day: "numeric"
      });
    document.getElementById("r-overall-score").textContent = result.overall.score;
    document.getElementById("r-summary").textContent = result.overall.summary;
    document.getElementById("r-quality-note").hidden = result.data_quality === "full";

    var ctaBtn = document.getElementById("cta-btn");
    if (result.cta_url) ctaBtn.href = result.cta_url;

    var wrap = document.getElementById("r-aspects");
    wrap.innerHTML = "";
    (result.aspects || []).forEach(function (a, idx) {
      var band = bandOf(a.score);
      var html =
        '<div class="aspect">' +
          '<div class="aspect-top">' +
            '<div class="aspect-title">' + (idx + 1) + ". " + esc(a.title_th) + "</div>" +
            '<div class="aspect-score">' + a.score + "<small>/10</small></div>" +
          "</div>" +
          '<div class="meter"><div class="meter-fill ' + band + '" style="width:0%"></div></div>' +
          '<div class="chips">' +
            '<span class="chip ' + band + '">' + STATUS_BANDS[band].label + "</span>" +
            (a.confidence === "low" ? '<span class="chip hedge">ข้อมูลจำกัด</span>' : "") +
          "</div>" +
          '<div class="aspect-headline">' + esc(a.headline) + "</div>" +
          '<div class="aspect-detail">' + esc(a.detail) + "</div>";
      if (a.evidence && a.evidence.length) {
        html += '<div class="evidence"><span class="evidence-label">อ้างอิงจาก:</span><ul>' +
          a.evidence.map(function (ev) { return "<li>" + esc(ev) + "</li>"; }).join("") +
          "</ul></div>";
      }
      html += "</div>";
      wrap.insertAdjacentHTML("beforeend", html);
    });

    window.scrollTo({ top: 0, behavior: "smooth" });
    // animate meters after paint
    requestAnimationFrame(function () {
      setTimeout(function () {
        document.querySelectorAll(".meter-fill").forEach(function (el, i) {
          var score = (result.aspects[i] || {}).score || 0;
          el.style.width = (score * 10) + "%";
        });
      }, 60);
    });
  }

  document.getElementById("again-btn").addEventListener("click", function () {
    window.location.reload();
  });
})();
