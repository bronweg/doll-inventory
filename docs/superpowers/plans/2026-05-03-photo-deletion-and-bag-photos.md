# Photo Deletion & Bag Photos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add soft-delete for doll photos and per-bag photo support, sharing one generalized `photos` table.

**Architecture:** Extend the `photos` table with `container_id`, `deleted_at`, `deleted_by` columns and make `doll_id` nullable; add new API endpoints for delete/restore/bag-photo; update frontend DollDetail, Admin, and DollsList pages.

**Tech Stack:** FastAPI + SQLAlchemy 2.x + SQLite (backend); React 18 + TypeScript + i18next (frontend); Docker Compose local dev.

---

## File Map

**Backend — modified:**
- `backend/app/db/models.py` — Photo model: add columns, make doll_id nullable, add container relationship
- `backend/app/db/migrations.py` — add `_migrate_002_photo_deletion_and_container_photos()`
- `backend/app/core/auth.py` — add `PHOTO_DELETE`, `PHOTO_RESTORE` to Permission class and `all_permissions()`
- `backend/app/schemas/photos.py` — extend `PhotoResponse`, add `PhotosListResponse` with `include_deleted`
- `backend/app/services/photos_service.py` — add soft-delete, restore, container-photo helpers
- `backend/app/api/photos.py` — add DELETE/restore endpoints; update list endpoint; add container photo endpoints

**Frontend — modified:**
- `frontend/src/api/dolls.ts` — extend `Photo` type, update `getPhotos()`, add `deletePhoto()`, `restorePhoto()`
- `frontend/src/api/containers.ts` — extend `Container` type with `photo` field; add `uploadContainerPhoto()`, `deleteContainerPhoto()`
- `frontend/src/pages/DollDetail.tsx` — add delete button, show-deleted toggle, restore button
- `frontend/src/pages/Admin.tsx` — add per-container photo block (upload/replace/remove)
- `frontend/src/pages/DollsList.tsx` — render bag photo banner for container scopes
- `frontend/src/i18n/en.json`, `he.json`, `ru.json` — add 13 new keys

---

### Task 1: Migration — extend photos table

**Files:**
- Modify: `backend/app/db/migrations.py`

- [ ] **Step 1: Add the migration function**

Open `backend/app/db/migrations.py`. Add this function before the final line of the file:

```python
def _index_exists(conn: sqlite3.Connection, index_name: str) -> bool:
    """Check if an index exists."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,)
    )
    return cursor.fetchone() is not None


def _migrate_002_photo_deletion_and_container_photos(conn: sqlite3.Connection) -> None:
    """
    Migration 002: Generalize photos table for soft-delete and container photos.

    1. Rebuild photos table: doll_id nullable, add container_id / deleted_at / deleted_by.
    2. Add indexes on deleted_at and container_id.
    3. Add partial unique index: one live photo per container.
    """
    logger.info("Running migration 002: Photo deletion and container photos")
    cursor = conn.cursor()

    # Check if already migrated (container_id column present)
    if _column_exists(conn, "photos", "container_id"):
        logger.info("✓ Migration 002 already applied")
        return

    # Fetch existing rows before rebuild
    cursor.execute("SELECT id, doll_id, path, is_primary, created_at, created_by FROM photos")
    existing_photos = cursor.fetchall()

    # Rebuild photos table with new schema
    cursor.execute("ALTER TABLE photos RENAME TO photos_old")
    cursor.execute("""
        CREATE TABLE photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doll_id INTEGER REFERENCES dolls(id) ON DELETE CASCADE,
            container_id INTEGER REFERENCES containers(id) ON DELETE CASCADE,
            path VARCHAR(500) NOT NULL,
            is_primary BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL,
            created_by VARCHAR(255) NOT NULL,
            deleted_at DATETIME,
            deleted_by VARCHAR(255),
            CHECK ((doll_id IS NULL) <> (container_id IS NULL))
        )
    """)

    # Restore existing rows
    if existing_photos:
        cursor.executemany(
            "INSERT INTO photos (id, doll_id, path, is_primary, created_at, created_by) VALUES (?,?,?,?,?,?)",
            existing_photos
        )

    cursor.execute("DROP TABLE photos_old")

    # Recreate existing index
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_photos_doll_id ON photos(doll_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_photos_is_primary ON photos(is_primary)")

    # New indexes
    if not _index_exists(conn, "ix_photos_deleted_at"):
        cursor.execute("CREATE INDEX ix_photos_deleted_at ON photos(deleted_at)")
    if not _index_exists(conn, "ix_photos_container_id"):
        cursor.execute("CREATE INDEX ix_photos_container_id ON photos(container_id)")
    if not _index_exists(conn, "ux_photos_container_live"):
        cursor.execute(
            "CREATE UNIQUE INDEX ux_photos_container_live ON photos(container_id) "
            "WHERE container_id IS NOT NULL AND deleted_at IS NULL"
        )

    logger.info("✓ Migration 002 completed")
```

- [ ] **Step 2: Register the migration in `run_migrations()`**

In `backend/app/db/migrations.py`, find the `run_migrations()` function body. After the line `_migrate_001_add_containers(conn)`, add:

```python
        _migrate_002_photo_deletion_and_container_photos(conn)
```

- [ ] **Step 3: Verify syntax**

```bash
docker compose -f docker/docker-compose.local.yml run --rm backend python -c "from app.db.migrations import run_migrations; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/db/migrations.py
git commit -m "feat: migration 002 — generalize photos table for soft-delete and container photos"
```

