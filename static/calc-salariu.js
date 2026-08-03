/* Calculator salariu net.
 *
 * De ce e fisier extern si nu <script> inline: CSP-ul sitului e `script-src 'self'` FARA
 * `'unsafe-inline'` (vezi render._write_headers). Varianta inline nu a rulat niciodata pe
 * live -- masurat 2026-08-02 pe https://izz.ro/ghiduri/salariul-minim/: `calcSalariu` era
 * `undefined`, `#calc-results` era gol, si nicio cifra introdusa nu producea nimic.
 * Din acelasi motiv nu exista `onclick=`/`oninput=` in markup: si alea sunt cod inline.
 *
 * Salariul minim vine din `data-salariu-minim` pe container, nu dintr-un literal generat
 * in JS, ca sa nu mai fie nevoie de interpolare de sursa executabila.
 */
(function () {
  "use strict";

  function lei(n) {
    // Separator de mie romanesc; Math.round inainte, ca sa nu apara zecimale de rotunjire.
    return Math.round(n).toLocaleString("ro-RO") + " lei";
  }

  function scazut(n) {
    // Minusul are sens doar cand chiar se scade ceva: cu campul golit, "-0 lei" pe cinci
    // randuri arata a defect.
    return (n > 0 ? "-" : "") + lei(n);
  }

  function rand(eticheta, valoare, clasa) {
    var d = document.createElement("div");
    d.className = "calc-item" + (clasa ? " " + clasa : "");
    var e = document.createElement("span");
    e.className = "calc-label";
    e.textContent = eticheta;
    var v = document.createElement("span");
    v.className = "calc-val";
    v.textContent = valoare;
    d.appendChild(e);
    d.appendChild(v);
    return d;
  }

  function init(box) {
    var input = box.querySelector(".calc-brut");
    var out = box.querySelector(".calc-results");
    if (!input || !out) return;

    var salariuMinim = parseFloat(box.getAttribute("data-salariu-minim")) || 0;

    function calc() {
      // `min="0"` tine doar de validarea formularului, nu de valoarea citita aici: un brut
      // negativ tastat manual dadea "- -1.250 lei" pe fiecare rand.
      var brut = Math.max(0, parseFloat(input.value) || 0);
      var cas = Math.round(brut * 0.25);
      var cass = Math.round(brut * 0.1);
      var deducere = Math.round(salariuMinim * 0.2);
      var baza = Math.max(0, brut - cas - cass - deducere);
      var impozit = Math.round(baza * 0.1);
      var net = brut - cas - cass - impozit;

      out.textContent = "";
      out.appendChild(rand("CAS (25%)", scazut(cas)));
      out.appendChild(rand("CASS (10%)", scazut(cass)));
      out.appendChild(rand("Deducere personală", lei(deducere)));
      out.appendChild(rand("Bază impozabilă", lei(baza)));
      out.appendChild(rand("Impozit (10%)", scazut(impozit)));
      out.appendChild(rand("SALARIU NET", lei(net), "calc-total"));
    }

    input.addEventListener("input", calc);
    box.addEventListener("click", function (ev) {
      var b = ev.target.closest(".btn-preset");
      if (!b || !box.contains(b)) return;
      input.value = b.getAttribute("data-brut");
      calc();
    });
    calc();
  }

  function start() {
    var boxes = document.querySelectorAll(".calculator[data-salariu-minim]");
    for (var i = 0; i < boxes.length; i++) init(boxes[i]);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
