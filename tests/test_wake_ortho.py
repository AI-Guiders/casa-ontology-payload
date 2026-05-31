"""Wake ortho — display vs lexeme (МАМА! / не кричи / Мама)."""

from __future__ import annotations

from casa.prisms.hippo.wake_util import (
    classify_surface_target,
    norm_lexeme,
    surface_attempt_from_wake,
    surface_matches_target,
)


def _wake_mama_shout() -> dict:
    return {
        "surface_text": "Surface L2: МАМА.",
        "active": [{"concept_id": "lang.word.мама", "votes": 5}],
    }


def test_norm_lexeme_ignores_case_and_punct() -> None:
    assert norm_lexeme("МАМА!") == norm_lexeme("Мама") == norm_lexeme("мама")


def test_shout_lexeme_match_display_mismatch() -> None:
    wake = _wake_mama_shout()
    m = classify_surface_target(wake, "Мама", lattice_id="L2_word")
    assert m["lexeme_match"] is True
    assert m["display_match"] is False
    assert m["ortho_mismatch"] is True
    assert surface_matches_target(wake, "Мама", lattice_id="L2_word") is False


def test_sentence_case_full_match() -> None:
    wake = {
        "surface_text": "Surface L2: Мама.",
        "active": [{"concept_id": "lang.word.мама", "votes": 5}],
    }
    m = classify_surface_target(wake, "Мама", lattice_id="L2_word")
    assert m["display_match"] is True
    assert m["ortho_mismatch"] is False


def test_surface_attempt_prefers_display_case() -> None:
    wake = _wake_mama_shout()
    assert surface_attempt_from_wake(wake, lattice_id="L2_word") == "МАМА"


def test_wake_turn_ne_krichi_episode() -> None:
    from casa.prisms.memory.memory_prisms import ensure_prisms, prism_hippo
    from casa.prisms.hippo.wake import wake_turn

    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    bundle = {"claims": [{"concept_id": "lang.word.мама"}], "graph": {"edges": []}}

    # Monkey-patch surface: field decodes lexeme, babble shows ALL CAPS
    from casa.prisms.hippo import wake as wake_mod

    def fake_surface(_state, **kwargs):
        return _wake_mama_shout()

    original = wake_mod.surface_from_sss
    wake_mod.surface_from_sss = fake_surface
    try:
        report = wake_turn(
            state,
            cue="не кричи",
            lattice_id="L2_word",
            target="Мама",
            bundle=bundle,
            auto=True,
        )
    finally:
        wake_mod.surface_from_sss = original

    assert report["ortho_mismatch"] is True
    assert report["matched"] is False
    assert report["surface_attempt"] == "МАМА"
    ep = report["episode"]
    assert ep is not None
    assert ep.get("correction_kind") == "ortho_surface"
    assert ep.get("correct") == "Мама"
    assert len(prism_hippo(state).get("episodes") or []) == 1