---

### Task 2: Update SQLAlchemy Photo model

**Files:**
- Modify: `backend/app/db/models.py`

- [ ] **Step 1: Update the Photo class**

Replace the entire `Photo` class in `backend/app/db/models.py` with:

```python
class Photo(Base):
    """Photo model for doll or container images."""
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    doll_id = Column(Integer, ForeignKey("dolls.id", ondelete="CASCADE"), nullable=True, index=True)
    container_id = Column(Integer, ForeignKey("containers.id", ondelete="CASCADE"), nullable=True, index=True)
    path = Column(String(500), nullable=False)
    is_primary = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(String(255), nullable=False)
    deleted_at = Column(DateTime, nullable=True, index=True)
    deleted_by = Column(String(255), nullable=True)

    doll = relationship("Doll", back_populates="photos")
    container = relationship("Container", back_populates="photos")
```

- [ ] **Step 2: Add `photos` relationship to Container**

In `backend/app/db/models.py`, find the `Container` class. After the line `dolls = relationship("Doll", back_populates="container")`, add:

```python
    photos = relationship("Photo", back_populates="container", cascade="all, delete-orphan")
```

- [ ] **Step 3: Verify no import errors**

```bash
docker compose -f docker/docker-compose.local.yml run --rm backend python -c "from app.db.models import Photo, Container; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/db/models.py
git commit -m "feat: update Photo model — nullable doll_id, add container_id/deleted_at/deleted_by"
```

---

### Task 3: Add PHOTO_DELETE and PHOTO_RESTORE permissions

**Files:**
- Modify: `backend/app/core/auth.py`

- [ ] **Step 1: Add permission constants**

In `backend/app/core/auth.py`, find the `Permission` class. After the line `PHOTO_SET_PRIMARY = "photo:set_primary"`, add:

```python
    PHOTO_DELETE = "photo:delete"
    PHOTO_RESTORE = "photo:restore"
```

- [ ] **Step 2: Add to `all_permissions()`**

In the same file, find the `all_permissions()` method. Add to the returned set:

```python
            cls.PHOTO_DELETE,
            cls.PHOTO_RESTORE,
```

(The set now includes `PHOTO_DELETE` and `PHOTO_RESTORE`; admin gets both automatically.)

- [ ] **Step 3: Verify**

```bash
docker compose -f docker/docker-compose.local.yml run --rm backend python -c "from app.core.auth import Permission; print(Permission.PHOTO_DELETE, Permission.PHOTO_RESTORE)"
```

