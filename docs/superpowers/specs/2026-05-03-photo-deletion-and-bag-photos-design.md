# Photo Deletion & Bag Photos — Design Spec

**Date:** 2026-05-03
**Status:** Approved (pending implementation)

## Summary

Two user-facing capabilities land together because they share a data model:

1. **Delete doll photos.** Admins can remove any photo from a doll's gallery. Deletion is soft (a `deleted_at` timestamp) so admins can recover mistaken deletions through a "show deleted" toggle. Deleting the current primary is refused when alternatives exist — admins must promote another photo first.
2. **Give each bag its own photo.** User-created containers ("Bag 1", "Bag 2", …) can have exactly one photo that displays as a banner on the dolls-list scope page and as a thumbnail in Admin. System containers (Home, Wishlist) are excluded.

The two features share one generalized `photos` table, one media-serving path, and one soft-delete mechanism.

## Goals

- Admins can delete any doll photo; kids and editors cannot.
- Admins can recover soft-deleted doll photos via a "show deleted" view.
- Deleting the current primary photo is refused when the doll has other live photos.
- Each user-created bag holds at most one photo, managed by admins.
- Bag photo displays as context on the `?scope=container-{id}` dolls list.
- All new UI strings exist in English, Hebrew, and Russian from day one.

## Non-Goals

- Orphan file garbage collection (soft-deleted files stay on disk; future cleanup task).
- Bulk photo deletion.
- Photo editing / cropping / rotation.
- Editor-level permissions on bag photos (admin-only for now; revisitable).
- Protecting soft-deleted media files from direct URL access (acceptable under LAN/SSO threat model).
- Real automated tests (project policy; manual verification only).

## Data Model

### `photos` table — generalized

Add columns:

| Column          | Type            | Notes                                                   |
|-----------------|-----------------|---------------------------------------------------------|
| `container_id`  | `INTEGER NULL`  | FK → `containers.id`, `ON DELETE CASCADE`, indexed      |
| `deleted_at`    | `DATETIME NULL` | Indexed; matches the soft-delete pattern used on dolls  |
| `deleted_by`    | `VARCHAR NULL`  | Subject identifier of the admin who deleted             |

Change columns:

- `doll_id` — make nullable (was `NOT NULL`).

### Code-enforced invariants

- **XOR owner:** exactly one of `doll_id` / `container_id` must be set on each row. Enforced by a SQLAlchemy validator and by Pydantic on write. The migration rebuilds the `photos` table anyway, so it also adds a table-level `CHECK ((doll_id IS NULL) <> (container_id IS NULL))` as a DB-level backstop.
- **Container-photo primary flag:** for rows where `container_id IS NOT NULL`, `is_primary` is always `True`.
- **One live photo per container:** `CREATE UNIQUE INDEX ux_photos_container_live ON photos(container_id) WHERE container_id IS NOT NULL AND deleted_at IS NULL`.

### `containers` table

No schema changes. System-container exclusion is an endpoint-level guard (`409 Conflict` if `is_system=True`), not a DB constraint.

### Migration

New file `backend/migrate_add_photo_deletion_and_container_photos.py`, registered in `run_migrations()` after the existing soft-delete migration. Steps:

1. Rebuild `photos` table (SQLite-safe pattern: create `photos_new`, copy rows, drop old, rename) so that `doll_id` becomes nullable and `container_id`, `deleted_at`, `deleted_by` columns are added.
2. `CREATE INDEX ix_photos_deleted_at ON photos(deleted_at)`.
3. `CREATE INDEX ix_photos_container_id ON photos(container_id)`.
4. `CREATE UNIQUE INDEX ux_photos_container_live ON photos(container_id) WHERE container_id IS NOT NULL AND deleted_at IS NULL`.

Runs in a transaction. Idempotent (checks for column/index existence before adding).

## Permissions

### New permissions

Added to the `Permission` enum in `backend/app/core/auth.py`:

- `PHOTO_DELETE` — admin only.
- `PHOTO_RESTORE` — admin only. Separate from `DELETE` so policy can diverge later.

### Permission matrix

| Permission              | Admin | Editor | Kid |
|-------------------------|:-----:|:------:|:---:|
| `PHOTO_ADD`             | ✓     | ✓      | ✓   |
| `PHOTO_SET_PRIMARY`     | ✓     | ✓      | ✓   |
| `PHOTO_DELETE`          | ✓     | ✗      | ✗   |
| `PHOTO_RESTORE`         | ✓     | ✗      | ✗   |

### Container photo permissions

Bag-photo endpoints reuse `PHOTO_ADD` (upload) and `PHOTO_DELETE` (delete) with an inline `container.is_system=False` check. No new permission is introduced for containers — admin-only on both sides.

