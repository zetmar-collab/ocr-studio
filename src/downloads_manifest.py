"""Wygenerowane przez scripts/update_data_manifest.py - nie edytuj recznie."""

from __future__ import annotations

TESSDATA_BASE_URL = "https://github.com/tesseract-ocr/tessdata_best/raw/e12c65a915945e4c28e237a9b52bc4a8f39a0cec"
DICT_BASE_URL = "https://raw.githubusercontent.com/wooorm/dictionaries/8cfea406b505e4d7df52d5a19bce525df98c54ab/dictionaries"

# kod jezyka OCR -> (sha256, rozmiar w bajtach)
TESSDATA_FILES: dict[str, tuple[str, int]] = {
    "ces": ("d821773116d3c4e0360ea750066436c60ae45af02c39da3a840a543d761b3f41", 10918912),
    "deu": ("8407331d6aa0229dc927685c01a7938fc5a641d1a9524f74838cdac599f0d06e", 8628461),
    "eng": ("8280aed0782fe27257a68ea10fe7ef324ca0f8d85bd2fd145d1c2b560bcb66ba", 15400601),
    "fra": ("907743d98915c91a3906dfbf6e48b97598346698fe53aaa797e1a064ffcac913", 3972885),
    "ita": ("8df9c89176fb93f56bf4b2d4ede04c01c1f31d4b7697fbd76cc336df700f3f38", 8863635),
    "nld": ("92e7a1ad4bf8082e268de57c7823316ec024935702c6ed2a1e473b3a071aa733", 8903736),
    "pol": ("e80cc4cefbdface06e9223f43f089556b9dcf104020fbc0a200f6863c57d4405", 11978867),
    "por": ("711de9dbb8052067bd42f16b9119967f30bada80d57e2ef24f65d09f531adb04", 8159939),
    "slk": ("3553e335f64408412c8741fec19e443b5fda81d88abe59aa1401cba4e8825bed", 11542252),
    "spa": ("e2c1ffdad8b30f26c45d4017a9183d3a7f9aa69e59918be4f88b126fac99ab2c", 13570187),
    "ukr": ("1277f6e3b6f707063a92d40e7678e7f57154e8414e328e340be9ee9275eea9c8", 10859081),
}

# kod slownika -> katalog w repozytorium zrodlowym
SPELL_REPO_CODES: dict[str, str] = {
    "de_DE": "de",
    "en_US": "en",
    "es_ES": "es",
    "fr_FR": "fr",
    "it_IT": "it",
    "pl_PL": "pl",
}

# (kod slownika, rozszerzenie) -> (sha256, rozmiar)
DICT_FILES: dict[tuple[str, str], tuple[str, int]] = {
    ("de_DE", "aff"): ("57fdd1b16aac2131003c91e0cf2a488becb970382a402a9ce089307301cb3ef0", 19199),
    ("de_DE", "dic"): ("b5c781a0cf6f285fb6b9b8ab02fbea104b987104a1efdda8a835837e89e3ec77", 1118194),
    ("en_US", "aff"): ("8ae1f19d4840d957728ad90555d5a8dff6cc5c046279c95ff0c00fc0a0136c7b", 3086),
    ("en_US", "dic"): ("f0b1a234bd178bdd01875b2a392a9647f888b8fe879f79c52aae62c2759b3647", 551762),
    ("es_ES", "aff"): ("892039d59db11d747061b81c3a92a52d48ba0e055b5835af1943cbd3c2fba85b", 167135),
    ("es_ES", "dic"): ("907f786a8ceb3456722b20ad91dd4dbe99c5c16e45015ea63155e36f26b06d2c", 706202),
    ("fr_FR", "aff"): ("05a735d34c912e4e381ff08ee7c747923ccf5cf9dca81d8467982fa1ca51c2b7", 199870),
    ("fr_FR", "dic"): ("984e933237bc1224a48f42828233be9b03228260ef67aa8e2bdddcd03a26230d", 1229133),
    ("it_IT", "aff"): ("5770cd3e16d494c045b4a9a4a9fcd7962577e642d0384a7129c020a12cdd2c79", 70020),
    ("it_IT", "dic"): ("b1348fbdb6f441ea9dd7e33b2cfcb96ead39ccd5e48bf894972774cd5aa86abb", 1295754),
    ("pl_PL", "aff"): ("de7b54a8fa37562d58b481cf3d87a63e3dcc2d74021f6403eb0e4f5df9ecc225", 268824),
    ("pl_PL", "dic"): ("74b6155391025419967c26913541b55b36d58e80b1028037d4a0b8ddcb18d0b7", 4683579),
}
