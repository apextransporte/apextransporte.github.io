// Fills the Meet the crew section from staff.json. The hand typed cards stay as a fallback.
(async function () {
  var root = document.getElementById("staff-root");
  if (!root) return;

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text) n.textContent = text;
    return n;
  }

  function initial(name) {
    var m = String(name).normalize("NFKD").match(/[A-Za-z0-9]/);
    return m ? m[0].toUpperCase() : "?";
  }

  function card(p) {
    var c = el("div", "scard");
    c.setAttribute("data-name", p.name);
    var av = el("span", "sav", initial(p.name));
    av.setAttribute("aria-hidden", "true");
    var body = el("div", "sbody");
    body.appendChild(el("b", "sname", p.name));
    var roles = el("div", "sroles");
    roles.appendChild(el("span", "rl main", p.main));
    (p.tags || []).forEach(function (t) { roles.appendChild(el("span", "rl", t)); });
    body.appendChild(roles);
    var dist = el("small", "sdist");
    dist.hidden = true;
    body.appendChild(dist);
    c.appendChild(av);
    c.appendChild(body);
    return c;
  }

  function tier(label, people, lead) {
    var frag = document.createDocumentFragment();
    frag.appendChild(el("p", "stier", label));
    var grid = el("div", lead ? "sgrid lead" : "sgrid");
    people.forEach(function (p) { grid.appendChild(card(p)); });
    frag.appendChild(grid);
    return frag;
  }

  try {
    var res = await fetch("staff.json?t=" + Date.now(), { cache: "no-store" });
    if (!res.ok) return;
    var data = await res.json();
    var lead = data.leadership || [];
    var team = data.team || [];
    if (!lead.length && !team.length) return;
    root.textContent = "";
    if (lead.length) root.appendChild(tier("Leadership", lead, true));
    if (team.length) root.appendChild(tier("Team", team, false));
    var total = document.getElementById("staff-total");
    if (total) total.textContent = "Total staff on board: " + (data.total || lead.length + team.length);
  } catch (e) {
    /* keep the hand typed cards */
  }
})();
