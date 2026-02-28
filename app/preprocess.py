"""4 variações de pré-processamento da imagem para OCR em cupons fiscais."""

import io
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def decode_b64_to_image(image_b64: str) -> Image.Image:
    """Decodifica string base64 em PIL Image."""
    import base64
    raw = base64.b64decode(image_b64)
    return Image.open(io.BytesIO(raw)).convert("RGB")


def variation_original(img: Image.Image) -> Image.Image:
    """Variação 1: imagem original (RGB)."""
    return img.copy()


def variation_grayscale(img: Image.Image) -> Image.Image:
    """Variação 2: escala de cinza."""
    return ImageOps.grayscale(img).convert("RGB")


def variation_threshold(img: Image.Image) -> Image.Image:
    """Variação 3: binarização (threshold) para texto preto em fundo branco."""
    gray = ImageOps.grayscale(img)
    return ImageOps.invert(gray).point(lambda x: 255 if x > 128 else 0, mode="1").convert("RGB")


def variation_enhanced(img: Image.Image) -> Image.Image:
    """Variação 4: contraste e nitidez aumentados."""
    enhanced = ImageEnhance.Contrast(img).enhance(1.5)
    enhanced = ImageEnhance.Sharpness(enhanced).enhance(2.0)
    return enhanced


def get_four_variations(image_b64: str) -> list[Image.Image]:
    """
    Gera as 4 variações de pré-processamento a partir da imagem em base64.
    Retorna lista de 4 PIL Images na ordem: original, grayscale, threshold, enhanced.
    """
    img = decode_b64_to_image(image_b64)
    return [
        variation_original(img),
        variation_grayscale(img),
        variation_threshold(img),
        variation_enhanced(img),
    ]
