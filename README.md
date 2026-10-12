# Albania — legislation as Markdown (LawCodex)

Laws of the **Republic of Albania** (Republika e Shqipërisë) as plain Markdown, generated
from the official database of the **Qendra e Botimeve Zyrtare** (QBZ, Official Publications
Centre, https://qbz.gov.al), publisher of the *Fletorja Zyrtare*. Language: Albanian (`sq`).

Part of [LawCodex](https://github.com/LawCodex): one repository per jurisdiction.

## What is covered

| Directory | Content | Files |
|---|---|---|
| `kushtetuta/` | Kushtetuta e Republikës së Shqipërisë (law 8417/1998), official consolidated text (2022) | 1 |
| `kode/` | Codes (Civil, Penal, Civil/Criminal Procedure, Labour, Family, Electoral, Customs, Maritime, Air, Railway, Military Penal, Juvenile Criminal Justice) | 13 |
| `ligje/<year>/` | All other laws (ligje) not recorded as repealed, incl. ratification laws | 2,654 |

Of the 2,668 files, 314 use the latest **official consolidated text** published by QBZ
("tekst i konsoliduar" / "i përditësuar"); the rest are the original text as published in
the Fletorja Zyrtare. When amending laws were published after the text used (66 files), their
full texts are appended in chronological order under *"Ndryshime të mëvonshme"*.

File names: `<yyyy>-<mm>-<dd>-<law no.>-<slug>.md` (date of the law), e.g.
`kode/1994-07-29-7850-kodi-civil-i-republikes-se-shqiperise.md`. Front matter: `title`,
`identifier` ("Ligj nr. …, datë …"), `eli` (QBZ ELI URI), `type`, `date`, `last_amended`,
`status`, `text_version` (`consolidated` / `original` [`_with_later_amendments`]),
`official_journal`, `source`, `consolidated_version`, `retrieved`.

## How the corpus was selected

QBZ's database (Alfresco; the public, anonymous REST API used by the qbz.gov.al web app) holds
4,957 acts of type *ligj*: 3,089 base acts, 1,731 amending acts, 97 repealing acts and 40
corrections. Base acts are kept unless QBZ records a repeal relation (`qbz:actRepeals`)
pointing to them (419 dropped). Amending/repealing acts are not separate files: their effect is
in the consolidated texts, or they are appended as described above. `status: in_force` means
"not recorded as repealed by QBZ" — implicit repeals are not tracked.

Text was extracted from QBZ's PDFs with `pdftotext`; article labels (Neni N) are `####`
headings, all-caps divisions (PJESA, KREU, TITULLI…) `###`. Footnotes of the PDFs remain inline.

## What is NOT covered

- Decisions of the Council of Ministers (*vendime*, ~30,000), decrees, orders, instructions and
  other secondary acts (available in the same database; skipped for volume).
- English translations (QBZ publishes few, not as an official corpus).

## Licence

Under Albanian copyright law (Law no. 35/2016), official texts of a legislative,
administrative or judicial nature are not protected by copyright. Texts as published by QBZ.

## Regenerating

```
python scripts/al_fetch.py  ../_raw/al
python scripts/al_convert.py ../_raw/al .
```

Needs `pdftotext` (poppler) and `scripts/requirements.txt`. Retrieved 2026-10-12.