Expected: `photo:delete photo:restore`

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/auth.py
git commit -m "feat: add PHOTO_DELETE and PHOTO_RESTORE permissions (admin-only)"
```

---

### Task 4: Extend Pydantic schemas

**Files:**
- Modify: `backend/app/schemas/photos.py`

- [ ] **Step 1: Replace the file content**

```python
"""
Pydantic schemas for photos.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PhotoResponse(BaseModel):
    """Schema for a single photo."""
    id: int
    doll_id: Optional[int] = None
    container_id: Optional[int] = None
    url: str
    is_primary: bool
    created_at: datetime
    created_by: str
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None

    class Config:
        from_attributes = True


class PhotoListResponse(BaseModel):
    """Schema for list of photos for a doll."""
    doll_id: int
    primary_photo_id: Optional[int] = None
    photos: list[PhotoResponse]


class SetPrimaryResponse(BaseModel):
    """Schema for set primary photo response."""
    doll_id: int
    primary_photo_id: int
    photo_id: int


class ContainerPhotoResponse(BaseModel):
    """Schema for container photo response (wraps nullable photo)."""
    photo: Optional[PhotoResponse] = None
```

- [ ] **Step 2: Verify**

```bash
docker compose -f docker/docker-compose.local.yml run --rm backend python -c "from app.schemas.photos import PhotoResponse, ContainerPhotoResponse; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/photos.py
git commit -m "feat: extend PhotoResponse with optional container_id/deleted_at/deleted_by"
```

---

### Task 5: Extend photos_service with soft-delete and container helpers

**Files:**
- Modify: `backend/app/services/photos_service.py`

- [ ] **Step 1: Add imports**

At the top of `backend/app/services/photos_service.py`, the existing import is:
```python
from app.db.models import Photo, Doll, Event
```
Change it to:
```python
from app.db.models import Photo, Doll, Container, Event
```

Also ensure `datetime` is imported — it already is via `from datetime import datetime` in the file? Check: the file imports only from pathlib and fastapi. Add at the top:
```python
from datetime import datetime
```

- [ ] **Step 2: Add soft-delete helper**

Append to `backend/app/services/photos_service.py`:

```python
def soft_delete_photo(db: Session, photo: Photo, deleted_by: str) -> None:
    """Mark a photo as soft-deleted."""
    photo.deleted_at = datetime.utcnow()
    photo.deleted_by = deleted_by


def restore_photo(db: Session, photo: Photo) -> None:
    """Clear soft-delete flags on a photo."""
    photo.deleted_at = None
    photo.deleted_by = None


def get_live_photos_for_doll(db: Session, doll_id: int) -> list[Photo]:
    """Return non-deleted photos for a doll, newest first."""
    return (
        db.query(Photo)
        .filter(Photo.doll_id == doll_id, Photo.deleted_at.is_(None))
        .order_by(Photo.created_at.desc())
        .all()
    )


def get_live_primary_for_doll(db: Session, doll_id: int) -> Optional[Photo]:
    """Return the live primary photo for a doll, or None."""
    return db.query(Photo).filter(
        Photo.doll_id == doll_id,
        Photo.is_primary == True,
        Photo.deleted_at.is_(None)
    ).first()


def get_live_photo_for_container(db: Session, container_id: int) -> Optional[Photo]:
    """Return the live photo for a container, or None."""
    return db.query(Photo).filter(
        Photo.container_id == container_id,
        Photo.deleted_at.is_(None)
    ).first()


def create_container_photo_record(
    db: Session,
    container_id: int,
    path: str,
    created_by: str
) -> Photo:
    """Create a primary photo record for a container."""
    photo = Photo(
        container_id=container_id,
        path=path,
        is_primary=True,
        created_by=created_by
    )
    db.add(photo)
    db.flush()
    return photo


async def save_container_photo_file(container_id: int, file) -> str:
    """Save an uploaded container photo file to disk."""
    from app.utils.media import get_file_extension, ensure_directory_exists
    import uuid
    ext = get_file_extension(file.filename, file.content_type)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    uuid_suffix = str(uuid.uuid4()).split('-')[0]
    relative_path = f"containers/{container_id}/{timestamp}_{uuid_suffix}{ext}"
    full_path = settings.PHOTOS_DIR / relative_path
    ensure_directory_exists(full_path.parent)
    with open(full_path, "wb") as f:
        content = await file.read()
        f.write(content)
    return relative_path


def log_container_photo_event(
    db: Session,
    container_id: int,
    event_type: str,
    photo_id: int,
    created_by: str
) -> None:
    """Log a container-photo event (doll_id = NULL)."""
    import json
    payload = {"photo_id": photo_id, "container_id": container_id}
    event = Event(
        doll_id=None,
        event_type=event_type,
        payload=json.dumps(payload),
        created_by=created_by
    )
    db.add(event)
```

- [ ] **Step 3: Fix Event model to allow nullable doll_id**

The `Event` model has `doll_id` as `nullable=False`. We need to allow NULL for container events. Open `backend/app/db/models.py` and change the Event.doll_id line from:

```python
    doll_id = Column(Integer, ForeignKey("dolls.id", ondelete="CASCADE"), nullable=False, index=True)
```

to:

```python
    doll_id = Column(Integer, ForeignKey("dolls.id", ondelete="CASCADE"), nullable=True, index=True)
```

And add the events migration step to migration 002 in `backend/app/db/migrations.py`. Inside `_migrate_002_photo_deletion_and_container_photos`, before the `logger.info("✓ Migration 002 completed")` line, add:

```python
    # Make events.doll_id nullable (needed for container-photo events)
    if not _column_exists(conn, "events", "doll_id"):
        pass  # already handled
    else:
        cursor.execute("PRAGMA table_info(events)")
        events_cols = cursor.fetchall()
        doll_id_col = next((c for c in events_cols if c[1] == "doll_id"), None)
        if doll_id_col and doll_id_col[3] == 1:  # notnull == 1
            logger.info("Making events.doll_id nullable...")
            cursor.execute("SELECT id, doll_id, event_type, payload, created_at, created_by FROM events")
            existing_events = cursor.fetchall()
            cursor.execute("ALTER TABLE events RENAME TO events_old")
            cursor.execute("""
                CREATE TABLE events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doll_id INTEGER REFERENCES dolls(id) ON DELETE CASCADE,
                    event_type VARCHAR(50) NOT NULL,
                    payload TEXT,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(255) NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_events_doll_id ON events(doll_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_events_event_type ON events(event_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_events_created_at ON events(created_at)")
            if existing_events:
                cursor.executemany(
                    "INSERT INTO events (id, doll_id, event_type, payload, created_at, created_by) VALUES (?,?,?,?,?,?)",
                    existing_events
                )
            cursor.execute("DROP TABLE events_old")
            logger.info("✓ Made events.doll_id nullable")
        else:
            logger.info("✓ events.doll_id already nullable")
```

- [ ] **Step 4: Verify**

```bash
docker compose -f docker/docker-compose.local.yml run --rm backend python -c "from app.services.photos_service import soft_delete_photo, restore_photo, get_live_photo_for_container; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/photos_service.py backend/app/db/models.py backend/app/db/migrations.py
git commit -m "feat: add soft-delete, restore, and container photo helpers to photos_service"
```

---

### Task 6: Add backend API endpoints

**Files:**
- Modify: `backend/app/api/photos.py`

- [ ] **Step 1: Update imports at top of photos.py**

The current import block imports `Doll, Photo`. Change it to also import `Container`:

```python
from app.db.models import Doll, Photo, Container
```

Also add to the schemas import:
```python
from app.schemas.photos import PhotoResponse, PhotoListResponse, SetPrimaryResponse, ContainerPhotoResponse
```

Also add `Permission.PHOTO_DELETE` and `Permission.PHOTO_RESTORE` — they're accessed via `Permission.PHOTO_DELETE` so no import change needed (Permission is already imported).

- [ ] **Step 2: Update `photo_to_response` to include new fields**

Replace the existing `photo_to_response` function:

```python
def photo_to_response(photo: Photo) -> PhotoResponse:
    """Convert a Photo model to PhotoResponse."""
    return PhotoResponse(
        id=photo.id,
        doll_id=photo.doll_id,
        container_id=photo.container_id,
        url=build_photo_url(photo.path),
        is_primary=photo.is_primary,
        created_at=photo.created_at,
        created_by=photo.created_by,
        deleted_at=photo.deleted_at,
        deleted_by=photo.deleted_by,
    )
```

- [ ] **Step 3: Update `list_photos` to support `include_deleted`**

Replace the existing `list_photos` endpoint:

```python
@router.get("/dolls/{doll_id}/photos", response_model=PhotoListResponse)
async def list_photos(
    doll_id: int,
    include_deleted: bool = False,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[User, Depends(require_permission(Permission.DOLL_READ))] = None,
):
    """List photos for a doll. include_deleted=true requires photo:restore permission."""
    doll = db.query(Doll).filter(Doll.id == doll_id).first()
    if not doll:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Doll with id {doll_id} not found")

    if include_deleted and not user.has_permission(Permission.PHOTO_RESTORE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission required: {Permission.PHOTO_RESTORE}")

    query = db.query(Photo).filter(Photo.doll_id == doll_id)
    if not include_deleted:
        query = query.filter(Photo.deleted_at.is_(None))
    photos = query.order_by(Photo.created_at.desc()).all()

    primary_photo_id = next((p.id for p in photos if p.is_primary and p.deleted_at is None), None)

    return PhotoListResponse(
        doll_id=doll_id,
        primary_photo_id=primary_photo_id,
        photos=[photo_to_response(p) for p in photos]
    )
```

- [ ] **Step 4: Add `DELETE /photos/{photo_id}` endpoint**

After the `set_primary_photo` endpoint in `backend/app/api/photos.py`, add:

```python
@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    photo_id: int,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[User, Depends(require_permission(Permission.PHOTO_DELETE))] = None,
):
    """
    Soft-delete a photo. Refuses if photo is primary and other live photos exist.
    Requires: photo:delete permission (admin only).
    """
    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.deleted_at.is_(None)).first()
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="photo not found")

    # Refuse deleting primary when alternatives exist
    if photo.doll_id and photo.is_primary:
        other_live = db.query(Photo).filter(
            Photo.doll_id == photo.doll_id,
            Photo.id != photo_id,
            Photo.deleted_at.is_(None)
        ).count()
        if other_live > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="cannot delete primary photo — set another primary first"
            )

    from app.services import photos_service
    photos_service.soft_delete_photo(db, photo, user.email)
    photos_service.log_photo_event(
        db=db,
        doll_id=photo.doll_id,
        event_type="PHOTO_DELETED",
        photo_id=photo.id,
        created_by=user.email,
    )
    db.commit()
    return None
