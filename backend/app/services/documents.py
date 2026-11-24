from pathlib import Path
import pymupdf
from docx import Document as DocxDocument
from fastapi import HTTPException, UploadFile

ALLOWED = {".pdf", ".txt", ".docx"}


async def extract_upload(upload: UploadFile, max_bytes: int) -> tuple[str, int, bytes]:
    name = Path(upload.filename or "").name
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(415, "Only PDF, TXT, and DOCX files are supported")
    raw = await upload.read(max_bytes + 1)
    if not raw:
        raise HTTPException(400, "The uploaded file is empty")
    if len(raw) > max_bytes:
        raise HTTPException(413, f"File exceeds the {max_bytes // (1024 * 1024)} MB limit")
    try:
        if ext == ".pdf":
            pdf = pymupdf.open(stream=raw, filetype="pdf")
            pages = [p.get_text("text") for p in pdf]
            text = "\n\n".join(f"[Page {i + 1}]\n{value}" for i, value in enumerate(pages))
            count = len(pages)
        elif ext == ".docx":
            import io
            doc = DocxDocument(io.BytesIO(raw))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            count = 1
        else:
            text = raw.decode("utf-8-sig")
            count = 1
    except Exception as exc:
        raise HTTPException(400, "Could not read this document") from exc
    if not text.strip():
        raise HTTPException(422, "No extractable text was found in this document")
    return text, count, raw


def split_chunks(text: str, size: int = 1400, overlap: int = 220) -> list[str]:
    paragraphs = text.splitlines()
    result: list[str] = []
    current = ""
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        while len(paragraph) > size:
            if current:
                result.append(current)
                current = current[-overlap:]
            result.append(paragraph[:size])
            paragraph = paragraph[size - overlap:]
        if len(current) + len(paragraph) + 1 > size and current:
            result.append(current)
            current = current[-overlap:] + "\n" + paragraph
        else:
            current = f"{current}\n{paragraph}".strip()
    if current.strip():
        result.append(current.strip())
    return result
