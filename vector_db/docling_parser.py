import io
import os

from config import settings

SUPPORTED_DOC_EXTS = {
    ".pdf", ".docx", ".pptx", ".md", ".txt", ".html", ".htm",
    ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp",
}
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}

_converter = None


def is_document(path):
    return os.path.splitext(path)[1].lower() in SUPPORTED_DOC_EXTS


def _build_converter():
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        EasyOcrOptions,
        PdfPipelineOptions,
        RapidOcrOptions,
        TesseractOcrOptions,
    )
    from docling.document_converter import DocumentConverter, PdfFormatOption

    engines = {
        "rapidocr": RapidOcrOptions,
        "easyocr": EasyOcrOptions,
        "tesseract": TesseractOcrOptions,
    }
    ocr_cls = engines.get(settings.DOCLING_OCR_ENGINE, RapidOcrOptions)

    # future: RapidOCR is free and local but weak on handwriting; swap a vision-LLM OCR for that.
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = settings.DOCLING_DO_OCR
    ocr_options = ocr_cls()
    ocr_options.force_full_page_ocr = False
    try:
        ocr_options.bitmap_area_threshold = settings.DOCLING_BITMAP_AREA_THRESHOLD
    except Exception:
        pass
    pipeline_options.ocr_options = ocr_options

    allowed = [
        InputFormat.PDF, InputFormat.DOCX, InputFormat.PPTX,
        InputFormat.MD, InputFormat.HTML, InputFormat.IMAGE, InputFormat.ASCIIDOC,
    ]
    return DocumentConverter(
        allowed_formats=allowed,
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)},
    )


def _get_converter():
    global _converter
    if _converter is None:
        _converter = _build_converter()
    return _converter


def parse(path):
    if not os.path.isfile(path):
        raise ValueError(f"file not found: {path}")
    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_DOC_EXTS:
        raise ValueError(
            f"unsupported file type: {ext}. supported: {' '.join(sorted(SUPPORTED_DOC_EXTS))}"
        )

    source = _to_source(path, ext)
    try:
        result = _get_converter().convert(source)
    except Exception as exc:
        raise ValueError(f"could not parse {os.path.basename(path)}: {exc}") from exc
    return result.document


def _to_source(path, ext):
    if ext == ".txt":
        from docling.datamodel.base_models import DocumentStream

        with open(path, "rb") as fh:
            data = fh.read()
        name = os.path.splitext(os.path.basename(path))[0] + ".md"
        return DocumentStream(name=name, stream=io.BytesIO(data))
    return path


def is_scanned(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in _IMAGE_EXTS:
        return True
    if ext == ".pdf":
        return not _pdf_has_text_layer(path)
    return False


def _pdf_has_text_layer(path, min_chars_per_page=20):
    import fitz

    doc = fitz.open(path)
    pages = doc.page_count
    total = sum(len(page.get_text().strip()) for page in doc)
    doc.close()
    if pages == 0:
        return False
    return (total / pages) >= min_chars_per_page
