"""8 variações de pré-processamento em escala de cinza (brilho, contraste, nitidez, binarização)."""

import io
from PIL import Image, ImageEnhance, ImageOps


def decode_b64_to_image_grayscale(image_b64: str) -> Image.Image:
    """Decodifica base64 e retorna imagem em escala de cinza (modo L)."""
    import base64
    raw = base64.b64decode(image_b64)
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    return ImageOps.grayscale(img)


def variation_base(gray: Image.Image) -> Image.Image:
    """Variação 1: grayscale sem alteração."""
    return gray.copy()


def variation_brighter(gray: Image.Image) -> Image.Image:
    """Variação 2: mais luminoso."""
    return ImageEnhance.Brightness(gray).enhance(1.4)


def variation_darker(gray: Image.Image) -> Image.Image:
    """Variação 3: menos luminoso."""
    return ImageEnhance.Brightness(gray).enhance(0.6)


def variation_contrast_high(gray: Image.Image) -> Image.Image:
    """Variação 4: mais contraste."""
    return ImageEnhance.Contrast(gray).enhance(1.5)


def variation_contrast_low(gray: Image.Image) -> Image.Image:
    """Variação 5: menos contraste."""
    return ImageEnhance.Contrast(gray).enhance(0.7)


def variation_threshold(gray: Image.Image) -> Image.Image:
    """Variação 6: binarização (preto e branco, threshold 128)."""
    return gray.point(lambda x: 255 if x > 128 else 0, mode="1").convert("L")


def variation_sharp(gray: Image.Image) -> Image.Image:
    """Variação 7: mais nitidez."""
    return ImageEnhance.Sharpness(gray).enhance(2.0)


def variation_bright_contrast(gray: Image.Image) -> Image.Image:
    """Variação 8: brilho e contraste levemente aumentados."""
    out = ImageEnhance.Brightness(gray).enhance(1.2)
    return ImageEnhance.Contrast(out).enhance(1.3)


def get_eight_variations(image_b64: str) -> list[Image.Image]:
    """
    Gera 8 variações em escala de cinza: base, mais/menos brilho, mais/menos contraste,
    binarização, nitidez, brilho+contraste.
    """
    img = decode_b64_to_image_grayscale(image_b64)
    return [
        variation_base(img),
        variation_brighter(img),
        variation_darker(img),
        variation_contrast_high(img),
        variation_contrast_low(img),
        variation_threshold(img),
        variation_sharp(img),
        variation_bright_contrast(img),
    ]