```

- [ ] **Step 5: Add `POST /photos/{photo_id}/restore` endpoint**

```python
@router.post("/photos/{photo_id}/restore", response_model=PhotoResponse)
async def restore_photo(
    photo_id: int,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[User, Depends(require_permission(Permission.PHOTO_RESTORE))] = None,
):
    """
    Restore a soft-deleted photo.
    If restoring a doll photo and doll has no live primary, promote restored photo.
    Requires: photo:restore permission (admin only).
    """
    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.deleted_at.isnot(None)).first()
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="photo not found")

    # Container photo: refuse if another live photo already exists
    if photo.container_id:
        existing = db.query(Photo).filter(
            Photo.container_id == photo.container_id,
            Photo.deleted_at.is_(None)
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="container already has a photo")

    from app.services import photos_service
    photos_service.restore_photo(db, photo)

    # Auto-promote to primary if doll has no live primary
    if photo.doll_id:
        live_primary = photos_service.get_live_primary_for_doll(db, photo.doll_id)
        if not live_primary:
            photo.is_primary = True

    photos_service.log_photo_event(
        db=db,
        doll_id=photo.doll_id,
        event_type="PHOTO_RESTORED",
        photo_id=photo.id,
        created_by=user.email,
    )
    db.commit()
    db.refresh(photo)
    return photo_to_response(photo)
```

- [ ] **Step 6: Add container photo endpoints**

```python
@router.post("/containers/{container_id}/photo", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_container_photo(
    container_id: int,
    file: Annotated[UploadFile, File(...)],
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[User, Depends(require_permission(Permission.PHOTO_ADD))] = None,
):
    """
    Upload (or replace) a photo for a user-created container.
    Admin only; system containers are refused.
    Requires: photo:add permission + admin role check.
    """
    if not user.has_permission(Permission.PHOTO_DELETE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission required: {Permission.PHOTO_DELETE}")

    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="container not found")
    if container.is_system:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="system containers cannot have photos")

    if not is_valid_image(file.filename, file.content_type):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image (jpg, jpeg, png, webp, gif)")

    from app.services import photos_service
    replaced = False
    existing = photos_service.get_live_photo_for_container(db, container_id)
    if existing:
        photos_service.soft_delete_photo(db, existing, user.email)
        replaced = True

    relative_path = await photos_service.save_container_photo_file(container_id, file)
    photo = photos_service.create_container_photo_record(db, container_id, relative_path, user.email)

    photos_service.log_container_photo_event(db, container_id, "CONTAINER_PHOTO_ADDED", photo.id, user.email)
    if replaced:
        photos_service.log_container_photo_event(db, container_id, "CONTAINER_PHOTO_REPLACED", photo.id, user.email)

    db.commit()
    db.refresh(photo)
    return photo_to_response(photo)


