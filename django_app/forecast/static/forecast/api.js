/* API playground: edit params -> live cURL / Python / JS snippets -> send the request and show a formatted response. */
(function (root) {
  "use strict";

  function escapeHtml(s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }

  /* JSON -> HTML with the same colours as the static docs (k = key, s = string, n = number/bool, c = null) */
  function highlight(obj) {
    var json = escapeHtml(typeof obj === "string" ? obj : JSON.stringify(obj, null, 2));
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (m) {
      var cls = "n";
      if (/^"/.test(m)) cls = /:$/.test(m) ? "k" : "s";
      else if (/null/.test(m)) cls = "c";
      return '<span class="' + cls + '">' + m + "</span>";
    });
  }

  function buildUrl(origin, params) {
    var q = Object.keys(params).map(function (k) { return encodeURIComponent(k) + "=" + encodeURIComponent(params[k]); }).join("&");
    return origin + "/api/predict/?" + q;
  }

  var NUMERIC = { temperature: 1, humidity: 1, wind_speed: 1, pressure: 1 };
  function val(k, v) { return NUMERIC[k] && v !== "" && !isNaN(Number(v)) ? String(Number(v)) : v; }

  function snippet(kind, origin, params) {
    var keys = Object.keys(params), url = origin + "/api/predict/";
    if (kind === "curl") {
      return "curl -G \"" + url + "\" \\\n" + keys.map(function (k) { return "  --data-urlencode \"" + k + "=" + params[k] + "\""; }).join(" \\\n");
    }
    if (kind === "python") {
      return "import requests\n\nr = requests.get(\n    \"" + url + "\",\n    params={\n" +
        keys.map(function (k) { return "        \"" + k + "\": " + (NUMERIC[k] && params[k] !== "" && !isNaN(Number(params[k])) ? val(k, params[k]) : "\"" + params[k] + "\"") + ","; }).join("\n") +
        "\n    },\n)\nr.raise_for_status()\nprint(r.json()[\"forecast\"])";
    }
    return "const params = new URLSearchParams({\n" + keys.map(function (k) { return "  " + k + ": \"" + params[k] + "\","; }).join("\n") +
      "\n});\nconst res = await fetch(\"" + url + "?\" + params);\nconst data = await res.json();\nconsole.log(data.forecast);";
  }

  var api = { highlight: highlight, buildUrl: buildUrl, snippet: snippet };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof document === "undefined") return;

  /* ------------------------------------------------------------------ DOM wiring */
  var $ = function (s) { return document.querySelector(s); };
  var FIELDS = ["city", "model", "temperature", "humidity", "wind_speed", "pressure", "date"];
  var tab = "curl";

  function params() {
    var p = {};
    FIELDS.forEach(function (f) { var el = document.getElementById("pg-" + f); if (el) p[f] = el.value; });
    return p;
  }
  function refresh() {
    var p = params();
    $("#pg-code").textContent = snippet(tab, location.origin, p);
    $("#pg-url").textContent = buildUrl(location.origin, p);
  }

  function send() {
    var p = params(), btn = $("#pg-send"), st = $("#pg-status"), tm = $("#pg-time"), out = $("#pg-response"), t0 = performance.now();
    btn.disabled = true; st.className = "pill"; st.textContent = "Sending…"; tm.textContent = "— ms";
    fetch(buildUrl("", p), { headers: { Accept: "application/json" } })
      .then(function (r) {
        return r.text().then(function (text) {
          var ms = Math.round(performance.now() - t0), body;
          try { body = JSON.parse(text); out.innerHTML = highlight(body); } catch (e) { out.textContent = text; }
          st.className = "pill " + (r.ok ? "ok" : "bad"); st.textContent = r.status + " " + (r.statusText || (r.ok ? "OK" : "Error")); tm.textContent = ms + " ms";
        });
      })
      .catch(function (e) { st.className = "pill bad"; st.textContent = "Network error"; out.textContent = String(e); })
      .then(function () { btn.disabled = false; });
  }

  function copy(id, btn) {
    var text = document.getElementById(id).textContent, done = function () { var o = btn.textContent; btn.textContent = "Copied ✓"; setTimeout(function () { btn.textContent = o; }, 1400); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, done);
    else { var ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select(); try { document.execCommand("copy"); } catch (e) {} document.body.removeChild(ta); done(); }
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!$("#playground")) return;
    var d = document.getElementById("pg-date"); if (d && !d.value) d.value = new Date().toISOString().slice(0, 10);
    FIELDS.forEach(function (f) { var el = document.getElementById("pg-" + f); if (el) { el.addEventListener("input", refresh); el.addEventListener("change", refresh); } });
    Array.prototype.forEach.call(document.querySelectorAll(".tab"), function (b) {
      b.addEventListener("click", function () {
        tab = b.getAttribute("data-tab");
        Array.prototype.forEach.call(document.querySelectorAll(".tab"), function (x) { x.classList.toggle("active", x === b); });
        refresh();
      });
    });
    Array.prototype.forEach.call(document.querySelectorAll(".copy-btn"), function (b) { b.addEventListener("click", function () { copy(b.getAttribute("data-copy"), b); }); });
    $("#pg-send").addEventListener("click", send);
    refresh();
  });
})(typeof window !== "undefined" ? window : this);
