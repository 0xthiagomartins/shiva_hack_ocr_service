"""Tesseract nas 4 variações; geração do arquivo .toon."""

import os
from pathlib import Path

import pytesseract
from PIL import Image


TOON_SEPARATOR = "--- variation {i} ---"
LANG = "por"  # português; ajuste se precisar eng


def run_ocr_on_image(img: Image.Image) -> str:
    """Executa Tesseract em uma imagem e retorna o texto bruto."""
    return pytesseract.image_to_string(img, lang=LANG).strip()


def run_ocr_on_variations(images: list[Image.Image]) -> list[str]:
    """Executa OCR em cada uma das 4 variações. Retorna lista de 4 strings."""
    return [run_ocr_on_image(img) for img in images]


def build_toon_content(texts: list[str]) -> str:
    """Monta o conteúdo do arquivo .toon com as 4 variações."""
    parts = []
    for i, text in enumerate(texts, start=1):
        parts.append(TOON_SEPARATOR.format(i=i))
        parts.append(text)
        parts.append("")
    return "\n".join(parts)


def write_toon_file(content: str, process_id: str, toon_dir: str) -> str:
    """
    Grava o conteúdo no arquivo {process_id}.toon em toon_dir.
    Cria o diretório se não existir. Retorna o path absoluto do arquivo.
    """
    path = Path(toon_dir)
    path.mkdir(parents=True, exist_ok=True)
    filepath = path / f"{process_id}.toon"
    filepath.write_text(content, encoding="utf-8")
    return str(filepath)


def run_ocr_and_save_toon(
    images: list[Image.Image],
    process_id: str,
    toon_dir: str,
) -> str:
    """
    Executa OCR nas 4 variações, monta o .toon e salva.
    Retorna o conteúdo do .toon (string) para envio ao LLM.
    """
    texts = run_ocr_on_variations(images)
    content = build_toon_content(texts)
    write_toon_file(content, process_id, toon_dir)
    return content