@router.delete("/containers/{container_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
async def delete_container_photo(
    container_id: int,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[User, Depends(require_permission(Permission.PHOTO_DELETE))] = None,
):
    """
    Soft-delete a container's photo.
    Requires: photo:delete permission (admin only).
    """
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="container not found")
    if container.is_system:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="system containers cannot have photos")

    from app.services import photos_service
    photo = photos_service.get_live_photo_for_container(db, container_id)
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="container has no photo")

    photos_service.soft_delete_photo(db, photo, user.email)
    photos_service.log_container_photo_event(db, container_id, "CONTAINER_PHOTO_DELETED", photo.id, user.email)
    db.commit()
    return None


@router.get("/containers/{container_id}/photo", response_model=ContainerPhotoResponse)
async def get_container_photo(
    container_id: int,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[User, Depends(require_permission(Permission.CONTAINER_READ))] = None,
):
    """Return the live photo for a container, or null."""
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="container not found")
    if container.is_system:
        return ContainerPhotoResponse(photo=None)

    from app.services import photos_service
    photo = photos_service.get_live_photo_for_container(db, container_id)
    return ContainerPhotoResponse(photo=photo_to_response(photo) if photo else None)
```

- [ ] **Step 7: Update `log_photo_event` in photos_service to allow nullable doll_id**

In `backend/app/services/photos_service.py`, the `log_photo_event` function signature has `doll_id: int`. Change it to `doll_id: Optional[int]`:

```python
def log_photo_event(
    db: Session,
    doll_id: Optional[int],
    event_type: str,
    photo_id: int,
    created_by: str,
    path: Optional[str] = None
) -> None:
```

- [ ] **Step 8: Update containers list endpoint to inline photo field**

In `backend/app/api/containers.py`, add import:

```python
from app.schemas.photos import PhotoResponse
from app.services import photos_service
```

Change `ContainerListResponse` and `ContainerResponse` usage to inline photo. Actually, the cleanest approach: update the `list_containers` endpoint to return a custom response with photo inlined. First update `backend/app/schemas/containers.py` — add `photo` field to `ContainerResponse`:

In `backend/app/schemas/containers.py`, change:
```python
from typing import Optional
from app.schemas.photos import PhotoResponse
```
at the top (add the import), and add to `ContainerResponse`:
```python
    photo: Optional[PhotoResponse] = None
```

Then update `list_containers` in `backend/app/api/containers.py` to populate it:

```python
from app.db.models import Container, Doll, Photo
from app.services import photos_service
from app.api.photos import photo_to_response
```

In `list_containers`, change the return to:
```python
    container_responses = []
    for c in containers:
        photo = None if c.is_system else photos_service.get_live_photo_for_container(db, c.id)
        resp = ContainerResponse(
            id=c.id,
            name=c.name,
            sort_order=c.sort_order,
            is_active=c.is_active,
            is_system=c.is_system,
            created_at=c.created_at,
            updated_at=c.updated_at,
            photo=photo_to_response(photo) if photo else None,
        )
        container_responses.append(resp)

    return ContainerListResponse(
        items=container_responses,
        total=total
    )
```

- [ ] **Step 9: Start stack and smoke-test endpoints**

```bash
docker compose -f docker/docker-compose.local.yml up -d --build
```

Then verify at http://localhost:8000/docs:
- `DELETE /api/photos/{photo_id}` exists
- `POST /api/photos/{photo_id}/restore` exists
- `GET /api/dolls/{doll_id}/photos?include_deleted=true` returns all photos
- `POST /api/containers/{container_id}/photo` exists
- `DELETE /api/containers/{container_id}/photo` exists
- `GET /api/containers/{container_id}/photo` exists
- `GET /api/containers` now returns `photo` field per item

- [ ] **Step 10: Commit**

```bash
git add backend/app/api/photos.py backend/app/api/containers.py backend/app/schemas/containers.py backend/app/services/photos_service.py
git commit -m "feat: add photo delete/restore endpoints and container photo endpoints"
```

---

### Task 7: i18n — add new keys to all three locales

**Files:**
- Modify: `frontend/src/i18n/en.json`, `frontend/src/i18n/he.json`, `frontend/src/i18n/ru.json`

- [ ] **Step 1: Add keys to en.json**

In `frontend/src/i18n/en.json`, before the closing `}`, add:

```json
  "photo_delete": "Delete Photo",
  "photo_delete_confirm": "Delete this photo?",
  "photo_delete_refused_primary": "Cannot delete the primary photo while other photos exist — set another as primary first.",
  "photo_deleted": "Photo deleted",
  "show_deleted_photos": "Show deleted photos",
  "restore": "Restore",
  "photo_restored": "Photo restored",
  "upload_bag_photo": "Upload bag photo",
  "replace_bag_photo": "Replace",
  "remove_bag_photo": "Remove",
  "bag_photo": "Bag Photo",
  "bag_photo_removed": "Bag photo removed",
  "bag_photo_replaced": "Bag photo replaced"
```

- [ ] **Step 2: Add keys to he.json**

In `frontend/src/i18n/he.json`, before the closing `}`, add:

```json
  "photo_delete": "מחק תמונה",
  "photo_delete_confirm": "למחוק תמונה זו?",
  "photo_delete_refused_primary": "לא ניתן למחוק את התמונה הראשית כשקיימות תמונות אחרות — הגדר תחילה תמונה אחרת כראשית.",
  "photo_deleted": "התמונה נמחקה",
  "show_deleted_photos": "הצג תמונות שנמחקו",
  "restore": "שחזר",
  "photo_restored": "התמונה שוחזרה",
  "upload_bag_photo": "העלה תמונת תיק",
  "replace_bag_photo": "החלף",
  "remove_bag_photo": "הסר",
  "bag_photo": "תמונת תיק",
  "bag_photo_removed": "תמונת התיק הוסרה",
  "bag_photo_replaced": "תמונת התיק הוחלפה"
