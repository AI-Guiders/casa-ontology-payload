from casa.prisms.memory.meta_concept_aliases import canonical_lex_concept_id, lex_concept_id_variants


def test_legacy_register_maps_to_letter_case_canon() -> None:
    assert canonical_lex_concept_id("lang.word.capital_letter") == "lang.meta.letterCase.upper"
    assert canonical_lex_concept_id("lang.meta.letterCase.upper") == "lang.meta.letterCase.upper"


def test_size_legacy_maps_to_meta_size() -> None:
    assert canonical_lex_concept_id("lang.word.bolshaya") == "lang.meta.size.large"


def test_compare_comparative_maps_to_meta_compare() -> None:
    assert canonical_lex_concept_id("lang.meta.size.comparative.greater") == "lang.meta.compare.greater"
    assert canonical_lex_concept_id("lang.meta.compare.less") == "lang.meta.compare.less"


def test_variants_single_canon() -> None:
    assert lex_concept_id_variants("lang.word.capital_letter") == ("lang.meta.letterCase.upper",)
