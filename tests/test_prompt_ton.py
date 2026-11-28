"""Promptul de titlu cere sobrietate la violență; PROMPT_VERSION rămâne neschimbat."""
from generator import process


def test_prompturile_de_titlu_interzic_violenta_ca_metafora():
    for prompt in (process.USER_B, process.USER_BATCH):
        assert "fara violenta ca metafora" in prompt
        assert "spulberat" in prompt


def test_prompt_version_nu_se_schimba_ca_sa_nu_reprocesam_corpusul():
    assert process.config.PROMPT_VERSION == "v2-esenta"
