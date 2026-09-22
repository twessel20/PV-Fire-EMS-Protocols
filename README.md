# PVFIRE EMS Protocols

Mobile-first, offline-ready quick-reference interface for Pleasant Valley Fire Department EMS protocols.

## Firefighters
Open the published site in Safari/Chrome. Use search, categories and favorites. After the first successful online load, the app shell and current protocol index are cached for offline use.

## Officer / administrator updates
Routine maintenance does not require editing code.

### Replace one protocol
1. Find its `id` in `protocols.json` (for example `adult-chest-pain-stemi`).
2. Name the approved replacement PDF exactly `<id>.pdf`.
3. Upload it to `updates/single/` on the `main` branch.
4. GitHub Actions extracts the PDF text, replaces only that indexed entry, updates the date/search index, and republishes the site.
5. Verify the mobile view against the source PDF.

### Replace the whole book
Upload the approved new manual as `updates/full/protocol-book.pdf`. The automated processor attempts to locate every existing protocol title in the new book before replacing the index. If any title cannot be confidently located, it does not publish the full-book update.

## Access control
Only GitHub users with write access to this repository can upload/publish. Keep write access limited to designated PVFIRE officers/administrators.

## Clinical source
This site is a quick-reference presentation. The approved PVFIRE protocol source and Medical Control remain authoritative.
