// Apex Transporte: language switcher for the whole site.
// Visitors pick a language and the page translates, including the live leaderboard.
// To add or remove a language, edit the LANGS list below.
(function () {
  var SOURCE = "en";
  var LANGS = [
    ["en", "English"],
    ["tr", "Türkçe"],
    ["es", "Español"],
    ["fr", "Français"],
    ["de", "Deutsch"],
    ["pt", "Português"],
    ["ru", "Русский"],
    ["pl", "Polski"],
    ["ar", "العربية"],
    ["hi", "हिन्दी"],
    ["id", "Bahasa Indonesia"],
    ["sw", "Kiswahili"],
    ["zu", "isiZulu"],
    ["af", "Afrikaans"]
  ];

  function getCookie(name) {
    var m = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return m ? decodeURIComponent(m[1]) : "";
  }

  function currentLang() {
    var parts = getCookie("googtrans").split("/");
    return parts[2] || SOURCE;
  }

  function setLang(code) {
    var expired = "expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
    if (code === SOURCE) {
      document.cookie = "googtrans=; " + expired;
      document.cookie = "googtrans=; " + expired + "; domain=" + location.hostname;
    } else {
      document.cookie = "googtrans=/" + SOURCE + "/" + code + "; path=/";
    }
    location.reload();
  }

  var style = document.createElement("style");
  style.textContent =
    "#apex-lang{position:fixed;right:16px;bottom:calc(16px + env(safe-area-inset-bottom,0px));z-index:9999;display:flex;align-items:center;gap:8px;background:#111;border:1px solid #d62828;border-radius:10px;padding:6px 10px;font-family:inherit}" +
    "#apex-lang label{color:#fff;font-size:13px}" +
    "#apex-lang select{background:#d62828;color:#fff;border:0;border-radius:8px;padding:8px 10px;font-size:14px;font-family:inherit;cursor:pointer}" +
    "#apex-lang select:focus-visible{outline:2px solid #fff;outline-offset:2px}" +
    "iframe.skiptranslate,.VIpgJd-ZVi9od-ORHb-OEVmcd{display:none!important}" +
    "body{top:0!important}" +
    ".goog-tooltip{display:none!important}" +
    ".goog-text-highlight{background:none!important;box-shadow:none!important}";
  document.head.appendChild(style);

  function build() {
    var box = document.createElement("div");
    box.id = "apex-lang";
    box.className = "notranslate";
    box.setAttribute("translate", "no");

    var label = document.createElement("label");
    label.setAttribute("for", "apex-lang-select");
    label.textContent = "Language";

    var select = document.createElement("select");
    select.id = "apex-lang-select";
    select.setAttribute("aria-label", "Choose your language");

    var active = currentLang();
    LANGS.forEach(function (l) {
      var opt = document.createElement("option");
      opt.value = l[0];
      opt.textContent = l[1];
      if (l[0] === active) opt.selected = true;
      select.appendChild(opt);
    });
    select.addEventListener("change", function () {
      setLang(select.value);
    });

    var holder = document.createElement("div");
    holder.id = "apex-gt";
    holder.style.cssText = "position:absolute;left:-9999px;top:0;width:1px;height:1px;overflow:hidden";

    box.appendChild(label);
    box.appendChild(select);
    document.body.appendChild(box);
    document.body.appendChild(holder);
  }

  function loadTranslator() {
    window.googleTranslateElementInit = function () {
      new google.translate.TranslateElement(
        { pageLanguage: SOURCE, autoDisplay: false },
        "apex-gt"
      );
    };
    var s = document.createElement("script");
    s.src = "https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit";
    s.async = true;
    document.head.appendChild(s);
  }

  function start() {
    build();
    if (currentLang() !== SOURCE) loadTranslator();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
