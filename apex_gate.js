/* Apex members-only gate.
   Load order: this file runs first. It checks the Discord sign-in, fills the private parts of the page
   from the bot, then loads app.js. Private files (data, net_worth, apex_drivers, members) are fetched
   from the locked bot route instead of the public site. */
(function () {
  var API = "https://apex-bot-52td.onrender.com";
  var KEY = "apex_token";
  var PRIVATE = /(?:^|\/)(data|net_worth|apex_drivers|members)\.json(?:\?|$)/;
  var realFetch = window.fetch.bind(window);

  var style = document.createElement("style");
  style.textContent = "body:not(.apex-member) [data-members-only]{display:none!important}" +
    "[data-gate-message]{display:none}" +
    "body:not(.apex-member):not(.apex-wait) [data-gate-message]{display:block}";
  document.head.appendChild(style);

  var hash = location.hash;
  var denied = hash.indexOf("#apex_denied=1") === 0;
  if (hash.indexOf("#apex_token=") === 0) {
    try { localStorage.setItem(KEY, hash.slice(12)); } catch (e) {}
  }
  if (hash.indexOf("#apex_") === 0) {
    history.replaceState(null, "", location.pathname + location.search);
  }

  function token() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function drop() { try { localStorage.removeItem(KEY); } catch (e) {} }
  function loginUrl() { return API + "/auth/login"; }

  /* app.js asks for the private files by their old names. Send those requests to the locked route. */
  window.fetch = function (input, init) {
    var url = typeof input === "string" ? input : (input && input.url) || "";
    var m = PRIVATE.exec(url);
    if (!m) return realFetch(input, init);
    var t = token();
    if (!t) {
      /* Visitors get company totals only (for the Our numbers box). Everything else never answers,
         because a rejected request would let app.js fill the page with partial numbers. */
      if (m[1] === "data") return realFetch(API + "/api/public", { cache: "no-store" });
      return new Promise(function () {});
    }
    return realFetch(API + "/api/file/" + m[1] + ".json", {
      headers: { Authorization: "Bearer " + t }, cache: "no-store"
    }).then(function (r) {
      if (!r.ok) throw new Error("locked");
      /* Show keem under the Discord name Apex | keem everywhere on the site. */
      return r.text().then(function (text) {
        return new Response(text.split("Corprate keem").join("Apex | keem"), {
          status: r.status, headers: r.headers
        });
      });
    });
  };

  function loadApp() {
    var s = document.createElement("script");
    s.src = "app.js?v=2";
    document.body.appendChild(s);
  }

  function showLocked() {
    document.body.classList.remove("apex-wait");
    document.body.classList.remove("apex-member");
    document.querySelectorAll("[data-sign-in]").forEach(function (a) { a.href = loginUrl(); });
    document.querySelectorAll("[data-denied-note]").forEach(function (n) {
      n.style.display = denied ? "block" : "none";
    });
  }

  function fill(d) {
    var table = document.getElementById("jobsTable");
    var rename = function (html) { return String(html).split("Corprate keem").join("Apex | keem"); };
    if (table && d.jobs_rows) table.insertAdjacentHTML("beforeend", rename(d.jobs_rows));
    var list = document.getElementById("dlist");
    if (list && d.dlist) list.innerHTML = rename(d.dlist);
  }

  function start() {
    var t = token();
    if (!t) { showLocked(); loadApp(); return; }
    document.body.classList.add("apex-wait");
    realFetch(API + "/api/static", { headers: { Authorization: "Bearer " + t }, cache: "no-store" })
      .then(function (r) {
        if (r.status === 401 || r.status === 403) { drop(); return null; }
        if (!r.ok) throw new Error("bad status");
        return r.json();
      })
      .then(function (d) {
        if (!d) { showLocked(); loadApp(); return; }
        fill(d);
        document.body.classList.remove("apex-wait");
        document.body.classList.add("apex-member");
        loadApp();
      })
      .catch(function () { showLocked(); loadApp(); });
  }

  window.ApexGate = {
    loginUrl: loginUrl,
    signOut: function () { drop(); location.reload(); }
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
