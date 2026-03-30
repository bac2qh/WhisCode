from whiscode.postprocess import strip_repetitions, postprocess, postprocess_for_refine


class TestStripRepetitions:
    def test_repeated_single_word(self):
        text = "thinking thinking thinking thinking thinking thinking"
        assert strip_repetitions(text) == "thinking"

    def test_repeated_phrase(self):
        text = "I'm thinking, I'm thinking, I'm thinking, I'm thinking, I'm thinking,"
        assert strip_repetitions(text) == "I'm thinking,"

    def test_natural_speech_preserved(self):
        # Only 3 repeats — below threshold of 5
        text = "yeah, yeah, yeah, of course"
        assert strip_repetitions(text) == "yeah, yeah, yeah, of course"

    def test_four_repeats_preserved(self):
        text = "yes yes yes yes of course"
        assert strip_repetitions(text) == "yes yes yes yes of course"

    def test_exactly_five_repeats_collapsed(self):
        text = "yes yes yes yes yes done"
        assert strip_repetitions(text) == "yes done"

    def test_normal_text_unchanged(self):
        text = "def my_function return value"
        assert strip_repetitions(text) == text

    def test_empty_string(self):
        assert strip_repetitions("") == ""

    def test_case_insensitive(self):
        text = "Yeah Yeah yeah Yeah Yeah Yeah"
        assert strip_repetitions(text) == "Yeah"

    def test_long_hallucination(self):
        phrase = "I'm thinking, "
        text = (phrase * 20).strip()
        result = strip_repetitions(text)
        assert result == "I'm thinking,"

    def test_repetition_at_end(self):
        text = "hello yes yes yes yes yes"
        assert strip_repetitions(text) == "hello yes"

    def test_repetition_in_middle(self):
        text = "hello yes yes yes yes yes goodbye"
        assert strip_repetitions(text) == "hello yes goodbye"

    def test_two_separate_repetitions(self):
        text = "a a a a a b b b b b"
        assert strip_repetitions(text) == "a b"

    def test_custom_threshold_triggers(self):
        text = "ok ok ok"
        assert strip_repetitions(text, min_repeats=3) == "ok"

    def test_custom_threshold_preserves(self):
        text = "ok ok ok"
        assert strip_repetitions(text, min_repeats=4) == "ok ok ok"

    def test_postprocess_applies_strip(self):
        text = "thinking thinking thinking thinking thinking thinking"
        assert postprocess(text) == "thinking"


class TestPostprocessForRefine:
    def test_strips_repetitions(self):
        text = "thinking thinking thinking thinking thinking thinking"
        assert postprocess_for_refine(text) == "thinking"

    def test_applies_replacements(self):
        result = postprocess_for_refine("whiscode is great", replacements={"whiscode": "WhisCode"})
        assert result == "WhisCode is great"

    def test_does_not_apply_symbols(self):
        # "slash" should remain as-is, not converted to "/"
        result = postprocess_for_refine("use slash to separate")
        assert result == "use slash to separate"

    def test_does_not_apply_casing(self):
        # "camel case foo bar" should remain as-is, not converted
        result = postprocess_for_refine("camel case foo bar")
        assert result == "camel case foo bar"

    def test_empty_string(self):
        assert postprocess_for_refine("") == ""

    def test_normal_prose_unchanged(self):
        text = "Hey, just wanted to follow up on our earlier discussion."
        assert postprocess_for_refine(text) == text