### Media serving

`GET /media/{path}` stays unauthenticated (matches current behavior; assumes LAN/SSO at the proxy). Soft-deleted files remain on disk and remain fetchable by URL.

## API Endpoints

All endpoints use `Depends(require_permission(...))`. Errors use FastAPI `HTTPException` with the exact detail strings below.

### Doll photos

**`DELETE /photos/{photo_id}` → `204`**
Auth: `PHOTO_DELETE`.
- `404 photo not found` — not found or already soft-deleted.
- `409 cannot delete primary photo — set another primary first` — `is_primary=True` and at least one other live photo exists on the same doll.
- Otherwise: set `deleted_at=now()`, `deleted_by=current_user`, log `PHOTO_DELETED` event.
- Deleting the sole photo (primary or not) is **allowed** — doll ends up with no photos.

**`POST /photos/{photo_id}/restore` → `PhotoResponse`**
Auth: `PHOTO_RESTORE`.
- `404 photo not found` — not found or not deleted.
- `409 container already has a photo` — if restoring a container photo and a live one already exists (also enforced by unique partial index).
- Clear `deleted_at` and `deleted_by`.
- If restoring a doll photo and the doll currently has no live primary, mark the restored photo `is_primary=True` as part of the same transaction. Otherwise restore as non-primary.
- Log `PHOTO_RESTORED` event.

