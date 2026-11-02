;(function(){try{
(function(){var q=document.getElementById("dq"),cards=document.querySelectorAll(".dcard"),groups=document.querySelectorAll(".dgroup"),c=document.getElementById("dcount"),n=document.getElementById("dnone");
    function f(){cards=document.querySelectorAll(".dcard");groups=document.querySelectorAll(".dgroup");var v=q.value.trim().toLowerCase(),k=0;
    cards.forEach(function(x){var m=!v||x.getAttribute("data-n").indexOf(v)>-1;x.hidden=!m;if(m)k++;});
    groups.forEach(function(g){g.hidden=!g.querySelector(".dcard:not([hidden])");});
    c.textContent=v?k+" of "+cards.length+" drivers":cards.length+" drivers";n.hidden=k>0;}
    q.addEventListener("input",f);})();
}catch(e){console.error(e)}})();
;(function(){try{
(function(){
var gal=document.getElementById("gal");if(!gal)return;
var figs=[].slice.call(gal.querySelectorAll(".shot")),chips=document.querySelectorAll(".gchip"),
cnt=document.getElementById("gcount"),more=document.getElementById("gmore"),empty=document.getElementById("gempty"),
STEP=12,limit=STEP,filt="All",shown=[];
function render(){
var match=figs.filter(function(f){return filt==="All"||f.getAttribute("data-cat")===filt;});
shown=match.slice(0,limit);
figs.forEach(function(f){f.hidden=shown.indexOf(f)<0;});
cnt.textContent="Showing "+shown.length+" of "+match.length+" photos";
more.hidden=match.length<=limit;
empty.hidden=match.length>0;}
chips.forEach(function(c){c.addEventListener("click",function(){
filt=c.getAttribute("data-f");limit=STEP;
chips.forEach(function(x){var on=x===c;x.classList.toggle("on",on);x.setAttribute("aria-pressed",on);});
render();});});
more.addEventListener("click",function(){limit+=STEP;render();});
render();
var lb=document.getElementById("lb"),li=lb.querySelector("img"),cap=document.getElementById("lcap"),idx=0,last=null;
function show(){var f=shown[idx],i=f.querySelector("img");li.src=i.src;li.alt=i.alt;
cap.innerHTML="";cap.appendChild(document.createTextNode(f.querySelector("figcaption").textContent));
var sm=document.createElement("small");sm.textContent=(idx+1)+" of "+shown.length;cap.appendChild(sm);}
function openAt(n){last=document.activeElement;idx=n;show();lb.hidden=false;document.body.style.overflow="hidden";document.getElementById("lbx0").focus();}
function close(){lb.hidden=true;document.body.style.overflow="";if(last)last.focus();}
function step(d){idx=(idx+d+shown.length)%shown.length;show();}
gal.addEventListener("click",function(e){var b=e.target.closest(".zoom");if(!b)return;openAt(shown.indexOf(b.closest(".shot")));});
document.getElementById("lbx0").addEventListener("click",function(e){e.stopPropagation();close();});
document.getElementById("lbp").addEventListener("click",function(e){e.stopPropagation();step(-1);});
document.getElementById("lbn").addEventListener("click",function(e){e.stopPropagation();step(1);});
lb.addEventListener("click",function(e){if(e.target===lb)close();});
document.addEventListener("keydown",function(e){if(lb.hidden)return;
if(e.key==="Escape")close();if(e.key==="ArrowLeft")step(-1);if(e.key==="ArrowRight")step(1);});
var sx=0;lb.addEventListener("touchstart",function(e){sx=e.touches[0].clientX;},{passive:true});
lb.addEventListener("touchend",function(e){var d=e.changedTouches[0].clientX-sx;if(Math.abs(d)>50)step(d<0?1:-1);});
})();
}catch(e){console.error(e)}})();
;(function(){try{
(function(){var i=document.getElementById("jobSearch"),t=document.getElementById("jobsTable"),c=document.getElementById("jobCount");
if(!i||!t)return;i.addEventListener("input",function(){var q=i.value.toLowerCase().trim(),n=0;
t.querySelectorAll(".jr:not(.hd)").forEach(function(r){var ok=r.querySelector("b").textContent.toLowerCase().indexOf(q)>-1;r.hidden=!ok;if(ok)n++;});
c.textContent=n+" drivers";});})();
}catch(e){console.error(e)}})();
;(function(){try{
/* ---- Live data from the Apex Data bot ----
   Once your bot is hosted online, paste its feed address below,
   e.g. "https://your-app.up.railway.app/apex-feed.json"
   Leave it as "" to keep showing the fixed numbers above. */
const APEX_FEED_URL = "";

(function () {
  if (!APEX_FEED_URL) return;

  function fmtKm(n) {
    return Math.round(n).toLocaleString("en-US") + " km";
  }
  function fmtHours(mins) {
    const h = mins / 60;
    return Math.round(h).toLocaleString("en-US") + " h";
  }
  function fmtDate(iso) {
    if (!iso) return "\u2014";
    const d = new Date(iso);
    return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  }
  function fmtTime(mins) {
    const h = Math.floor(mins / 60), m = mins % 60;
    return h.toLocaleString("en-US") + " h " + m + " m";
  }

  fetch(APEX_FEED_URL, { cache: "no-store" })
    .then((r) => r.json())
    .then((data) => {
      const s = data.stats || {};
      const set = (key, val) => {
        const el = document.querySelector('[data-stat="' + key + '"] b');
        if (el && val !== null && val !== undefined) el.textContent = val;
      };
      set("activeDrivers", s.activeDrivers);
      set("totalDistanceKm", s.totalDistanceKm != null ? fmtKm(s.totalDistanceKm) : null);
      set("drivingTimeMinutes", s.drivingTimeMinutes != null ? fmtHours(s.drivingTimeMinutes) : null);
      set("totalRuns", s.totalRuns);
      set("latestJob", fmtDate(new Date().toISOString()));

      const src = document.getElementById("statSrc");
      if (src && data.updated) {
        src.textContent = "Live from our Discord \u2022 updated " + new Date(data.updated).toLocaleString();
      }

      if (Array.isArray(data.jobs) && data.jobs.length) {
        const table = document.getElementById("jobsTable");
        const header = table.querySelector(".jr.hd");
        table.innerHTML = "";
        table.appendChild(header);
        data.jobs.slice(0, 50).forEach((j) => {
          const row = document.createElement("div");
          row.className = "jr";
          const level = j.levelAfter ? String(j.levelAfter) : "\u2014";
          const fuel = j.fuelLiters != null ? j.fuelLiters + " l" : "\u2014";
          row.innerHTML =
            '<b data-l="Driver">' + j.driver + "</b>" +
            '<span data-l="Distance">' + j.distanceKm + " km</span>" +
            '<span data-l="Time">' + fmtTime(j.timeMinutes) + "</span>" +
            '<span data-l="Fuel">' + fuel + "</span>" +
            '<span class="inc" data-l="Income">\u20ac' + j.incomeEur.toLocaleString() + "</span>" +
            '<span data-l="Level">' + level + "</span>";
          table.appendChild(row);
        });
      }
    })
    .catch(() => {
      /* Feed unreachable — the fixed numbers above stay as they are. */
    });
})();
}catch(e){console.error(e)}})();
;(function(){try{
/* ---- Fills the Job log table from data.json (written by the Discord bot) ---- */
(function () {
  var DASH = "\u2014";
  var LABELS = ["Total distance", "Last job", "Time", "Fuel", "Income", "Level", "Net worth"];
  function norm(s) { return String(s || "").toLowerCase().replace(/[^a-z0-9]/g, ""); }
  function empty(el) { var t = el.textContent.trim(); return !t || t === DASH; }
  function cell(row, label) { return row.querySelector('[data-l="' + label + '"]'); }
  function fill(row, label, val, note) {
    var el = cell(row, label);
    if (el && val && empty(el)) { el.textContent = val; if (note) el.title = note; }
  }
  function put(row, label, val, note) {
    var el = cell(row, label);
    if (el && val) { el.textContent = val; if (note) el.title = note; }
  }
  /* The level is the LEFT number on the job result bar (for example 9 in "9 to 10") */
  function levelOf(m) {
    if (m.level) return String(m.level);
    var t = String(m.last_level || "").match(/^\D*(\d+)/);
    return t ? t[1] : null;
  }
  function apply(row, m) {
    put(row, "Total distance", m.distance, "Total from job log screenshots");
    put(row, "Last job", m.last_km);
    put(row, "Time", m.last_time);
    put(row, "Fuel", m.last_fuel);
    put(row, "Income", m.last_income);
    put(row, "Level", levelOf(m));
    if (m.networth && m.networth !== "\u20ac0") { put(row, "Net worth", m.networth); row.setAttribute("data-nw", "bot"); }
  }
  function setStat(key, val) {
    var el = document.querySelector('[data-stat="' + key + '"] b');
    if (el && val) el.textContent = val;
  }
  function newRow(name) {
    var row = document.createElement("div");
    row.className = "jr jr8";
    var b = document.createElement("b");
    b.setAttribute("data-l", "Driver");
    b.textContent = name;
    row.appendChild(b);
    LABELS.forEach(function (l) {
      var s = document.createElement("span");
      s.setAttribute("data-l", l);
      if (l === "Income" || l === "Net worth") s.className = "inc";
      s.textContent = DASH;
      row.appendChild(s);
    });
    return row;
  }
  function norm2(s) {
    return String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/\u00f8/gi, "o")
      .toLowerCase().replace(/^apex_/, "").replace(/[^a-z0-9]/g, "");
  }
  function money(n) {
    if (n == null) return null;
    return "\u20ac" + Math.round(n).toLocaleString("en-US");
  }
  function kmText(n) {
    if (n == null) return null;
    return Math.round(n).toLocaleString("en-US") + " km";
  }
  function loadNetWorth() {
    var FIXED = { "Apex|Baku": 23156, "Apex | kretek": 110714 };
    return fetch("net_worth.json?v=" + Date.now(), { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .catch(function () { return {}; })
      .then(function (d) {
        d = d || {};
        Object.keys(FIXED).forEach(function (k) {
          Object.keys(d).forEach(function (x) { if (norm2(x) === norm2(k)) delete d[x]; });
          d[k] = FIXED[k];
        });
        var byName = {}, total = 0;
        Object.keys(d).forEach(function (k) { byName[norm2(k)] = d[k]; total += Number(d[k]) || 0; });
        var table = document.getElementById("jobsTable");
        if (table) {
          [].slice.call(table.querySelectorAll(".jr:not(.hd)")).forEach(function (row) {
            var v = byName[norm2(row.querySelector("b").textContent)];
            if (v != null && row.getAttribute("data-nw") !== "bot") put(row, "Net worth", money(v));
          });
        }
        if (!window.__botTotal) setStat("netWorth", money(total));
      })
      .catch(function () { /* net_worth.json missing: the saved values stay as they are */ });
  }
  function loadApex() {
    return fetch("apex_drivers.json?v=" + Date.now(), { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var table = document.getElementById("jobsTable");
        if (!table) return;
        var members = Array.isArray(d.members) ? d.members : [];
        var rows = {};
        [].slice.call(table.querySelectorAll(".jr:not(.hd)")).forEach(function (row) {
          rows[norm2(row.querySelector("b").textContent)] = row;
        });
        members.forEach(function (m) {
          var k = norm2(m.name), row = rows[k];
          if (!row) { row = newRow(m.name); table.appendChild(row); rows[k] = row; }
          fill(row, "Net worth", money(m.netWorth));
          fill(row, "Total distance", kmText(m.distanceKm));
          var j = m.job;
          if (j) {
            fill(row, "Last job", j.km == null ? null : j.km + " km");
            fill(row, "Time", j.time);
            fill(row, "Fuel", j.fuelL == null ? null : j.fuelL + " l");
            fill(row, "Income", j.income == null ? null : "\u20AC" + Number(j.income).toLocaleString("en-US"));
            var lv = j.levelFrom || j.levelTo;
            if (lv) fill(row, "Level", String(lv));
          }
        });
        var c = document.getElementById("jobCount");
        if (c) c.textContent = table.querySelectorAll(".jr:not(.hd)").length + " drivers";
      })
      .catch(function () { /* apex_drivers.json missing: the table stays as it is */ });
  }
  fetch("data.json?v=" + Date.now(), { cache: "no-store" })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      setStat("activeDrivers", d.drivers);
      setStat("totalDistanceKm", d.distance);
      setStat("drivingTimeMinutes", d.hours);
      setStat("totalRuns", d.runs);
      if (d.networth) { window.__botTotal = true; setStat("netWorth", d.networth); }
      var table = document.getElementById("jobsTable");
      if (!table) return;
      var members = Array.isArray(d.members) ? d.members : [];
      var byName = {};
      var exact = {};
      members.forEach(function (m) { byName[norm(m.name)] = m; exact[m.name] = m; });
      var ALIASES = {
        "blaxthegamer092": "APEX | \u026Es\u2295Blaxthegamer",
        "rex": "REX \ud83c\uddf9\ud83c\uddf7",
        "ronin": "R\u00f8\u014b\u0131\u014b_ \u2070\u2070\u20708",
        "asad": "\u13aa\u1d18\u1d07x | \u13aas\u1d00\u1d05\u4e97",
        "anas": "\u261c\u2620\ud835\udc00\ud835\udc0d\ud835\udc00\ud835\udc12\u2620\u261e"
      };
      function find(name) {
        var n = norm(name);
        var al = ALIASES[norm2(name)];
        if (al && exact[al]) return exact[al];
        if (al && byName[norm(al)]) return byName[norm(al)];
        if (byName[n]) return byName[n];
        if (n.length < 4) return null;
        for (var k in byName) { if (k.length >= 4 && (k.indexOf(n) > -1 || n.indexOf(k) > -1)) return byName[k]; }
        return null;
      }
      var known = {};
      [].slice.call(table.querySelectorAll(".jr:not(.hd)")).forEach(function (row) {
        var name = row.querySelector("b").textContent;
        known[norm(name)] = true;
        var m = find(name);
        if (m) { apply(row, m); known[norm(m.name)] = true; }
      });
      var crew = [].slice.call(document.querySelectorAll("#dlist .dcard b")).map(function (b) { return b.textContent.trim(); });
      members.forEach(function (m) { crew.push(m.name); });
      crew.forEach(function (name) {
        var n = norm(name);
        if (!n || known[n]) return;
        known[n] = true;
        var row = newRow(name);
        var m = find(name);
        if (m) apply(row, m);
        table.appendChild(row);
      });
      var c = document.getElementById("jobCount");
      if (c) c.textContent = table.querySelectorAll(".jr:not(.hd)").length + " drivers";
      {
        var dt = new Date(), el = document.querySelector('[data-stat="latestJob"] b');
        if (el && !isNaN(dt)) el.textContent = dt.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
      }
    })
    .catch(function () { /* data.json missing or unreachable: the table stays as it is */ })
    .then(loadApex)
    .then(loadNetWorth);
})();
}catch(e){console.error(e)}})();
;(function(){try{
(function () {
  var table = document.getElementById("jobsTable");
  var search = document.getElementById("jobSearch");
  if (!table || !search) return;
  var mode = "distance";
  var DASH = "\u2014";

  function num(t) {
    var m = String(t || "").match(/([\d.,]+)(?:\s*([kKmM])(?![a-zA-Z]))?/);
    if (!m) return -1;
    var v = parseFloat(m[1].replace(/,/g, ""));
    if (isNaN(v)) return -1;
    if (m[2] === "k" || m[2] === "K") v *= 1e3;
    if (m[2] === "m" || m[2] === "M") v *= 1e6;
    return v;
  }
  function val(row, label) {
    var el = row.querySelector('[data-l="' + label + '"]');
    return el ? el.textContent.trim() : "";
  }
  function key(row) {
    if (mode === "level") return num(val(row, "Level"));
    if (mode === "income") return num(val(row, "Income"));
    if (mode === "networth") return num(val(row, "Net worth"));
    return num(val(row, "Total distance"));
  }

  var bar = document.createElement("div");
  bar.className = "sortbar";
  [["distance", "Distance"], ["level", "Level"], ["income", "Income"], ["networth", "Net worth"]].forEach(function (o) {
    var b = document.createElement("button");
    b.type = "button";
    b.textContent = o[1];
    b.setAttribute("data-mode", o[0]);
    b.setAttribute("aria-pressed", o[0] === mode ? "true" : "false");
    b.addEventListener("click", function () {
      mode = o[0];
      [].slice.call(bar.children).forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
      enhance();
    });
    bar.appendChild(b);
  });
  search.parentNode.insertBefore(bar, table);

  var obs = new MutationObserver(function () { clearTimeout(timer); timer = setTimeout(enhance, 250); });
  var timer;
  function watch() { obs.observe(table, { childList: true, subtree: true, characterData: true }); }

  function enhance() {
    obs.disconnect();
    var rows = [].slice.call(table.querySelectorAll(".jr:not(.hd)"));
    rows.sort(function (a, b) { return key(b) - key(a); });
    rows.forEach(function (r, i) {
      table.appendChild(r);
      var name = r.querySelector("b");
      if (name) name.setAttribute("data-rank", String(i + 1));
      var empty = 0;
      [].slice.call(r.querySelectorAll("span")).forEach(function (sp) {
        var isDash = sp.textContent.trim() === DASH;
        sp.classList.toggle("nd", isDash);
        if (isDash) empty++;
      });
      r.classList.toggle("sparse", empty >= 5);
    });
    watch();
  }
  watch();
  setTimeout(enhance, 1200);
  setTimeout(enhance, 4000);

  function ago(d) {
    var s = Math.max(0, Math.round((Date.now() - d.getTime()) / 1000));
    if (s < 90) return "just now";
    var m = Math.round(s / 60);
    if (m < 60) return m + " minutes ago";
    var h = Math.round(m / 60);
    if (h < 48) return h + (h === 1 ? " hour ago" : " hours ago");
    var dd = Math.round(h / 24);
    return dd + " days ago";
  }
  fetch("data.json?v=" + Date.now(), { cache: "no-store" })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      var el = document.getElementById("statSrc");
      var dt = d.latest_date ? new Date(d.latest_date) : null;
      if (el && dt && !isNaN(dt)) {
        el.innerHTML = '<span class="livedot" aria-hidden="true"></span>Live from our Discord. Latest job ' + ago(dt) + ".";
      }
    })
    .catch(function () {});

  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  ["activeDrivers", "totalDistanceKm", "drivingTimeMinutes", "totalRuns"].forEach(function (k) {
    var el = document.querySelector('[data-stat="' + k + '"] b');
    if (!el || reduce) return;
    var done = false;
    var so = new MutationObserver(function () {
      if (done) return;
      var m = el.textContent.match(/^([\d,]+)(.*)$/);
      if (!m) return;
      done = true;
      so.disconnect();
      var target = parseInt(m[1].replace(/,/g, ""), 10), rest = m[2], t0 = null;
      function step(ts) {
        if (t0 === null) t0 = ts;
        var p = Math.min(1, (ts - t0) / 900);
        el.textContent = Math.round(target * p).toLocaleString("en-US") + rest;
        if (p < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    });
    so.observe(el, { childList: true, characterData: true, subtree: true });
  });
})();
}catch(e){console.error(e)}})();
;(function(){try{
(function () {
  var table = document.getElementById("jobsTable");
  var root = document.getElementById("lbx");
  if (!table || !root) return;
  var mode = "distance";
  var MODES = [["distance", "Distance", "Total distance"], ["networth", "Net worth", "Net worth"]];

  function num(t) {
    var m = String(t || "").match(/([\d.,]+)(?:\s*([kKmM])(?![a-zA-Z]))?/);
    if (!m) return -1;
    var v = parseFloat(m[1].replace(/,/g, ""));
    if (isNaN(v)) return -1;
    if (m[2] === "k" || m[2] === "K") v *= 1e3;
    if (m[2] === "m" || m[2] === "M") v *= 1e6;
    return v;
  }
  function esc(t) {
    return String(t).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; });
  }
  function label() {
    for (var i = 0; i < MODES.length; i++) if (MODES[i][0] === mode) return MODES[i][2];
    return "Total distance";
  }
  function collect() {
    var lab = label();
    return [].slice.call(table.querySelectorAll(".jr:not(.hd)")).map(function (r) {
      var b = r.querySelector("b");
      var el = r.querySelector('[data-l="' + lab + '"]');
      var txt = el ? el.textContent.trim() : "";
      return { name: b ? b.textContent.trim() : "", txt: txt, v: num(txt) };
    }).filter(function (x) { return x.name && x.v > 0; })
      .sort(function (a, b) { return b.v - a.v; });
  }
  function rowHtml(x, i, top) {
    var w = Math.max(3, Math.round((x.v / top) * 100));
    return '<li><span class="rk2">' + (i + 1) + '</span><div><div class="nm">' + esc(x.name) +
      '</div><i class="bar" data-w="' + w + '"></i></div><span class="vl">' + esc(x.txt) + "</span></li>";
  }
  function render() {
    var list = collect();
    var html = '<div class="sortbar" role="group" aria-label="Rank by">';
    MODES.forEach(function (m) {
      html += '<button type="button" data-mode="' + m[0] + '" aria-pressed="' + (m[0] === mode) + '">' + m[1] + "</button>";
    });
    html += "</div>";
    if (!list.length) {
      root.innerHTML = html + '<p class="src">No data yet.</p>';
      bind();
      return;
    }
    var top = list[0].v;
    html += '<div class="lbx-pod">';
    list.slice(0, 3).forEach(function (x, i) {
      html += '<div class="pcard p' + (i + 1) + '"><div class="pr">' + (i + 1) + '</div><div class="pn">' + esc(x.name) +
        '</div><div class="pv">' + esc(x.txt) + "</div></div>";
    });
    html += "</div>";
    var mid = list.slice(3, 10);
    if (mid.length) {
      html += '<ol class="lbx-list" start="4">';
      mid.forEach(function (x, i) { html += rowHtml(x, i + 3, top); });
      html += "</ol>";
    }
    var rest = list.slice(10);
    if (rest.length) {
      html += '<details class="lbx-more"><summary>Show ranks 11 to ' + list.length + '</summary><ol class="lbx-list" start="11">';
      rest.forEach(function (x, i) { html += rowHtml(x, i + 10, top); });
      html += "</ol></details>";
    }
    var open = root.querySelector("details") && root.querySelector("details").open;
    root.innerHTML = html;
    if (open && root.querySelector("details")) root.querySelector("details").open = true;
    bind();
    requestAnimationFrame(function () {
      [].slice.call(root.querySelectorAll(".bar")).forEach(function (b) { b.style.width = b.getAttribute("data-w") + "%"; });
    });
  }
  function bind() {
    [].slice.call(root.querySelectorAll(".sortbar button")).forEach(function (b) {
      b.addEventListener("click", function () { mode = b.getAttribute("data-mode"); render(); });
    });
  }
  var timer;
  new MutationObserver(function () { clearTimeout(timer); timer = setTimeout(render, 400); })
    .observe(table, { childList: true, subtree: true, characterData: true });
  render();
  setTimeout(render, 1800);
  setTimeout(render, 4800);
})();
}catch(e){console.error(e)}})();
;(function(){try{
(function () {
  var table = document.getElementById("jobsTable");
  function getCards() { return [].slice.call(document.querySelectorAll(".scard")); }
  if (!table || !getCards().length) return;
  function n2(s) {
    return String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/\u00f8/gi, "o")
      .toLowerCase().replace(/^apex_/, "").replace(/[^a-z0-9]/g, "");
  }
  function fill() {
    var rows = {};
    [].slice.call(table.querySelectorAll(".jr:not(.hd)")).forEach(function (r) {
      var b = r.querySelector("b");
      if (b) rows[n2(b.textContent)] = r;
    });
    getCards().forEach(function (c) {
      var r = rows[n2(c.getAttribute("data-name"))];
      var el = r && r.querySelector('[data-l="Total distance"]');
      var t = el ? el.textContent.trim() : "";
      var d = c.querySelector(".sdist");
      if (/\d/.test(t)) { d.textContent = t + " driven"; d.hidden = false; }
      else { d.hidden = true; }
    });
  }
  var timer;
  new MutationObserver(function () { clearTimeout(timer); timer = setTimeout(fill, 400); })
    .observe(table, { childList: true, subtree: true, characterData: true });
  window.__apexFillStaff = fill;
  fill();
  setTimeout(fill, 1800);
  setTimeout(fill, 4800);
})();
}catch(e){console.error(e)}})();
;(function(){try{
(function () {
  var sec = document.getElementById("members");
  var live = document.getElementById("mLive"), liveTxt = document.getElementById("mLiveTxt");
  var q = document.getElementById("mQ");
  var tab = "all", data = null, lastText = "", lastOk = 0, shown = { off: 0, vis: 0, all: 0 };

  function clean(n) {
    var raw = String(n || "").trim();
    var c = raw.replace(/^\s*[\[(]?\s*apex(?![a-z])\s*[\])]?\s*(?:\|\||[|_<>:\-])*\s*/i, "").replace(/^[\s|_<>:\-]+/, "").trim();
    return c || raw;
  }
  function initial(s) {
    var m = String(s).match(/[\p{L}\p{N}]/u);
    return m ? m[0].toUpperCase() : "A";
  }
  function norm(s) { return String(s || "").toLowerCase(); }

  function card(p, visitor, i) {
    var full = String(p.name || "Unknown");
    var shortName = clean(full);
    var el = document.createElement("div");
    el.className = "mcard" + (visitor ? " visitor" : "");
    el.style.setProperty("--i", Math.min(i, 40));
    el.title = full;
    var av = document.createElement("div");
    av.className = "mav";
    function ph() {
      var d = document.createElement("div");
      d.className = "mph";
      d.textContent = initial(shortName);
      av.innerHTML = "";
      av.appendChild(d);
    }
    if (p.avatar) {
      var img = document.createElement("img");
      img.alt = "";
      img.loading = "lazy";
      img.referrerPolicy = "no-referrer";
      img.onerror = ph;
      img.src = p.avatar;
      av.appendChild(img);
    } else { ph(); }
    var tx = document.createElement("div");
    tx.className = "mtx";
    var nm = document.createElement("span");
    nm.className = "mname";
    nm.textContent = shortName;
    var role = document.createElement("span");
    role.className = "mrole";
    role.textContent = visitor ? "Visitor" : "Apex member";
    tx.appendChild(nm);
    tx.appendChild(role);
    el.appendChild(av);
    el.appendChild(tx);
    return el;
  }

  function sorted(list) {
    return list.slice().sort(function (a, b) {
      return clean(a.name).localeCompare(clean(b.name), undefined, { sensitivity: "base" });
    });
  }

  function count(id, to) {
    var el = document.getElementById(id), key = id === "mOff" ? "off" : id === "mVis" ? "vis" : "all";
    var from = shown[key], start = null;
    shown[key] = to;
    if (from === to || window.matchMedia("(prefers-reduced-motion:reduce)").matches) { el.textContent = to; return; }
    function step(t) {
      if (start === null) start = t;
      var k = Math.min(1, (t - start) / 700);
      el.textContent = Math.round(from + (to - from) * (1 - Math.pow(1 - k, 3)));
      if (k < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function render() {
    if (!data) return;
    var off = data.members || [], vis = data.visitors || [];
    var oc = data.member_count != null ? data.member_count : off.length;
    var vc = data.visitor_count != null ? data.visitor_count : vis.length;
    count("mOff", oc); count("mVis", vc); count("mAll", oc + vc);

    var term = norm(q.value.trim());
    function match(p) { return !term || norm(p.name).indexOf(term) > -1 || norm(clean(p.name)).indexOf(term) > -1; }
    var fo = tab === "vis" ? [] : sorted(off.filter(match));
    var fv = tab === "off" ? [] : sorted(vis.filter(match));

    var og = document.getElementById("mOffGrid"), vg = document.getElementById("mVisGrid");
    og.innerHTML = ""; vg.innerHTML = "";
    fo.forEach(function (p, i) { og.appendChild(card(p, false, i)); });
    fv.forEach(function (p, i) { vg.appendChild(card(p, true, i)); });
    document.getElementById("mOffBox").hidden = !fo.length;
    document.getElementById("mVisBox").hidden = !fv.length;
    document.getElementById("mNone").hidden = fo.length + fv.length > 0;
  }

  function ago() {
    if (!lastOk) return;
    var s = Math.max(0, Math.round((Date.now() - lastOk) / 1000));
    var t = s < 10 ? "just now" : s < 60 ? s + " seconds ago" : Math.floor(s / 60) + (s < 120 ? " minute ago" : " minutes ago");
    liveTxt.textContent = live.classList.contains("off") ? "Reconnecting" : "Live, updated " + t;
  }

  var SOURCES = ["members.json", "https://apextransporte.github.io/apextransporte-/members.json"];
  function get(i) {
    return fetch(SOURCES[i] + "?v=" + Date.now(), { cache: "no-store" })
      .then(function (r) { if (!r.ok) throw new Error("missing"); return r.text(); })
      .catch(function (e) { if (i + 1 < SOURCES.length) return get(i + 1); throw e; });
  }
  function load() {
    get(0)
      .then(function (txt) {
        lastOk = Date.now();
        live.classList.remove("off");
        if (txt !== lastText) { lastText = txt; data = JSON.parse(txt); render(); }
        sec.hidden = false;
        ago();
      })
      .catch(function () {
        live.classList.add("off");
        if (!data) {
          document.getElementById("mNone").textContent = "The member list is not available yet. Please check back soon.";
          document.getElementById("mNone").hidden = false;
          document.getElementById("mOffBox").hidden = true;
          document.getElementById("mVisBox").hidden = true;
          sec.hidden = false;
        }
        ago();
      });
  }

  [].slice.call(document.querySelectorAll(".mtabs button")).forEach(function (b) {
    b.addEventListener("click", function () {
      tab = b.getAttribute("data-tab");
      [].slice.call(document.querySelectorAll(".mtabs button")).forEach(function (x) {
        x.setAttribute("aria-pressed", String(x === b));
      });
      render();
    });
  });
  q.addEventListener("input", render);

  load();
  setInterval(load, 60000);
  setInterval(ago, 5000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) load(); });
})();
}catch(e){console.error(e)}})();
;(function(){try{
(function () {
  var t = document.getElementById("jobsTable");
  if (!t) return;
  t.addEventListener("click", function (e) {
    if (window.innerWidth > 1000) return;
    var r = e.target.closest(".jr:not(.hd)");
    if (r) r.classList.toggle("open");
  });
})();
}catch(e){console.error(e)}})();
;(function(){try{
(function(){
  /* Keeps the driver table, the Driver directory and the staff cards in step with the Discord server. members.json is rebuilt every 30 minutes by the bot. */
  var STOP={apex:1,the:1};
  var ALIAS={corpratekeem:"keem",nightwingtir:"nightwingsa"};
  function nz(s){return String(s||"").normalize("NFKC").toLowerCase().replace(/[^\p{L}\p{N}]/gu,"");}
  function tk(s){return String(s||"").normalize("NFKC").toLowerCase().split(/[^\p{L}\p{N}]+/u).filter(Boolean);}
  function build(list){
    var out=[];
    list.forEach(function(m){
      var keys={},toks={};
      ["name","username","global_name","nick"].forEach(function(f){
        if(!m[f])return;
        var k=nz(m[f]);if(k)keys[k]=1;
        tk(m[f]).forEach(function(t){toks[t]=1;});
      });
      out.push({keys:keys,toks:toks});
    });
    return out;
  }
  function who(name,pool){
    var n=nz(name);if(!n)return -2;
    var al=ALIAS[n];if(al){name=al;n=nz(al);}
    var i,p;
    for(i=0;i<pool.length;i++){if(pool[i].keys[n])return i;}
    var dt=tk(name).filter(function(t){return !STOP[t];});
    if(dt.length){
      for(i=0;i<pool.length;i++){p=pool[i];
        if(dt.every(function(t){return p.toks[t];}))return i;}
    }
    return -1;
  }
  function inServer(name,pool){return who(name,pool)!==-1;}
  window.__apexInServer={build:build,inServer:inServer,who:who};
  if(typeof document==="undefined")return;
  var pool=null,busy=false;
  function clean(){
    if(!pool||busy)return;busy=true;
    var table=document.getElementById("jobsTable");
    if(table){
      var best={};
      [].slice.call(table.querySelectorAll(".jr:not(.hd)")).forEach(function(r){
        var b=r.querySelector("b");if(!b)return;
        var w=who(b.textContent,pool);
        if(w===-1){r.remove();return;}
        if(w<0)return;
        var filled=[].slice.call(r.querySelectorAll("span")).filter(function(s){return s.textContent.trim()!=="\u2014";}).length;
        var o=best[w];
        if(!o){best[w]={row:r,filled:filled};}
        else if(filled>o.filled){o.row.remove();best[w]={row:r,filled:filled};}
        else{r.remove();}
      });
      var c=document.getElementById("jobCount");
      if(c)c.textContent=table.querySelectorAll(".jr:not(.hd)").length+" drivers";
    }
    var dl=document.getElementById("dlist");
    if(dl){
      [].slice.call(dl.querySelectorAll(".dcard")).forEach(function(d){
        var b=d.querySelector("b");if(b&&!inServer(b.textContent,pool))d.remove();
      });
      [].slice.call(dl.querySelectorAll(".dgroup")).forEach(function(g){
        if(!g.querySelector(".dcard"))g.remove();
      });
      var q=document.getElementById("dq");
      if(q)q.dispatchEvent(new Event("input"));
    }
    var sc=document.querySelectorAll(".scard");
    if(sc.length){
      sc.forEach(function(s){
        var b=s.querySelector(".sname");if(b&&!inServer(b.textContent,pool))s.remove();
      });
      [].slice.call(document.querySelectorAll(".sgrid")).forEach(function(g){
        if(!g.querySelector(".scard")){var t=g.previousElementSibling;if(t&&t.classList.contains("stier"))t.remove();g.remove();}
      });
      var tot=document.querySelector("#crew .sub b");
      if(tot&&/Total staff/.test(tot.textContent))tot.textContent="Total staff on board: "+document.querySelectorAll(".scard").length;
    }
    busy=false;
  }
  fetch("members.json?v="+Date.now(),{cache:"no-store"})
    .then(function(r){return r.json();})
    .then(function(d){
      var list=(d.members||[]).concat(d.visitors||[]);
      if(!list.length)return;
      pool=build(list);
      clean();
      var table=document.getElementById("jobsTable");
      if(table)new MutationObserver(clean).observe(table,{childList:true});
    })
    .catch(function(){/* members.json missing: nothing is hidden */});
})();
}catch(e){console.error(e)}})();
;(function(){try{
(function(){
  /* Builds the Meet the crew cards from staff.json. The Discord bot rewrites staff.json from server roles, so joins, leaves and role changes show up on their own. */
  function nz(s){return String(s||"").normalize("NFKC").toLowerCase().replace(/[^\p{L}\p{N}]/gu,"");}
  function el(tag,cls,txt){var e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e;}
  function setRoles(card,roles){
    var box=card.querySelector(".sroles");
    if(!box){box=el("div","sroles");card.querySelector(".sbody").insertBefore(box,card.querySelector(".sdist"));}
    box.textContent="";
    roles.forEach(function(r,i){box.appendChild(el("span",i===0?"rl main":"rl",r));});
  }
  function makeCard(name){
    var c=el("div","scard");c.setAttribute("data-name",name);
    var av=el("span","sav",(Array.from(name.trim())[0]||"?").toUpperCase());av.setAttribute("aria-hidden","true");
    var body=el("div","sbody");body.appendChild(el("b","sname",name));
    var d=el("small","sdist");d.hidden=true;body.appendChild(d);
    c.appendChild(av);c.appendChild(body);return c;
  }
  function render(list){
    var staff=document.querySelector("#crew .staff");if(!staff)return;
    var have={};
    [].slice.call(staff.querySelectorAll(".scard")).forEach(function(c){have[nz(c.getAttribute("data-name"))]=c;});
    var lead=[],team=[];
    list.forEach(function(p){
      if(!p||!p.name||!p.roles||!p.roles.length)return;
      var c=have[nz(p.name)]||makeCard(p.name);
      setRoles(c,p.roles);
      (p.tier==="lead"?lead:team).push(c);
    });
    if(!lead.length&&!team.length)return;
    staff.textContent="";
    function tier(label,cards,isLead){
      if(!cards.length)return;
      staff.appendChild(el("p","stier",label));
      var g=el("div",isLead?"sgrid lead":"sgrid");
      cards.forEach(function(c){g.appendChild(c);});
      staff.appendChild(g);
    }
    tier("Leadership",lead,true);
    tier("Team",team,false);
    var tot=document.querySelector("#crew .sub b");
    if(tot&&/Total staff/.test(tot.textContent))tot.textContent="Total staff on board: "+(lead.length+team.length);
    if(window.__apexFillStaff)window.__apexFillStaff();
  }
  fetch("staff.json?v="+Date.now(),{cache:"no-store"})
    .then(function(r){return r.json();})
    .then(function(d){render(d.staff||[]);})
    .catch(function(){/* staff.json missing: the cards in the page stay as they are */});
})();
}catch(e){console.error(e)}})();
;(function(){try{
(function(){
  /* Gives every official Discord member a Job log row, even before any job data exists. Data fills in later from the bot. */
  function nameOf(m){return m.name||m.nick||m.global_name||m.username||"";}
  function newRow(name){
    var DASH="\u2014",L=["Total distance","Last job","Time","Fuel","Income","Level","Net worth"];
    var row=document.createElement("div");row.className="jr jr8";
    var b=document.createElement("b");b.setAttribute("data-l","Driver");b.textContent=name;row.appendChild(b);
    L.forEach(function(l){var s=document.createElement("span");s.setAttribute("data-l",l);
      if(l==="Income"||l==="Net worth")s.className="inc";s.textContent=DASH;row.appendChild(s);});
    return row;
  }
  function run(d){
    var api=window.__apexInServer,table=document.getElementById("jobsTable");
    var list=d.members||[];
    if(!api||!table||!list.length)return;
    var pool=api.build(list),seen={};
    [].slice.call(table.querySelectorAll(".jr:not(.hd) b")).forEach(function(b){
      var w=api.who(b.textContent,pool);if(w>=0)seen[w]=1;
    });
    var added=false;
    list.forEach(function(m,i){
      var n=nameOf(m);if(seen[i]||!n)return;
      table.appendChild(newRow(n));added=true;
    });
    if(added){
      var c=document.getElementById("jobCount");
      if(c)c.textContent=table.querySelectorAll(".jr:not(.hd)").length+" drivers";
    }
  }
  function go(){
    fetch("members.json?v="+Date.now(),{cache:"no-store"})
      .then(function(r){return r.json();})
      .then(run)
      .catch(function(){/* members.json missing: no rows are added */});
  }
  setTimeout(go,2500);
  setTimeout(go,7000);
})();
}catch(e){console.error(e)}})();