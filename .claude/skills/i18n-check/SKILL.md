---
name: i18n-check
description: Verify that Hebrew, Russian, and English locale files in frontend/src/i18n/ have identical key sets. Use after adding or renaming user-facing strings, and before committing any change that touches a locale file.
---

# Check i18n locale sync

The frontend supports three locales: English (`en.json`), Hebrew (`he.json`), Russian (`ru.json`), all in `frontend/src/i18n/`. Every key must exist in all three files.

## Steps

1. Read all three files:
   - `frontend/src/i18n/en.json`
   - `frontend/src/i18n/he.json`
   - `frontend/src/i18n/ru.json`

2. Recursively flatten each into a set of dotted paths (e.g. `nav.home`, `form.submit.label`).

3. Compare the three sets. For each locale, report:
   - **Missing keys** (present in at least one other locale, absent here)
   - **Extra keys** (present here, absent in at least one other locale)

4. If all three sets are identical, report "All three locales are in sync" and stop.

5. Otherwise, print a table grouped by key:

   | Key | en | he | ru |
   |-----|----|----|----|
   | nav.profile | ✓ | ✓ | ✗ |

   Then, for each missing entry, suggest a translation based on the existing English string and the surrounding context. Ask the user to confirm each suggestion before writing it — Hebrew and Russian translations are not something to guess silently.

6. Write the confirmed translations back into the appropriate JSON files, preserving the existing key order and indentation style (2 spaces, trailing newline).

## Notes

- Preserve existing placeholders like `{{name}}` or `{count}` exactly — do not translate the variable names.
- Hebrew is RTL; ensure any punctuation you add matches the source string's intent.
- If a key was intentionally removed, offer to delete it from the other two locales instead of filling it in.
