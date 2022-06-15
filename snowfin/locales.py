from dataclasses import dataclass


@dataclass(frozen=True)
class Localization:
    da: str
    de: str
    en_GB: str
    en_US: str
    es_ES: str
    fr: str
    hr: str
    it: str
    lt: str
    hu: str
    nl: str
    no: str
    pl: str
    pt_BR: str
    ro: str
    fi: str
    sv_SE: str
    vi: str
    tr: str
    cs: str
    el: str
    bg: str
    ru: str
    uk: str
    hi: str
    th: str
    zh_CN: str
    ja: str
    zh_TW: str
    ko: str

    def __str__(self):
        return self.en_US

    def to_dict(self) -> dict:
        d = {}

        for k, v in self.__dict__.items():
            if k.startswith("__") or not v:
                continue

            d[k.replace("_", "-")] = v

        return d

    def get(self, lang: str, default: str) -> str:
        return getattr(self, lang, default)
