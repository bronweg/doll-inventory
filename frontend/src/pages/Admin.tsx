import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useMe } from '../hooks/useMe';
import { getDolls, createDoll, renameDoll, getDollEvents, deleteDoll, Doll, Event, DollCreateData } from '../api/dolls';
import { getMediaUrl, BAGS_COUNT } from '../api/client';
import { Toast } from '../components/Toast';

export function Admin() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { hasPerm } = useMe();

  const [dolls, setDolls] = useState<Doll[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Create doll form state
  const [newDollName, setNewDollName] = useState('');
  const [newDollLocation, setNewDollLocation] = useState<'HOME' | 'BAG'>('HOME');
  const [newDollBag, setNewDollBag] = useState<number>(1);
  const [creating, setCreating] = useState(false);

  // Events state
  const [selectedDollId, setSelectedDollId] = useState<number | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [loadingEvents, setLoadingEvents] = useState(false);

  // Rename state
  const [renamingDollId, setRenamingDollId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState('');

  // Delete confirmation state
  const [deletingDollId, setDeletingDollId] = useState<number | null>(null);
  const [deleteConfirmName, setDeleteConfirmName] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    loadDolls();
  }, []);

  const loadDolls = async () => {
    setLoading(true);
    try {
      const response = await getDolls({ limit: 200 });
      setDolls(response.items);
    } catch (err: any) {
      setToast({ message: err.message || t('error_loading'), type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDoll = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDollName.trim()) {
      setToast({ message: t('name_required'), type: 'error' });
      return;
    }

    setCreating(true);
    try {
      const data: DollCreateData = {
        name: newDollName.trim(),
        location: newDollLocation,
        bag_number: newDollLocation === 'BAG' ? newDollBag : null,
      };
      await createDoll(data);
      setToast({ message: t('doll_created'), type: 'success' });
      setNewDollName('');
      setNewDollLocation('HOME');
      setNewDollBag(1);
      await loadDolls();
    } catch (err: any) {
      setToast({ message: err.message || t('error_creating'), type: 'error' });
    } finally {
      setCreating(false);
    }
  };

  const handleRename = async (dollId: number, newName: string) => {
    if (!newName.trim()) {
      setToast({ message: t('name_required'), type: 'error' });
      return;
    }

    try {
      await renameDoll(dollId, newName.trim());
      setToast({ message: t('doll_renamed'), type: 'success' });
      setRenamingDollId(null);
      await loadDolls();
    } catch (err: any) {
      setToast({ message: err.message || t('error_renaming'), type: 'error' });
    }
  };

  const handleDelete = async (dollId: number, dollName: string) => {
    // Validate confirmation
    if (deleteConfirmName.trim() !== dollName) {
      setToast({ message: t('name_required'), type: 'error' });
      return;
    }

    setIsDeleting(true);
    try {
      await deleteDoll(dollId);
      setToast({ message: t('delete_success'), type: 'success' });
      setDeletingDollId(null);
      setDeleteConfirmName('');
      await loadDolls();
    } catch (err: any) {
      // Handle 404 gracefully (doll already deleted)
      if (err.status === 404) {
        setToast({ message: t('delete_already_deleted'), type: 'info' });
        setDeletingDollId(null);
        setDeleteConfirmName('');
        await loadDolls();
      } else {
        setToast({ message: err.message || t('delete_error'), type: 'error' });
      }
    } finally {
      setIsDeleting(false);
    }
  };

  const loadEvents = async (dollId: number) => {
    setLoadingEvents(true);
    try {
      const response = await getDollEvents(dollId, { limit: 50 });
      setEvents(response.items);
    } catch (err: any) {
      setToast({ message: err.message || t('error_loading_events'), type: 'error' });
    } finally {
      setLoadingEvents(false);
    }
  };

  const handleDollSelect = (dollId: number) => {
    setSelectedDollId(dollId);
    loadEvents(dollId);
  };

  const filteredDolls = dolls.filter((doll) =>
    doll.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatEventPayload = (event: Event): string => {
    try {
      const payload = JSON.parse(event.payload);
      if (event.event_type === 'DOLL_RENAMED') {
        return `${payload.old_name} → ${payload.new_name}`;
      } else if (event.event_type === 'DOLL_MOVED') {
        const oldLoc = payload.old_location === 'HOME' ? t('location_home') : t('location_bag', { number: payload.old_bag_number });
        const newLoc = payload.new_location === 'HOME' ? t('location_home') : t('location_bag', { number: payload.new_bag_number });
        return `${oldLoc} → ${newLoc}`;
      } else if (event.event_type === 'PHOTO_ADDED') {
        return t('photo_added');
      } else if (event.event_type === 'PHOTO_SET_PRIMARY') {
        return t('photo_set_primary');
      } else if (event.event_type === 'DOLL_CREATED') {
        return `${payload.name} (${payload.location})`;
      }
      return '';
    } catch {
      return '';
    }
  };

  return (
    <div className="page admin-page">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate('/')}>
          ← {t('back')}
        </button>
        <h1 className="page-title">{t('admin')}</h1>
      </div>




      {/* Create Doll Section */}
      {hasPerm('doll:create') && (
        <div className="admin-section">
          <h2 className="section-title">{t('create_doll')}</h2>
          <form className="create-doll-form" onSubmit={handleCreateDoll}>
            <div className="form-group">
              <label htmlFor="doll-name">{t('doll_name')}</label>
              <input
                id="doll-name"
                type="text"
                className="form-input"
                value={newDollName}
                onChange={(e) => setNewDollName(e.target.value)}
                placeholder={t('enter_doll_name')}
                disabled={creating}
              />
            </div>

            <div className="form-group">
              <label>{t('location')}</label>
              <div className="radio-group">
                <label className="radio-label">
                  <input
                    type="radio"
                    name="location"
                    value="HOME"
                    checked={newDollLocation === 'HOME'}
                    onChange={() => setNewDollLocation('HOME')}
                    disabled={creating}
                  />
                  <span>{t('location_home')}</span>
                </label>
                <label className="radio-label">
                  <input
                    type="radio"
                    name="location"
                    value="BAG"
                    checked={newDollLocation === 'BAG'}
                    onChange={() => setNewDollLocation('BAG')}
                    disabled={creating}
                  />
                  <span>{t('location_bag_generic')}</span>
                </label>
              </div>
            </div>

            {newDollLocation === 'BAG' && (
              <div className="form-group">
                <label htmlFor="bag-number">{t('bag_number')}</label>
                <select
                  id="bag-number"
                  className="form-select"
                  value={newDollBag}
                  onChange={(e) => setNewDollBag(parseInt(e.target.value, 10))}
                  disabled={creating}
                >
                  {Array.from({ length: BAGS_COUNT }, (_, i) => i + 1).map((num) => (
                    <option key={num} value={num}>
                      {t('bag', { number: num })}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <button type="submit" className="btn-primary" disabled={creating}>
              {creating ? t('creating') : t('create_doll')}
            </button>
          </form>
        </div>
      )}

      {/* Manage Dolls Section */}
      {(hasPerm('doll:create') || hasPerm('doll:rename')) && (
        <div className="admin-section">
          <h2 className="section-title">{t('manage_dolls')}</h2>

          <div className="search-box">
            <input
              type="text"
              className="search-input"
              placeholder={t('search')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {loading && <div className="loading">{t('loading')}</div>}

          {!loading && filteredDolls.length === 0 && (
            <div className="no-results">{t('no_dolls')}</div>
          )}

          {!loading && filteredDolls.length > 0 && (
            <div className="admin-dolls-list">
              {filteredDolls.map((doll) => (
                <div key={doll.id} className="admin-doll-item">
                  <div className="admin-doll-photo">
                    {doll.primary_photo_url ? (
                      <img src={getMediaUrl(doll.primary_photo_url)} alt={doll.name} />
                    ) : (
                      <div className="admin-doll-photo-placeholder">📷</div>
                    )}
                  </div>

                  <div className="admin-doll-info">
                    {renamingDollId === doll.id && hasPerm('doll:rename') ? (
                      <div className="rename-form">
                        <input
                          type="text"
                          className="rename-input"
                          value={renameValue}
                          onChange={(e) => setRenameValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              handleRename(doll.id, renameValue);
                            } else if (e.key === 'Escape') {
                              setRenamingDollId(null);
                            }
                          }}
                          autoFocus
                        />
                        <button
                          className="btn-small btn-primary"
                          onClick={() => handleRename(doll.id, renameValue)}
                        >
                          {t('save')}
                        </button>
                        <button
                          className="btn-small btn-secondary"
                          onClick={() => setRenamingDollId(null)}
                        >
                          {t('cancel')}
                        </button>
                      </div>
                    ) : (
                      <div className="admin-doll-name">
                        <span>{doll.name}</span>
                        {hasPerm('doll:rename') && (
                          <button
                            className="btn-icon"
                            onClick={() => {
                              setRenamingDollId(doll.id);
                              setRenameValue(doll.name);
                            }}
                            title={t('rename')}
                          >
                            ✏️
                          </button>
                        )}
                      </div>
                    )}

                    <div className="admin-doll-location">
                      {doll.location === 'HOME'
                        ? t('location_home')
                        : t('location_bag', { number: doll.bag_number })}
                    </div>
                  </div>

                  <div className="admin-doll-actions">
                    <button
                      className="btn-secondary"
                      onClick={() => navigate(`/doll/${doll.id}`)}
                    >
                      {t('view_details')}
                    </button>

                    {hasPerm('doll:delete') && (
                      <button
                        className="btn-danger"
                        onClick={() => {
                          setDeletingDollId(doll.id);
                          setDeleteConfirmName('');
                        }}
                      >
                        {t('delete')}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deletingDollId !== null && (
        <div className="modal-overlay" onClick={() => setDeletingDollId(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>{t('delete_confirm_title')}</h3>
            <p>{t('delete_confirm_text')}</p>

            {(() => {
              const doll = dolls.find(d => d.id === deletingDollId);
              if (!doll) return null;

              return (
                <>
                  <input
                    type="text"
                    className="modal-input"
                    placeholder={t('delete_confirm_placeholder')}
                    value={deleteConfirmName}
                    onChange={(e) => setDeleteConfirmName(e.target.value)}
                    autoFocus
                    disabled={isDeleting}
                  />

                  <div className="modal-actions">
                    <button
                      className="btn-danger"
                      onClick={() => handleDelete(doll.id, doll.name)}
                      disabled={deleteConfirmName.trim() !== doll.name || isDeleting}
                    >
                      {isDeleting ? t('deleting') : t('delete_confirm_action')}
                    </button>
                    <button
                      className="btn-secondary"
                      onClick={() => {
                        setDeletingDollId(null);
                        setDeleteConfirmName('');
                      }}
                      disabled={isDeleting}
                    >
                      {t('cancel')}
                    </button>
                  </div>
                </>
              );
            })()}
          </div>
        </div>
      )}


      {/* Recent Events Section */}
      {hasPerm('event:read') && (
        <div className="admin-section">
          <h2 className="section-title">{t('recent_events')}</h2>

          <div className="form-group">
            <label htmlFor="event-doll-select">{t('select_doll')}</label>
            <select
              id="event-doll-select"
              className="form-select"
              value={selectedDollId || ''}
              onChange={(e) => {
                const dollId = parseInt(e.target.value, 10);
                if (dollId) {
                  handleDollSelect(dollId);
                } else {
                  setSelectedDollId(null);
                  setEvents([]);
                }
              }}
            >
              <option value="">{t('select_doll')}</option>
              {dolls.map((doll) => (
                <option key={doll.id} value={doll.id}>
                  {doll.name}
                </option>
              ))}
            </select>
          </div>

          {loadingEvents && <div className="loading">{t('loading')}</div>}

          {!loadingEvents && selectedDollId && events.length === 0 && (
            <div className="no-results">{t('no_events')}</div>
          )}

          {!loadingEvents && events.length > 0 && (
            <div className="events-list">
              {events.map((event) => (
                <div key={event.id} className="event-item">
                  <div className="event-type">{event.event_type}</div>
                  <div className="event-details">{formatEventPayload(event)}</div>
                  <div className="event-meta">
                    <span className="event-user">{event.created_by}</span>
                    <span className="event-time">
                      {new Date(event.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

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