```

- [ ] **Step 3: Add keys to ru.json**

In `frontend/src/i18n/ru.json`, before the closing `}`, add:

```json
  "photo_delete": "Удалить фото",
  "photo_delete_confirm": "Удалить это фото?",
  "photo_delete_refused_primary": "Нельзя удалить главное фото, пока есть другие — сначала сделайте другое фото главным.",
  "photo_deleted": "Фото удалено",
  "show_deleted_photos": "Показать удалённые фото",
  "restore": "Восстановить",
  "photo_restored": "Фото восстановлено",
  "upload_bag_photo": "Загрузить фото сумки",
  "replace_bag_photo": "Заменить",
  "remove_bag_photo": "Удалить",
  "bag_photo": "Фото сумки",
  "bag_photo_removed": "Фото сумки удалено",
  "bag_photo_replaced": "Фото сумки заменено"
```

- [ ] **Step 4: Run i18n-check**

```
/i18n-check
```

All three locales should be in sync.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/i18n/en.json frontend/src/i18n/he.json frontend/src/i18n/ru.json
git commit -m "feat: add i18n keys for photo delete, restore, and bag photo (en/he/ru)"
```

---

### Task 8: Frontend API client — extend types and add new functions

**Files:**
- Modify: `frontend/src/api/dolls.ts`
- Modify: `frontend/src/api/containers.ts`

- [ ] **Step 1: Extend `Photo` type and add photo API functions in dolls.ts**

In `frontend/src/api/dolls.ts`, replace the `Photo` interface:

```typescript
export interface Photo {
  id: number;
  doll_id: number | null;
  container_id: number | null;
  url: string;
  is_primary: boolean;
  created_at: string;
  created_by: string;
  deleted_at: string | null;
  deleted_by: string | null;
}
```

Then add these functions at the end of the file:

```typescript
export async function deletePhoto(photoId: number): Promise<void> {
  return apiRequest<void>(`/api/photos/${photoId}`, { method: 'DELETE' });
}

export async function restorePhoto(photoId: number): Promise<Photo> {
  return apiRequest<Photo>(`/api/photos/${photoId}/restore`, { method: 'POST' });
}

export async function listPhotos(
  dollId: number,
  opts?: { includeDeleted?: boolean }
): Promise<PhotosListResponse> {
  const params = opts?.includeDeleted ? '?include_deleted=true' : '';
  return apiRequest<PhotosListResponse>(`/api/dolls/${dollId}/photos${params}`);
}
```

- [ ] **Step 2: Extend `Container` type and add container photo functions in containers.ts**

In `frontend/src/api/containers.ts`, replace the `Container` interface:

```typescript
export interface Container {
  id: number;
  name: string;
  sort_order: number;
  is_active: boolean;
  is_system: boolean;
  created_at: string;
  updated_at: string;
  photo: ContainerPhoto | null;
}

export interface ContainerPhoto {
  id: number;
  container_id: number | null;
  url: string;
  is_primary: boolean;
  created_at: string;
  created_by: string;
  deleted_at: string | null;
  deleted_by: string | null;
}
```

Then add at the end:

```typescript
export async function uploadContainerPhoto(containerId: number, file: File): Promise<ContainerPhoto> {
  const formData = new FormData();
  formData.append('file', file);
  return apiRequest<ContainerPhoto>(`/api/containers/${containerId}/photo`, {
    method: 'POST',
    body: formData,
  });
}

export async function deleteContainerPhoto(containerId: number): Promise<void> {
  return apiRequest<void>(`/api/containers/${containerId}/photo`, { method: 'DELETE' });
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
docker compose -f docker/docker-compose.local.yml run --rm frontend npx tsc --noEmit
```

