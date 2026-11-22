/* Apex members-only gate. Put this file next to index.html and load it with:
   <script src="apex_gate.js" defer></script>
   Mark each private section with data-members-only.
   Add one box with data-gate-message holding your Join Discord button and a Sign in link. */
(function () {
  var API = "https://YOUR-RENDER-URL.onrender.com"; // change to your Render address
  var KEY = "apex_token";
  var style = document.createElement("style");
  style.textContent = "[data-members-only]{display:none}[data-gate-message]{display:none}" +
    "body.apex-member [data-members-only]{display:block}" +
    "body:not(.apex-member) [data-gate-message]{display:block}";
  document.head.appendChild(style);

  var hash = location.hash;
  var denied = hash.indexOf("#apex_denied=1") === 0;
  if (hash.indexOf("#apex_token=") === 0) {
    try { localStorage.setItem(KEY, hash.slice(12)); } catch (e) {}
  }
  if (hash.indexOf("#apex_") === 0) {
    history.replaceState(null, "", location.pathname + location.search);
  }

  function loginUrl() { return API + "/auth/login"; }
  function token() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }

  function showLocked() {
    document.body.classList.remove("apex-member");
    document.querySelectorAll("[data-sign-in]").forEach(function (a) { a.href = loginUrl(); });
    document.querySelectorAll("[data-denied-note]").forEach(function (n) {
      n.style.display = denied ? "block" : "none";
    });
  }

  function load() {
    var t = token();
    if (!t) { showLocked(); return; }
    fetch(API + "/api/data", { headers: { Authorization: "Bearer " + t } })
      .then(function (r) {
        if (r.status === 401 || r.status === 403) {
          try { localStorage.removeItem(KEY); } catch (e) {}
          showLocked();
          return null;
        }
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        document.body.classList.add("apex-member");
        window.ApexData = data;
        document.dispatchEvent(new CustomEvent("apex:data", { detail: data }));
      })
      .catch(showLocked);
  }

  window.ApexGate = {
    loginUrl: loginUrl,
    signOut: function () { try { localStorage.removeItem(KEY); } catch (e) {} location.reload(); }
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", load);
  else load();
})();
