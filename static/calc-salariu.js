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

  /* Deducerea personala de baza, art. 77 alin. (4) Cod Fiscal (Legea 227/2015), forma
   * consolidata de pe legislatie.just.ro (document 257144), citita 2026-08-07. Forma asta e in
   * vigoare de la 01-01-2023, prin pct. 40 al art. I din OG nr. 16/2022 (M. Of. 716/15.07.2022).
   * ATENTIE la portal: deasupra formei in vigoare afiseaza si forma VECHE a art. 77, cea cu
   * "venit lunar brut de pana la 1.950 lei ... 510 lei" -- aia e istoric, nu drept aplicabil.
   *
   * Tabelul din lege da un procent DIN SALARIUL MINIM care scade pe masura ce brutul creste,
   * pe transe de 50 de lei peste salariul minim -- NU o cota fixa. Randurile relevante,
   * verbatim din act (coloana "fara" persoane in intretinere):
   *   pana la salariul minim ............ 20,00%
   *   salariul minim + 1 ... + 50 lei ... 19,50%
   *   salariul minim + 51 ... + 100 lei . 19,00%
   *   ...
   *   salariul minim + 901 ... + 950 lei  10,50%
   * Pasul e constant, -0,5 puncte procentuale per transa de 50 de lei, deci tabelul se reduce
   * la formula de mai jos -- verificata rand cu rand pe cele 20 de randuri extrase din act,
   * zero nepotriviri, in loc sa fie copiat ca literal de 40 de randuri.
   *
   * alin. (3): deducerea se acorda doar pentru venit brut de pana la 2.000 de lei peste
   * salariul minim. Plafonul nu are nevoie de o ramura separata: la +2.000 lei formula da
   * exact 0%, iar peste el ar da negativ, de unde `Math.max(0, ...)`.
   *
   * Ce NU acopera calculatorul, deliberat (nota din templates/_calc_salariu.html o spune):
   * persoanele in intretinere (coloanele 1-4+ din tabel, +5 pp fiecare) si deducerea
   * personala suplimentara de la alin. (6)-(7). Ambele cer date pe care nu le cerem.
   */
  function deducerePersonala(brut, salariuMinim) {
    var peste = Math.max(0, brut - salariuMinim);
    var procent = Math.max(0, 20 - 0.5 * Math.ceil(peste / 50));
    return Math.round((salariuMinim * procent) / 100);
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
      // alin. (2): deducerea "se acorda in limita venitului impozabil lunar realizat". Conteaza
      // doar sub ~1.331 lei brut, unde deducerea din tabel ar depasi brutul ramas dupa
      // contributii -- fara plafon, un brut de 1.000 lei afisa "Deducere personala 865 lei".
      var deducere = Math.min(deducerePersonala(brut, salariuMinim),
                              Math.max(0, brut - cas - cass));
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
