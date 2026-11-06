/* Atmos front-end: theme + language toggle, "latest real data" button, Chart.js charts. No build step needed. */
(function () {
  "use strict";
  var doc = document.documentElement;
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function json(id) { var el = document.getElementById(id); return el ? JSON.parse(el.textContent) : null; }

  /* ------------------------------------------------------------ i18n (English <-> Arabic) */
  var AR = {
    tagline: "ذكاء الطقس", nav_home: "الرئيسية", nav_insights: "تحليلات", nav_batch: "دفعة", nav_about: "عن المشروع",
    foot_tag: "تعلّم الآلة لغدٍ أكثر إشراقًا.", foot_dev: "للمطورين:", rights: "جميع الحقوق محفوظة.",
    h_weather: "متنبئ", h_predictor: "الطقس",
    lead_a: "أدخل قراءات الطقس لليوم واحصل على متوسط درجة الحرارة المتوقع للأيام السبعة القادمة في",
    chip_years: "سنوات من البيانات التاريخية", chip_ml: "3 نماذج تعلّم آلة", chip_7d: "توقع 7 أيام مع نطاق الثقة",
    avg_error: "متوسط خطأ النموذج (اليوم 1)", trained_thru: "تم التدريب حتى",
    p_conditions: "أحوال الطقس اليوم", p_conditions_sub: "أدخل متوسط قراءات اليوم أو حمّل أحدث البيانات الحقيقية.",
    f_city: "المدينة", f_model: "النموذج", btn_latest: "استخدم أحدث بيانات حقيقية",
    f_temp: "متوسط درجة حرارة اليوم (°م)", f_hum: "متوسط الرطوبة النسبية (%)", f_wind: "متوسط سرعة الرياح (كم/س)",
    f_press: "متوسط ضغط السطح (هيكتوباسكال)", f_date: "تاريخ هذه القراءات", btn_predict: "توقّع الأيام السبعة القادمة",
    p_forecast: "توقعات الغد", p_forecast_sub: "بناءً على نموذج تعلّم الآلة المدرَّب.",
    cat_cold: "بارد", cat_mild: "معتدل", cat_warm: "دافئ", cat_hot: "حار", tomorrow_mean: "غدًا (المتوسط)",
    likely_range: "النطاق المحتمل", empty_result: "ستظهر توقعاتك هنا", t_model: "النموذج", t_city: "المدينة", t_mae: "متوسط الخطأ (اختبار)",
    warn_a: "بعض المدخلات", warn_b: "خارج النطاق الذي تدرّب عليه النموذج، لذا تعامل مع التوقع بحذر.",
    p_week: "نظرة على 7 أيام", p_week_sub: "متوسط الحرارة المتوقع مع نطاق 95% مقارنة بالمعدل الموسمي.", normal: "المعدل",
    why: "لماذا هذا التوقع؟", why_note: "تأثير كل مُدخل على توقع الغد مقارنةً بالظروف المتوسطة (°م).",
    p_history: "آخر التوقعات", download_csv: "تحميل CSV", clear: "مسح",
    ins_title: "تحليلات", ins_title2: "المناخ", ins_sub: "سنوات من البيانات اليومية تقول عن",
    k_mean: "متوسط الحرارة", k_hot: "أحرّ يوم", k_cold: "أبرد يوم", k_trend: "اتجاه الاحترار", decade: "عقد",
    k_rainy: "أيام ممطرة / سنة", k_wet: "أمطر يوم", c_month: "الحرارة حسب الشهر", c_year: "متوسط الحرارة لكل سنة",
    c_recent: "آخر 365 يومًا مقابل المعدل الموسمي", c_rain: "متوسط الأمطار حسب الشهر (مم)", c_heat: "خريطة حرارية لمتوسط الحرارة الشهري (°م)",
    b_title: "التوقع", b_title2: "بالدفعة", b_sub: "ارفع ملف CSV بعدة أيام واحصل على توقع 7 أيام لكل صف.",
    b_file: "ملف CSV", b_run: "شغّل التوقعات", b_sample: "ملف CSV نموذجي", b_empty: "ستظهر النتائج هنا",
    a_title: "عن", a_sub: "تطبيق تعلّم آلة يتوقع متوسط الحرارة للأيام السبعة القادمة في",
    a_how: "كيف يعمل", a_quality: "الدقة على فترة الاختبار (اليوم +1)", built_by: "تم التطوير بواسطة",
    author_sub: "تحليل البيانات ولوحات المعلومات وتطبيقات الويب لتعلّم الآلة."
  };

  function applyLang(lang) {
    $$("[data-i18n]").forEach(function (el) {
      if (el.dataset.en === undefined) el.dataset.en = el.textContent;
      var k = el.getAttribute("data-i18n");
      el.textContent = (lang === "ar" && AR[k]) ? AR[k] : el.dataset.en;
    });
    if (lang === "ar") { doc.setAttribute("lang", "ar"); doc.setAttribute("dir", "rtl"); }
    else { doc.setAttribute("lang", "en"); doc.removeAttribute("dir"); }
    var b = $("#lang-toggle"); if (b) b.textContent = lang === "ar" ? "EN" : "AR";
  }

  /* ------------------------------------------------------------ theme */
  function setTheme(t) {
    doc.setAttribute("data-theme", t); doc.setAttribute("data-bs-theme", t);
    try { localStorage.setItem("atmos-theme", t); } catch (e) {}
    var i = $("#theme-toggle i"); if (i) i.className = "bi " + (t === "dark" ? "bi-brightness-high-fill" : "bi-moon-stars-fill");
  }

  /* ------------------------------------------------------------ charts */
  var charts = [];
  function css(v) { return getComputedStyle(doc).getPropertyValue(v).trim(); }
  function make(id, cfg) {
    var el = document.getElementById(id);
    if (!el || typeof Chart === "undefined") return null;
    var c = new Chart(el.getContext("2d"), cfg); charts.push(c); return c;
  }
  function themeDefaults() {
    if (typeof Chart === "undefined") return;
    Chart.defaults.color = css("--chart-text"); Chart.defaults.borderColor = css("--chart-grid");
    Chart.defaults.font.family = "Poppins, Cairo, system-ui, sans-serif";
  }
  var TEAL = "#2dd4bf", BLUE = "#60a5fa", ORANGE = "#fb923c", RED = "#f87171";
  var base = { responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false } };

  function recentHistory(slug, startDate) {
    try {
      var h = JSON.parse(sessionStorage.getItem("recent_" + slug) || "[]");
      return h.filter(function (x) { return x.date < startDate; }).slice(-10);
    } catch (e) { return []; }
  }

  function drawForecast() {
    var d = json("chart-data"); if (!d) return;
    var hist = recentHistory(d.city_slug, d.start_date), n = hist.length, m = d.dates.length;
    var labels = hist.map(function (x) { return x.date; }).concat([d.start_date], d.dates);
    var pad = function (k) { return new Array(k).fill(null); };
    var actual = hist.map(function (x) { return x.temperature; }).concat([d.start_value], pad(m));
    var fc = pad(n).concat([d.start_value], d.pred);
    var low = pad(n).concat([d.start_value], d.low), high = pad(n).concat([d.start_value], d.high);
    var normal = pad(n + 1).concat(d.normal);
    make("forecastChart", { type: "line", data: { labels: labels, datasets: [
      { label: "Real / entered", data: actual, borderColor: BLUE, backgroundColor: BLUE, tension: .3, pointRadius: 3 },
      { label: "Forecast", data: fc, borderColor: TEAL, backgroundColor: TEAL, borderWidth: 3, tension: .3, pointRadius: 4 },
      { label: "95% low", data: low, borderWidth: 0, pointRadius: 0, fill: false },
      { label: "95% range", data: high, borderWidth: 0, pointRadius: 0, fill: "-1", backgroundColor: "rgba(45,212,191,.2)" },
      { label: "Seasonal normal", data: normal, borderColor: ORANGE, borderDash: [6, 6], pointRadius: 0, tension: .3 }
    ] }, options: Object.assign({}, base, { plugins: { legend: { labels: { filter: function (i) { return i.text !== "95% low"; } } } },
      scales: { y: { title: { display: true, text: "°C" } } } }) });
    var note = $("#chart-note");
    if (note) note.textContent = n ? "Blue = recent real observations (loaded from Open-Meteo) and the value you entered; teal = forecast." :
      "Tip: press “Use latest real data” before predicting to also see the last days of real observations on this chart.";
  }

  function drawExplain() {
    var ex = json("explain-data"); if (!ex) return;
    make("explainChart", { type: "bar", data: { labels: ex.map(function (e) { return e.label; }), datasets: [{
      data: ex.map(function (e) { return e.effect; }), backgroundColor: ex.map(function (e) { return e.effect >= 0 ? ORANGE : BLUE; }), borderRadius: 6 }] },
      options: Object.assign({}, base, { indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { title: { display: true, text: "°C vs. average conditions" } } } }) });
  }

  function drawInsights() {
    var i = json("insights-data"); if (!i) return;
    make("monthlyChart", { type: "line", data: { labels: i.monthly.labels, datasets: [
      { label: "90th percentile", data: i.monthly.p90, borderWidth: 0, pointRadius: 0, backgroundColor: "rgba(251,146,60,.22)", fill: "+1" },
      { label: "10th percentile", data: i.monthly.p10, borderWidth: 0, pointRadius: 0, fill: false },
      { label: "Monthly mean", data: i.monthly.mean, borderColor: ORANGE, backgroundColor: ORANGE, tension: .3, pointRadius: 4 }] },
      options: Object.assign({}, base, { scales: { y: { title: { display: true, text: "°C" } } } }) });
    make("yearlyChart", { type: "bar", data: { labels: i.yearly.labels, datasets: [{ label: "Mean °C", data: i.yearly.mean, backgroundColor: ORANGE, borderRadius: 6 }] },
      options: Object.assign({}, base, { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: false, title: { display: true, text: "°C" } } } }) });
    make("recentChart", { type: "line", data: { labels: i.recent.labels, datasets: [
      { label: "Daily mean", data: i.recent.temp, borderColor: "rgba(96,165,250,.55)", borderWidth: 1, pointRadius: 0 },
      { label: "30-day mean", data: i.recent.avg30, borderColor: TEAL, borderWidth: 3, pointRadius: 0, tension: .3 },
      { label: "Seasonal normal", data: i.recent.normal, borderColor: ORANGE, borderDash: [6, 6], pointRadius: 0 }] },
      options: Object.assign({}, base, { scales: { x: { ticks: { maxTicksLimit: 12 } }, y: { title: { display: true, text: "°C" } } } }) });
    if (i.rain) make("rainChart", { type: "bar", data: { labels: i.rain.labels, datasets: [{ label: "mm", data: i.rain.mm, backgroundColor: BLUE, borderRadius: 6 }] },
      options: Object.assign({}, base, { plugins: { legend: { display: false } } }) });
  }

  function drawHorizon() {
    var c = json("horizon-data"); if (!c) return;
    var colors = [TEAL, ORANGE, "#a78bfa", RED, "#94a3b8"], k = 0;
    make("horizonChart", { type: "line", data: { labels: c.horizons.map(function (h) { return "+" + h + "d"; }),
      datasets: Object.keys(c.series).map(function (name) { var col = colors[k++ % colors.length];
        return { label: name, data: c.series[name], borderColor: col, backgroundColor: col, tension: .25, pointRadius: 3,
                 borderDash: /Persistence|Climatology/.test(name) ? [6, 5] : [] }; }) },
      options: Object.assign({}, base, { scales: { y: { title: { display: true, text: "MAE (°C) - lower is better" } } } }) });
  }

  function drawAll() {
    charts.forEach(function (c) { c.destroy(); }); charts = [];
    themeDefaults(); drawForecast(); drawExplain(); drawInsights(); drawHorizon();
  }

  /* ------------------------------------------------------------ "Use latest real data" */
  function initLatest() {
    var form = $("#predict-form"), btn = $("#btn-latest"), msg = $("#latest-msg");
    if (!form || !btn) return;
    function say(text, kind) { msg.textContent = text; msg.className = "latest-msg " + (kind || ""); }
    btn.addEventListener("click", function () {
      var city = form.elements["city"].value;
      btn.disabled = true; say("Loading the latest real observations…", "info");
      fetch(form.dataset.cityUrl + "?city=" + encodeURIComponent(city), { headers: { Accept: "application/json" } })
        .then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.error || ("HTTP " + r.status)); return j; }); })
        .then(function (j) {
          ["temperature", "humidity", "wind_speed", "pressure", "date"].forEach(function (k) { if (form.elements[k]) form.elements[k].value = j[k]; });
          try { sessionStorage.setItem("recent_" + city, JSON.stringify(j.history)); } catch (e) {}
          say("Loaded real readings for " + j.date + " (" + j.source + "). Now press “Predict”.", "ok");
        })
        .catch(function (e) { say("Could not load live data: " + e.message + ". You can still type the values manually.", "err"); })
        .then(function () { btn.disabled = false; });
    });
  }

  /* ------------------------------------------------------------ city background (cross-fade when the city changes) */
  function initScene() {
    var scene = $("#scene"), sel = $("select[name=city]");
    if (!scene || !sel) return;
    sel.addEventListener("change", function () {
      var url = scene.getAttribute("data-bg-" + sel.value) || scene.getAttribute("data-bg-default");
      if (!url) return;
      var img = new Image();
      img.onload = function () {
        scene.style.opacity = 0;
        setTimeout(function () { scene.style.setProperty("--city-photo", "url('" + url + "')"); scene.style.opacity = 1; }, 350);
      };
      img.src = url;
    });
  }

  /* ------------------------------------------------------------ boot */
  document.addEventListener("DOMContentLoaded", function () {
    var lang = "en", theme = doc.getAttribute("data-theme") || "dark";
    try { lang = localStorage.getItem("atmos-lang") || "en"; } catch (e) {}
    setTheme(theme); applyLang(lang);
    var tb = $("#theme-toggle"), lb = $("#lang-toggle");
    if (tb) tb.addEventListener("click", function () { setTheme(doc.getAttribute("data-theme") === "dark" ? "light" : "dark"); drawAll(); });
    if (lb) lb.addEventListener("click", function () {
      lang = (doc.getAttribute("lang") === "ar") ? "en" : "ar";
      try { localStorage.setItem("atmos-lang", lang); } catch (e) {}
      applyLang(lang);
    });
    initLatest(); initScene(); drawAll();
  });
})();
