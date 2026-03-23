from whiscode.stats import Stats


def test_empty_summary():
    s = Stats()
    assert s.summary() == "0 transcriptions, 0 words, 0.0 min of audio"


def test_single_record():
    s = Stats()
    s.record(5, 30.0)
    assert s.summary() == "1 transcription, 5 words, 0.5 min of audio"


def test_multiple_records():
    s = Stats()
    s.record(10, 60.0)
    s.record(5, 30.0)
    assert s.summary() == "2 transcriptions, 15 words, 1.5 min of audio"


def test_singular_word():
    s = Stats()
    s.record(1, 6.0)
    assert s.summary() == "1 transcription, 1 word, 0.1 min of audio"
