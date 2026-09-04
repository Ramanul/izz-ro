/* Calculator salariu net.
 * Codul este extern deoarece CSP-ul sitului folosește script-src 'self'.
 */
(function () {
  "use strict";

  function lei(n) {
    return Math.round(n).toLocaleString("ro-RO") + " lei";
  }

  function scazut(n) {
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
    var facilitate = box.querySelector(".calc-facilitate-200");
    if (!input || !out) return;

    var salariuMinim = parseFloat(box.getAttribute("data-salariu-minim")) || 0;

    function calc() {
      var brut = Math.max(0, parseFloat(input.value) || 0);
      var aplicaFacilitate = Boolean(facilitate && facilitate.checked);

      // OUG 89/2025, art. III: facilitatea de 200 lei este condiționată cumulativ.
      // Interfața solicită utilizatorului confirmarea situației sale; aici verificăm
      // mecanic salariul minim și plafonul brut disponibil calculatorului.
      var eligibil200 = aplicaFacilitate && brut === salariuMinim && brut <= 4600 && salariuMinim === 4325;
      var sumaNetaxabila = eligibil200 ? 200 : 0;
      var bazaContributii = Math.max(0, brut - sumaNetaxabila);

      var cas = Math.round(bazaContributii * 0.25);
      var cass = Math.round(bazaContributii * 0.1);

      // Art. 77 Cod fiscal: deducerea de bază este degresivă.
      var trepte = Math.max(0, Math.ceil((brut - salariuMinim) / 50));
      var rataDeducere = Math.max(0, 20 - trepte * 0.5);
      var deducere = brut > salariuMinim + 2000 ? 0 : Math.round(salariuMinim * rataDeducere / 100);
      deducere = Math.min(deducere, Math.max(0, bazaContributii - cas - cass));

      var baza = Math.max(0, bazaContributii - cas - cass - deducere);
      var impozit = Math.round(baza * 0.1);
      var net = brut - cas - cass - impozit;

      out.textContent = "";
      out.appendChild(rand("CAS (25%)", scazut(cas)));
      out.appendChild(rand("CASS (10%)", scazut(cass)));
      out.appendChild(rand("Deducere personală", lei(deducere)));
      out.appendChild(rand("Bază impozabilă", lei(baza)));
      out.appendChild(rand("Impozit (10%)", scazut(impozit)));
      if (eligibil200) {
        out.appendChild(rand("Sumă netaxabilă", lei(sumaNetaxabila), "calc-exempt"));
      }
      out.appendChild(rand("SALARIU NET", lei(net), "calc-total"));

      if (facilitate) {
        facilitate.disabled = brut !== salariuMinim || salariuMinim !== 4325;
        if (facilitate.disabled) facilitate.checked = false;
      }
    }

    input.addEventListener("input", calc);
    if (facilitate) facilitate.addEventListener("change", calc);
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
