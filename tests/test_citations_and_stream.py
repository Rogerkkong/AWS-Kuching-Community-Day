from app.services.generation.citations import parse_actions, validate_answer
from app.services.generation.stream import AnswerStreamParser


def run(pieces):
    p = AnswerStreamParser()
    out = []
    for piece in pieces:
        out += p.feed(piece)
    out += p.finish()
    return p, out


def test_validator_removes_invalid_and_normalises_groups():
    clean, used, removed = validate_answer("Had ialah 15 hari [S1, S3]. Lagi [S9]. Juga [ S2 ].", {1, 2, 3})
    assert clean == "Had ialah 15 hari [S1][S3]. Lagi. Juga [S2]."
    assert used == [1, 3, 2] and removed == [9]


def test_validator_nothing_valid_left():
    clean, used, _ = validate_answer("Jawapan tanpa sumber [S7].", {1, 2})
    assert used == [] and "[S" not in clean


def test_actions_need_valid_trailing_citation():
    text = """- Semak syarat kelayakan [S1]
- Dapatkan kelulusan Ketua Jabatan [S2].
- Hantar dalam 30 hari [S9]
- Baris tanpa rujukan
- [S1] rujukan di depan sahaja tidak sah
not a bullet [S1]"""
    acts = parse_actions(text, {1, 2})
    assert [a["text"] for a in acts] == ["Semak syarat kelayakan", "Dapatkan kelulusan Ketua Jabatan"]
    assert acts[1]["citations"] == [2]


def test_actions_box_hidden_when_none_valid():
    assert parse_actions("- Sesuatu [S5]\n- Lain", {1}) == []


def test_stream_parser_reads_first_line_and_splits_actions_across_tokens():
    p, out = run(["ANSWER", "ABLE: YES\nHad ", "ialah 15 hari [S1].\nACT", "IONS:\n- Semak [S1]\n- Lulus [S1]"])
    assert p.answerable is True
    answer = "".join(t for s, t in out if s == "answer")
    assert answer.strip() == "Had ialah 15 hari [S1]."
    assert "- Semak [S1]" in "".join(t for s, t in out if s == "actions")


def test_stream_parser_no_emits_nothing():
    p, out = run(["ANSWERABLE: NO"])
    assert p.answerable is False and out == []


def test_stream_parser_tolerates_markdown_marker():
    p, _ = run(["ANSWERABLE: YES\nJawapan [S1].\n**ACTIONS:**\n- Buat [S1]"])
    assert p.answer_text.strip() == "Jawapan [S1]."
    assert parse_actions(p.actions_text, {1})[0]["text"] == "Buat"
