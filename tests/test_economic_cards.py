import pytest
from generator.htmlart import _carlig_tematic, _cifra_cheie, _treapta_callout


CASES_CIFRA = [
    ("500 lei/MWh", "Prețul gazelor naturale urcă la 500 de lei pe MWh", "500 lei/MWH"),
    ("0,35 lei/kWh", "Tariful reglementat este 0,35 lei/kWh pentru consum redus", "0,35 lei/KWH"),
    ("100 €/MWh", "Piața spot deschide la 100 €/MWh în Austria", "100 €/MWH"),
    ("Scade de la 7% la 5%", "Inflația scade de la 7% la 5% în 2026", "5%"),
    ("Creștere între 5% și 7%", "Băncile prevăd o creștere între 5% și 7% la credite", "5–7%"),
    ("Procent simplu", "Avans de 5% pentru locuințe noi", "5%"),
    ("Valoare negativă", "PIB-ul a scăzut cu -2,5% în trimestrul al treilea", "-2,5%"),
    ("Valoare pozitivă", "Salariul mediu a crescut cu +4% într-un an", "+4%"),
    ("La sută", "Dobânda rămâne la 7,2 la sută", "7,2%"),
    ("Miliarde euro", "Altex estimează vânzări de 2 miliarde de euro", "2 MLD €"),
    ("Miliarde lei", "Bugetul alocat este de 1,2 mld. lei", "1,2 MLD LEI"),
    ("Milioane euro", "Fondul atrage 60 milioane € pentru investiții", "60 MIL €"),
    ("Milioane euro prefix", "Compania a obținut €60 mil. din finanțare", "60 MIL €"),
    ("Multiplicator", "Traficul a crescut de 10 ori în weekend", "10×"),
    ("Ambiguitate (TVA 19% și deficit 7%)", "TVA 19% și deficit 7% în noul pachet fiscal", None),
    ("Ambiguitate (procent și sumă)", "A vândut 45% din bancă pentru 700 de milioane de euro", None),
    ("Top 10 exclus", "Top 10 companii cele mai profitabile din energie", None),
    ("Legea nr. 71/2024 exclusă", "Modificări fiscale aduse prin Legea nr. 71/2024", None),
    ("Ore și date excluse", "Conferința de la ora 11:30 din 28 octombrie", None),
    ("Fără cifre financiare", "Directorii marilor bănci au primit bonusuri record", None),
]

@pytest.mark.parametrize("desc,titlu,expected", CASES_CIFRA)
def test_cifra_cheie(desc, titlu, expected):
    res = _cifra_cheie(titlu)
    assert res == expected, f"FAIL [{desc}]: got={res!r}, expected={expected!r}"


CARLIG_CASES = [
    ("Noua Casă", {"title": "Tinerii pot cumpăra locuințe mai scumpe prin „Noua Casă” cu avans redus"}, "Noua Casă"),
    ("Black Friday", {"title": "eMAG anunță reduceri masive de Black Friday 2026"}, "Black Friday"),
    ("Gaze naturale", {"title": "Prețul gazelor naturale pe piața românească urcă rapid"}, "Gaze naturale"),
    ("Transelectrica", {"title": "Transelectrica recomandă menținerea a patru termocentrale"}, "Transelectrica"),
    ("BNR", {"title": "BNR anticipează menținerea dobânzii de referință"}, "BNR"),
    ("Guvernul", {"title": "Guvernul analizează menținerea taxei pe colete"}, "Guvernul"),
    ("Entity match", {"title": "Proiectul de infrastructură ANIF derulat rapid", "entities": ["ANIF"]}, "ANIF"),
    ("Fallback", {"category": "economic", "title": "Tranziția economiei către inovație"}, "Economie"),
    # Screenshot tests from user
    ("Tech Revolut", {"category": "tech", "title": "Platforma financiară Revolut a înregistrat noi probleme de conectare pentru utilizatori"}, "Revolut"),
    ("Tech Samsung", {"category": "tech", "title": "Samsung pregătește extinderea gamei de pliabile după succesul înregistrat de Galaxy Z Fold 8"}, "Samsung"),
    ("Tech Ubisoft", {"category": "tech", "title": "Ubisoft lansează ultimul update major pentru jocul Assassin's Creed Black Flag Resynced"}, "Ubisoft"),
    ("Tech Starlink", {"category": "tech", "title": "Utilizatorii rețelei Starlink din peste 100 de țări ar fi monitorizați"}, "Starlink"),
    ("Tech Apple", {"category": "tech", "title": "Apple actualizează suita Creator Studio cu funcții avansate bazate pe inteligență artificială"}, "Apple"),
    ("Tech RecompLauncher", {"category": "tech", "title": "Platforma RecompLauncher centralizează jocurile exclusive portate pe PC"}, "RecompLauncher"),
]

@pytest.mark.parametrize("desc,art,expected", CARLIG_CASES)
def test_carlig_tematic(desc, art, expected):
    res = _carlig_tematic(art)
    assert res == expected, f"FAIL [{desc}]: got={res!r}, expected={expected!r}"


TREPTE_CASES = [
    ("5%", 0),
    ("10×", 0),
    ("2 MLD €", 1),
    ("60 MIL €", 2), # '60 MIL €' has len 8 -> treapta 2
    ("500 lei/MWH", 2),
    ("187 MIL LEI", 2),
]

@pytest.mark.parametrize("val,expected_treapta", TREPTE_CASES)
def test_treapta_callout(val, expected_treapta):
    assert _treapta_callout(val) == expected_treapta