**`GET /dolls/{doll_id}/photos?include_deleted=true` → `PhotosListResponse`**
Auth: default `DOLL_READ` (the existing guard used on the current list-photos endpoint). `include_deleted=true` additionally requires `PHOTO_RESTORE` — if a non-admin passes the flag, the endpoint returns `403`.
- Default: excludes soft-deleted rows (matches today's behavior).
- With flag: returns all rows including deleted; each row carries `deleted_at` and `deleted_by`.

### Bag photo

**`POST /containers/{container_id}/photo` → `PhotoResponse`**
Auth: `PHOTO_ADD` + inline role check (admin only — uploading a bag photo requires admin even though `PHOTO_ADD` alone is broader) + `is_system=False` check.
- `404 container not found`.
- `409 system containers cannot have photos` — if `is_system=True`.
- Multipart `file` validated like existing doll upload (size, mime type).
- If a live photo already exists for this container: soft-delete it in the same transaction (set `deleted_at`, `deleted_by`) before inserting the new row. New row has `is_primary=True`.
- Log `CONTAINER_PHOTO_ADDED`. If a replacement occurred, also log `CONTAINER_PHOTO_REPLACED`.

**`DELETE /containers/{container_id}/photo` → `204`**
Auth: `PHOTO_DELETE` (admin-only) + `is_system=False` check.
- `404 container has no photo` — container has no live photo.
- `409 system containers cannot have photos` — if `is_system=True`.
- Soft-delete the live container photo (no primary-reassignment logic — bag has one photo by design).
- Log `CONTAINER_PHOTO_DELETED`.

**`GET /containers/{container_id}/photo` → `{photo: PhotoResponse | null}`**
Auth: `CONTAINER_READ` (existing).
- Returns the live photo or `null`. System containers always return `null`.
- Also inlined into `GET /containers` list responses (field name `photo`, value `PhotoResponse | null`) so the Admin page can render thumbnails without N extra round-trips. System containers in that list also carry `photo: null`.

### Event types (new)

Added to the `EventType` enum: `PHOTO_DELETED`, `PHOTO_RESTORED`, `CONTAINER_PHOTO_ADDED`, `CONTAINER_PHOTO_REPLACED`, `CONTAINER_PHOTO_DELETED`.

Container-photo event rows write `doll_id = NULL` and include `container_id` in the event payload. Existing event filters keyed on `doll_id` naturally exclude these.

### Schema changes (Pydantic)

`PhotoResponse` gains three optional fields:

- `container_id: int | None`
- `deleted_at: datetime | None`
- `deleted_by: str | None`

Existing consumers ignore them.

## Frontend

### Doll detail page (`frontend/src/pages/DollDetail.tsx`)

- **Delete button** on each gallery thumbnail, rendered only for admins. Top-right overlay, same visual weight as the existing ★ primary badge.
- Native `confirm()` before calling `DELETE /photos/{id}`.
- On `409 cannot delete primary`: toast using i18n key `photo_delete_refused_primary`.
- Optimistic UI: thumbnail disappears on `204`; on error, re-fetch gallery.

### "Show deleted photos" admin toggle

- Small toggle at the top of the gallery, visible only to admins (i18n `show_deleted_photos`).
- When on, requests `GET /dolls/{id}/photos?include_deleted=true`.
- Soft-deleted photos render with a grayed-out overlay and a "Restore" button (i18n `restore`).
- Deleted photos cannot be set primary directly — must be restored first.

### Admin page (`frontend/src/pages/Admin.tsx`)

Each non-system container row gets an inline photo block:

- No photo → "Upload photo" button (i18n `upload_bag_photo`).
- Photo present → 48×48 thumbnail + "Replace" + "Remove" (i18n `replace_bag_photo`, `remove_bag_photo`).
- Remove uses native `confirm()`.
- System containers render no photo controls.
- Thumbnail URLs come from the inlined `photo` field on the `GET /containers` response.

### Dolls-list scope page (`frontend/src/pages/DollsList.tsx`)

When `scope=container-{id}` resolves to a non-system container with a live photo:

- Render the bag photo as a banner at the top of the list, above the existing title, ~160px tall on mobile, `object-fit: cover`.
- Tapping the banner opens the full-size image via the existing `/media/{path}` URL (no lightbox library).
- No upload/delete controls here — management lives in Admin.
- System containers or containers with no photo: no banner (page unchanged).

### API client (`frontend/src/api/`)

New functions:

- `deletePhoto(photoId: number): Promise<void>`
- `restorePhoto(photoId: number): Promise<PhotoResponse>`
- `listPhotos(dollId: number, opts?: {includeDeleted?: boolean}): Promise<PhotosListResponse>`
- `uploadContainerPhoto(containerId: number, file: File): Promise<PhotoResponse>`
- `deleteContainerPhoto(containerId: number): Promise<void>`

The `PhotoResponse` TS type adds the three optional fields.

### i18n — new keys (all three locales in the same commit)

`photo_delete` · `photo_delete_confirm` · `photo_delete_refused_primary` · `photo_deleted` · `show_deleted_photos` · `restore` · `photo_restored` · `upload_bag_photo` · `replace_bag_photo` · `remove_bag_photo` · `bag_photo` · `bag_photo_removed` · `bag_photo_replaced`

## Edge Cases & Invariants

1. Deleting the only photo (primary or not) — allowed. Doll ends up photoless.
2. Deleting the primary when other live photos exist — refused `409`.
3. Restoring a photo when the doll has no live primary — restored photo becomes primary in the same transaction.
4. Restoring a photo when a primary already exists — restored as non-primary.
5. Restoring a container photo when a live one already exists — refused `409` (also DB-enforced via unique partial index).
6. Replacing a bag photo — old soft-deleted + new inserted in a single transaction. Atomic.
7. Upload / delete on a system container — refused `409`.
8. Soft-deleted files on disk remain and remain fetchable via `/media/{path}`. Acceptable.
9. Hard deletion of a doll cascades via existing `cascade="all, delete-orphan"` — wipes photo rows (live and deleted) but not files. Matches today's behavior.
10. Deletion of a container cascades via new `ON DELETE CASCADE` on `container_id` — wipes all photo rows for that container (live and deleted), but not files.
11. `PhotoResponse.is_primary` for container photos is always `True`. Frontend ignores the field for container photos.
12. Container-photo events use `doll_id = NULL`; existing doll-scoped event filters exclude them naturally.

## Error Contract

| Case                                                  | Status | Body `detail`                                              |
|-------------------------------------------------------|:------:|------------------------------------------------------------|
| Delete non-primary / primary-only photo                | `204`  | —                                                          |
| Delete primary when alternatives exist                 | `409`  | `cannot delete primary photo — set another primary first`  |
| Delete/restore non-existent or wrong-state photo       | `404`  | `photo not found`                                          |
| Restore container photo when live one exists           | `409`  | `container already has a photo`                            |
| Upload/delete photo on system container                | `409`  | `system containers cannot have photos`                     |
| Container has no live photo on DELETE                  | `404`  | `container has no photo`                                   |
| Non-admin attempts delete/restore                      | `403`  | existing `require_permission` response                     |

## Atomicity

Both the doll-photo upload (existing) and the bag-photo replace flow use a single SQLAlchemy transaction with `session.begin()`. File writes happen before DB commit; if the commit fails, the newly-written file is unlinked in a `finally` block. Restore-and-promote-to-primary also runs as one transaction.

## Testing

Per the project's current policy (CLAUDE.md: "no real test suite"), no automated tests are added. The implementation plan will include a **manual verification checklist** mapping each of the 12 edge cases to clickable steps through the running Docker Compose stack, plus an i18n sweep that opens each language and visits the doll detail page, Admin page, and bag scope page.

## Open Questions

None at design time. All decisions captured above.