Expected: no errors (or only pre-existing errors unrelated to these files).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/dolls.ts frontend/src/api/containers.ts
git commit -m "feat: extend Photo/Container types and add delete/restore/container-photo API functions"
```

---

### Task 9: DollDetail — photo delete button, show-deleted toggle, restore

**Files:**
- Modify: `frontend/src/pages/DollDetail.tsx`

- [ ] **Step 1: Add imports**

At the top of `frontend/src/pages/DollDetail.tsx`, update the import from `../api/dolls` to include the new functions:

```typescript
import {
  getDoll,
  updateDoll,
  listPhotos,
  uploadPhoto,
  setPrimaryPhoto,
  deletePhoto,
  restorePhoto,
  Doll,
  Photo,
} from '../api/dolls';
```

Also add the `useMe` hook:

```typescript
import { useMe } from '../hooks/useMe';
```

- [ ] **Step 2: Add state for deleted photos toggle**

Inside the `DollDetail` component function, add after the existing state declarations:

```typescript
const { hasPerm } = useMe();
const [showDeleted, setShowDeleted] = useState(false);
```

- [ ] **Step 3: Update `loadPhotos` to use `listPhotos` with `includeDeleted` option**

Replace the existing `loadPhotos` function:

```typescript
const loadPhotos = async (includeDeleted = false) => {
  try {
    const data = await listPhotos(parseInt(id!, 10), { includeDeleted });
    setPhotos(data.photos);
  } catch (err: any) {
    console.error('Failed to load photos:', err);
  }
};
```

And in `useEffect`, update to pass `showDeleted`:

```typescript
useEffect(() => {
  if (id) {
    loadDoll();
    loadPhotos(showDeleted);
    loadContainers();
  }
}, [id]);
```

- [ ] **Step 4: Add delete handler**

```typescript
const handleDeletePhoto = async (photoId: number) => {
  if (!confirm(t('photo_delete_confirm'))) return;
  try {
    await deletePhoto(photoId);
    setToast({ message: t('photo_deleted'), type: 'success' });
    await loadPhotos(showDeleted);
  } catch (err: any) {
    if (err.status === 409) {
      setToast({ message: t('photo_delete_refused_primary'), type: 'error' });
    } else {
      setToast({ message: err.message || t('error_saving'), type: 'error' });
    }
  }
};
```

- [ ] **Step 5: Add restore handler**

```typescript
const handleRestorePhoto = async (photoId: number) => {
  try {
    await restorePhoto(photoId);
    setToast({ message: t('photo_restored'), type: 'success' });
    await loadPhotos(showDeleted);
  } catch (err: any) {
    setToast({ message: err.message || t('error_saving'), type: 'error' });
  }
};
```

- [ ] **Step 6: Add show-deleted toggle and wiring**

After `const handleSetPrimary` function, add a `useEffect` to reload when `showDeleted` changes:

```typescript
useEffect(() => {
  if (id) {
    loadPhotos(showDeleted);
  }
}, [showDeleted]);
```

- [ ] **Step 7: Update the photo gallery JSX**

In the `photo-section` div, after the `<h2>` and before the "Add Photo" button, add the toggle (admin only):

```tsx
{hasPerm('photo:restore') && (
  <label className="show-deleted-toggle">
    <input
      type="checkbox"
      checked={showDeleted}
      onChange={(e) => setShowDeleted(e.target.checked)}
    />
    {' '}{t('show_deleted_photos')}
  </label>
)}
```

In the photo gallery, replace the photo item rendering:

```tsx
{photos.map((photo) => (
  <div key={photo.id} className={`photo-item${photo.deleted_at ? ' photo-deleted' : ''}`}>
    <img src={getMediaUrl(photo.url)} alt="" style={photo.deleted_at ? { opacity: 0.4 } : undefined} />
    {photo.deleted_at ? (
      hasPerm('photo:restore') && (
        <button className="restore-photo-btn" onClick={() => handleRestorePhoto(photo.id)}>
          {t('restore')}
        </button>
      )
    ) : (
      <>
        {!photo.is_primary && (
          <button className="set-primary-btn" onClick={() => handleSetPrimary(photo.id)} disabled={saving}>
            {t('make_primary')}
          </button>
        )}
        {photo.is_primary && <div className="primary-badge">★</div>}
        {hasPerm('photo:delete') && (
          <button className="delete-photo-btn" onClick={() => handleDeletePhoto(photo.id)}>
            ✕
          </button>
        )}
      </>
    )}
  </div>
))}
```

- [ ] **Step 8: Rebuild stack and test**

```bash
docker compose -f docker/docker-compose.local.yml up -d --build
```

Open http://localhost:3000, navigate to a doll with photos:
1. Verify "✕" delete button appears on each photo (admin mode is the local default).
2. Click "✕" on a non-primary photo → confirm dialog → photo disappears.
3. Click "✕" on the primary photo when others exist → toast with `photo_delete_refused_primary`.
4. Enable "Show deleted photos" toggle → deleted photo reappears with gray overlay and "Restore" button.
5. Click "Restore" → photo reappears as live.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/pages/DollDetail.tsx
git commit -m "feat: add photo delete button, show-deleted toggle, and restore in DollDetail"
```

---

### Task 10: Admin — per-container photo management

**Files:**
- Modify: `frontend/src/pages/Admin.tsx`

- [ ] **Step 1: Add imports**

In `frontend/src/pages/Admin.tsx`, update the containers import:

```typescript
import {
  getContainers,
  createContainer,
  updateContainer,
  deleteContainer,
  uploadContainerPhoto,
  deleteContainerPhoto,
  Container,
} from '../api/containers';
```

