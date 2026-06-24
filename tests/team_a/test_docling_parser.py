import pytest

from vector_db import docling_parser

MD = (
    "# Photosynthesis\n\n"
    "## Light-Dependent Reactions\n\n"
    "The light-dependent reactions occur in the thylakoid membrane and produce ATP and NADPH "
    "used later in the Calvin cycle.\n"
)


def test_is_document_allowlist():
    for ext in [".pdf", ".docx", ".pptx", ".md", ".txt", ".html", ".htm", ".png", ".jpg", ".jpeg"]:
        assert docling_parser.is_document("file" + ext), ext
    assert not docling_parser.is_document("lecture.mp3")
    assert not docling_parser.is_document("lecture.mp4")
    assert not docling_parser.is_document("data.csv")


def test_unsupported_extension_raises(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("a,b,c")
    with pytest.raises(ValueError):
        docling_parser.parse(str(f))


def test_missing_file_raises():
    with pytest.raises(ValueError):
        docling_parser.parse("nope.md")


def test_parse_markdown_returns_document(tmp_path):
    f = tmp_path / "notes.md"
    f.write_text(MD, encoding="utf-8")

    doc = docling_parser.parse(str(f))

    text = doc.export_to_markdown()
    assert "Photosynthesis" in text
    assert "thylakoid" in text


def test_is_scanned_false_for_markdown(tmp_path):
    f = tmp_path / "notes.md"
    f.write_text(MD, encoding="utf-8")
    assert docling_parser.is_scanned(str(f)) is False


def test_is_scanned_true_for_image():
    assert docling_parser.is_scanned("photo.png") is True
    assert docling_parser.is_scanned("scan.jpg") is True


def test_parse_born_digital_pdf(tmp_path):
    fitz = pytest.importorskip("fitz")
    pdf = tmp_path / "n.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Photosynthesis converts light to chemical energy")
    doc.save(str(pdf))
    doc.close()
    try:
        dl = docling_parser.parse(str(pdf))
    except Exception as exc:  # models not cached offline
        pytest.skip(f"Docling PDF models unavailable: {exc}")
    assert "Photosynthesis" in dl.export_to_markdown()


def test_is_scanned_false_for_text_pdf(tmp_path):
    fitz = pytest.importorskip("fitz")
    pdf = tmp_path / "text.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "This page carries a real text layer with plenty of readable words.")
    doc.save(str(pdf))
    doc.close()
    assert docling_parser.is_scanned(str(pdf)) is False


def test_is_scanned_true_for_imageless_blank_pdf(tmp_path):
    fitz = pytest.importorskip("fitz")
    pdf = tmp_path / "blank.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(pdf))
    doc.close()
    assert docling_parser.is_scanned(str(pdf)) is True
