/* Cautare client-side pe /cauta/: index JSON mic, generat la render.
   Fara dependinte, fara server, fara trackere. Diacritice-insensibil. */
(function () {
  "use strict";
  var q = document.getElementById("q");
  var category = document.getElementById("search-category");
  var out = document.getElementById("search-results");
  var status = document.getElementById("search-status");
  if (!q || !out) return;

  var form = document.getElementById("search-form");
  if (form) form.addEventListener("submit", function (e) { e.preventDefault(); });

  var index = null, loading = false;
  var MAP = { "ă": "a", "â": "a", "î": "i", "ș": "s", "ş": "s", "ț": "t", "ţ": "t" };
  function norm(s) {
    return s.toLowerCase().replace(/[ăâîșşțţ]/g, function (c) { return MAP[c] || c; });
  }

  function load(cb) {
    if (index) return cb();
    if (loading) return;
    loading = true;
    status.textContent = "Se încarcă indexul…";
    fetch("/search-index.json")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        index = d.map(function (a) { return { n: norm(a.t), a: a }; });
        status.textContent = "";
        cb();
      })
      .catch(function () { status.textContent = "Indexul nu a putut fi încărcat."; });
  }

  function run() {
    var words = norm(q.value.trim()).split(/\s+/).filter(function (w) { return w.length > 1; });
    var selectedCategory = category ? category.value : "";
    out.textContent = "";
    if (!words.length) {
      status.textContent = selectedCategory ? "Introdu un termen pentru categoria selectată." : "";
      return;
    }
    var hits = [];
    for (var i = 0; i < index.length && hits.length < 50; i++) {
      var n = index[i].n, ok = !selectedCategory || index[i].a.c === selectedCategory;
      for (var j = 0; ok && j < words.length; j++) if (n.indexOf(words[j]) === -1) { ok = false; break; }
      if (ok) hits.push(index[i].a);
    }
    var suffix = selectedCategory ? " în „" + selectedCategory + "”" : "";
    status.textContent = hits.length ? hits.length + " rezultate" + suffix : "Niciun rezultat" + suffix + ".";
    hits.forEach(function (a) {
      var li = document.createElement("li");
      var link = document.createElement("a");
      link.href = a.u;
      link.textContent = a.t;
      var meta = document.createElement("span");
      meta.className = "search-meta";
      meta.textContent = " — " + a.c + ", " + a.d;
      li.appendChild(link);
      li.appendChild(meta);
      out.appendChild(li);
    });
  }

  q.addEventListener("input", function () { load(run); });
  if (category) category.addEventListener("change", function () { load(run); });
})();