Also add `useRef` to the React import (it's already imported via `useState, useEffect`, add `useRef`):

```typescript
import { useState, useEffect, useRef } from 'react';
```

- [ ] **Step 2: Add state for bag photo file input refs**

Inside the `Admin` component, add:

```typescript
const bagPhotoInputRefs = useRef<Map<number, HTMLInputElement>>(new Map());
```

- [ ] **Step 3: Add bag photo handlers**

```typescript
const handleUploadBagPhoto = async (containerId: number, file: File) => {
  try {
    await uploadContainerPhoto(containerId, file);
    setToast({ message: t('bag_photo_replaced'), type: 'success' });
    await loadContainers();
  } catch (err: any) {
    setToast({ message: err.message || t('upload_error'), type: 'error' });
  }
};

const handleRemoveBagPhoto = async (containerId: number) => {
  if (!confirm(t('photo_delete_confirm'))) return;
  try {
    await deleteContainerPhoto(containerId);
    setToast({ message: t('bag_photo_removed'), type: 'success' });
    await loadContainers();
  } catch (err: any) {
    setToast({ message: err.message || t('delete_error'), type: 'error' });
  }
};
```

- [ ] **Step 4: Add bag photo block in container list**

In the container list JSX, inside each `container-item` div, after the `container-actions` div, add (only for non-system containers and admins):

```tsx
{!container.is_system && hasPerm('photo:delete') && (
  <div className="container-photo-block">
    {container.photo ? (
      <>
        <img
          src={getMediaUrl(container.photo.url)}
          alt={container.name}
          style={{ width: 48, height: 48, objectFit: 'cover', borderRadius: 4 }}
        />
        <button
          className="btn-small btn-secondary"
          onClick={() => bagPhotoInputRefs.current.get(container.id)?.click()}
        >
          {t('replace_bag_photo')}
        </button>
        <button
          className="btn-small btn-danger"
          onClick={() => handleRemoveBagPhoto(container.id)}
        >
          {t('remove_bag_photo')}
        </button>
      </>
    ) : (
      <button
        className="btn-small btn-secondary"
        onClick={() => bagPhotoInputRefs.current.get(container.id)?.click()}
      >
        {t('upload_bag_photo')}
      </button>
    )}
    <input
      type="file"
      accept="image/*"
      style={{ display: 'none' }}
      ref={(el) => {
        if (el) bagPhotoInputRefs.current.set(container.id, el);
      }}
      onChange={(e) => {
        const file = e.target.files?.[0];
        if (file) handleUploadBagPhoto(container.id, file);
        e.target.value = '';
      }}
    />
  </div>
)}
```

- [ ] **Step 5: Test**

Open http://localhost:3000/admin:
1. Each non-system container row shows "Upload bag photo" button.
2. Click it → file picker opens → select an image → container shows 48×48 thumbnail + "Replace" + "Remove".
3. Click "Remove" → confirm → thumbnail disappears, "Upload bag photo" button returns.
4. System containers (Home, Wishlist) show no photo controls.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Admin.tsx
git commit -m "feat: add per-container bag photo management in Admin page"
```

---

### Task 11: DollsList — bag photo banner

**Files:**
- Modify: `frontend/src/pages/DollsList.tsx`

- [ ] **Step 1: Add state for container photo**

In `frontend/src/pages/DollsList.tsx`, add imports:

```typescript
import { getContainers, Container } from '../api/containers';
import { getMediaUrl } from '../api/client';
```

(If `getMediaUrl` is not already imported, add it.)

Inside the `DollsList` component, add:

```typescript
const [containerPhoto, setContainerPhoto] = useState<string | null>(null);
```

- [ ] **Step 2: Populate container photo when loading container scope**

In `loadDolls`, inside the `if (scope?.startsWith('container-'))` block, after setting `containerName`, add:

```typescript
        if (container && !container.is_system && container.photo) {
          setContainerPhoto(container.photo.url);
        } else {
          setContainerPhoto(null);
        }
```

Also set `setContainerPhoto(null)` in the other scope branches (home, bag, all) to clear it.

- [ ] **Step 3: Render banner in JSX**

In the component's return, after `<div className="page list-page">` and before `<div className="page-header">`, add:

```tsx
{containerPhoto && (
  <a href={getMediaUrl(containerPhoto)} target="_blank" rel="noopener noreferrer">
    <img
      src={getMediaUrl(containerPhoto)}
      alt={containerName}
      style={{
        width: '100%',
        height: 160,
        objectFit: 'cover',
        display: 'block',
      }}
    />
  </a>
)}
```

- [ ] **Step 4: Test**

1. Upload a bag photo in Admin for "Bag 1".
2. Open http://localhost:3000/list/container-{id} (find the ID from the URL when clicking the bag on the home screen).
3. Verify the banner appears above the page title.
4. Tap/click the banner → opens the full-size image in a new tab.
5. System containers and containers without a photo show no banner.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/DollsList.tsx
git commit -m "feat: show bag photo banner on container scope dolls list"
```

---

### Task 12: Manual verification checklist

Start the stack: `docker compose -f docker/docker-compose.local.yml up -d --build`

- [ ] **Edge case 1:** Upload 2 photos to a doll. Delete the non-primary one → succeeds (no confirmation needed beyond native confirm).
- [ ] **Edge case 2:** Try to delete the primary photo while 1 other live photo exists → toast `photo_delete_refused_primary`.
- [ ] **Edge case 3:** Delete the sole photo (the only one, even if primary) → succeeds. Doll has no photos.
- [ ] **Edge case 4:** Enable "Show deleted photos" toggle → deleted photo appears with gray overlay + "Restore". Click Restore → photo reappears live.
- [ ] **Edge case 5:** Upload 2 photos to a doll, delete both. Enable show-deleted. Restore one → it becomes the primary (doll had no live primary).
- [ ] **Edge case 6:** Navigate to Admin. Upload a bag photo to "Bag 1" → thumbnail appears.
- [ ] **Edge case 7:** Click "Replace" for the same bag → upload a new photo → thumbnail updates. Old photo is soft-deleted (not visible in Admin).
- [ ] **Edge case 8:** Click "Remove" for the bag photo → confirm → thumbnail disappears, "Upload bag photo" returns.
- [ ] **Edge case 9:** Home and Wishlist containers show no photo controls in Admin.
- [ ] **Edge case 10:** Navigate to the Bag 1 dolls list → banner appears at the top. Click it → opens full image.
- [ ] **Edge case 11:** Remove the Bag 1 photo from Admin → navigate back to Bag 1 list → no banner.
- [ ] **Edge case 12:** Switch language to Hebrew → all new keys display correctly. Switch to Russian → all new keys display correctly.

- [ ] **Commit**

```bash
git add .
git commit -m "feat: photo deletion, restore, and bag photos — complete implementation"
```
