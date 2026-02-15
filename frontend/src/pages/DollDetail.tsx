import { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  getDoll,
  updateDoll,
  getPhotos,
  uploadPhoto,
  setPrimaryPhoto,
  Doll,
  Photo,
} from '../api/dolls';
import { getMediaUrl, BAGS_COUNT } from '../api/client';
import { Toast } from '../components/Toast';

export function DollDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [doll, setDoll] = useState<Doll | null>(null);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    if (id) {
      loadDoll();
      loadPhotos();
    }
  }, [id]);

  const loadDoll = async () => {
    setLoading(true);
    try {
      const data = await getDoll(parseInt(id!, 10));
      setDoll(data);
    } catch (err: any) {
      setToast({ message: err.message || t('error_loading'), type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const loadPhotos = async () => {
    try {
      const data = await getPhotos(parseInt(id!, 10));
      setPhotos(data.photos);
    } catch (err: any) {
      // Silent fail for photos
      console.error('Failed to load photos:', err);
    }
  };

  const handleMove = async (location: 'HOME' | 'BAG', bagNumber: number | null) => {
    if (!doll) return;

    setSaving(true);
    try {
      const updated = await updateDoll(doll.id, {
        location,
        bag_number: bagNumber,
      });
      setDoll(updated);
      setToast({ message: t('move_success'), type: 'success' });
    } catch (err: any) {
      setToast({ message: err.message || t('move_error'), type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !doll) return;

    setUploading(true);
    try {
      await uploadPhoto(doll.id, file, true);
      setToast({ message: t('upload_success'), type: 'success' });
      await loadDoll();
      await loadPhotos();
    } catch (err: any) {
      setToast({ message: err.message || t('upload_error'), type: 'error' });
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleSetPrimary = async (photoId: number) => {
    setSaving(true);
    try {
      await setPrimaryPhoto(photoId);
      setToast({ message: t('primary_set'), type: 'success' });
      await loadDoll();
      await loadPhotos();
    } catch (err: any) {
      setToast({ message: err.message || t('error_saving'), type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="page detail-page">
        <div className="loading">{t('loading')}</div>
      </div>
    );
  }

  if (!doll) {
    return (
      <div className="page detail-page">
        <div className="error">{t('error_loading')}</div>
      </div>
    );
  }

  const primaryPhotoUrl = doll.primary_photo_url ? getMediaUrl(doll.primary_photo_url) : null;
  const currentLocation =
    doll.location === 'HOME'
      ? t('location_home')
      : t('location_bag', { number: doll.bag_number });

  return (
    <div className="page detail-page">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate(-1)}>
          ← {t('back')}
        </button>
      </div>

      <div className="doll-detail">
        <div className="doll-photo-large">
          {primaryPhotoUrl ? (
            <img src={primaryPhotoUrl} alt={doll.name} />
          ) : (
            <div className="doll-photo-placeholder">
              <span>📷</span>
            </div>
          )}
        </div>


      <div className="move-section">
        <h2 className="section-title">{t('move_to')}</h2>
        <div className="move-buttons">
          <button
            className="move-btn move-btn-home"
            onClick={() => handleMove('HOME', null)}
            disabled={saving || (doll.location === 'HOME')}
          >
            <span className="move-icon">🏠</span>
            <span className="move-label">{t('home')}</span>
          </button>

          {Array.from({ length: BAGS_COUNT }, (_, i) => i + 1).map((num) => (
            <button
              key={num}
              className="move-btn move-btn-bag"
              onClick={() => handleMove('BAG', num)}
              disabled={saving || (doll.location === 'BAG' && doll.bag_number === num)}
            >
              <span className="move-icon">👜</span>
              <span className="move-label">{t('bag', { number: num })}</span>
            </button>
          ))}
        </div>
        {saving && <div className="saving-indicator">{t('saving')}</div>}
      </div>

      <div className="photo-section">
        <h2 className="section-title">{t('photos')}</h2>

        <button
          className="add-photo-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? t('saving') : t('add_photo')}
        </button>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          style={{ display: 'none' }}
          onChange={handleFileSelect}
        />

        {photos.length === 0 && (
          <div className="no-photos">{t('no_photos')}</div>
        )}

        {photos.length > 0 && (
          <div className="photo-gallery">
            {photos.map((photo) => (
              <div key={photo.id} className="photo-item">
                <img src={getMediaUrl(photo.url)} alt="" />
                {!photo.is_primary && (
                  <button
                    className="set-primary-btn"
                    onClick={() => handleSetPrimary(photo.id)}
                    disabled={saving}
                  >
                    {t('make_primary')}
                  </button>
                )}
                {photo.is_primary && (
                  <div className="primary-badge">★</div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}

