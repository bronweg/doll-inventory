import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useMe } from '../hooks/useMe';
import { getDolls, createDoll, renameDoll, getDollEvents, deleteDoll, Doll, Event, DollCreateData } from '../api/dolls';
import { getContainers, createContainer, updateContainer, deleteContainer, Container } from '../api/containers';
import { getMediaUrl } from '../api/client';
import { Toast } from '../components/Toast';

export function Admin() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { hasPerm } = useMe();

  const [dolls, setDolls] = useState<Doll[]>([]);
  const [containers, setContainers] = useState<Container[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Create doll form state
  const [newDollName, setNewDollName] = useState('');
  const [newDollContainerId, setNewDollContainerId] = useState<number | null>(null);
  const [newDollPurchaseUrl, setNewDollPurchaseUrl] = useState('');
  const [creating, setCreating] = useState(false);

  // Container management state
  const [newContainerName, setNewContainerName] = useState('');
  const [creatingContainer, setCreatingContainer] = useState(false);
  const [editingContainerId, setEditingContainerId] = useState<number | null>(null);
  const [editContainerName, setEditContainerName] = useState('');

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
    loadContainers();
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

  const loadContainers = async () => {
    try {
      const response = await getContainers();
      setContainers(response.items);
      // Set default container to Home if available
      if (response.items.length > 0 && !newDollContainerId) {
        const homeContainer = response.items.find(c => c.name === 'Home');
        if (homeContainer) {
          setNewDollContainerId(homeContainer.id);
        } else {
          setNewDollContainerId(response.items[0].id);
        }
      }
    } catch (err: any) {
      console.error('Failed to load containers:', err);
    }
  };

  const handleCreateDoll = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDollName.trim()) {
      setToast({ message: t('name_required'), type: 'error' });
      return;
    }
    if (!newDollContainerId) {
      setToast({ message: t('container_required') || 'Please select a container', type: 'error' });
      return;
    }

    setCreating(true);
    try {
      const data: DollCreateData = {
        name: newDollName.trim(),
        container_id: newDollContainerId,
        purchase_url: newDollPurchaseUrl.trim() || null,
      };
      await createDoll(data);
      setToast({ message: t('doll_created'), type: 'success' });
      setNewDollName('');
      setNewDollPurchaseUrl('');
      // Keep container_id as is for next creation
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

  // Container management functions
  const handleCreateContainer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContainerName.trim()) {
      setToast({ message: t('name_required'), type: 'error' });
      return;
    }

    setCreatingContainer(true);
    try {
      await createContainer({ name: newContainerName.trim() });
      setToast({ message: t('container_created') || 'Container created', type: 'success' });
      setNewContainerName('');
      await loadContainers();
    } catch (err: any) {
      setToast({ message: err.message || t('error_creating'), type: 'error' });
    } finally {
      setCreatingContainer(false);
    }
  };

  const handleRenameContainer = async (containerId: number, newName: string) => {
    if (!newName.trim()) {
      setToast({ message: t('name_required'), type: 'error' });
      return;
    }

    try {
      await updateContainer(containerId, { name: newName.trim() });
      setToast({ message: t('container_renamed') || 'Container renamed', type: 'success' });
      setEditingContainerId(null);
      await loadContainers();
    } catch (err: any) {
      setToast({ message: err.message || t('error_renaming'), type: 'error' });
    }
  };

  const handleMoveContainer = async (containerId: number, direction: 'up' | 'down') => {
    const currentIndex = containers.findIndex(c => c.id === containerId);
    if (currentIndex === -1) return;

    const targetIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
    if (targetIndex < 0 || targetIndex >= containers.length) return;

    const currentContainer = containers[currentIndex];
    const targetContainer = containers[targetIndex];

    try {
      // Swap sort_order values
      await updateContainer(currentContainer.id, { sort_order: targetContainer.sort_order });
      await updateContainer(targetContainer.id, { sort_order: currentContainer.sort_order });
      await loadContainers();
    } catch (err: any) {
      setToast({ message: err.message || t('error_saving'), type: 'error' });
    }
  };

  const handleDeleteContainer = async (containerId: number) => {
    const container = containers.find(c => c.id === containerId);
    if (!container) return;

    if (container.is_system) {
      setToast({ message: t('cannot_delete_system_container') || 'Cannot delete system container', type: 'error' });
      return;
    }

    if (!confirm(t('confirm_delete_container', { name: container.name }) || `Delete container "${container.name}"?`)) {
      return;
    }

    try {
      await deleteContainer(containerId);
      setToast({ message: t('container_deleted') || 'Container deleted', type: 'success' });
      await loadContainers();
    } catch (err: any) {
      setToast({ message: err.message || t('delete_error'), type: 'error' });
    }
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
              <label htmlFor="container">{t('container') || 'Container'}</label>
              <select
                id="container"
                className="form-select"
                value={newDollContainerId || ''}
                onChange={(e) => setNewDollContainerId(parseInt(e.target.value, 10))}
                disabled={creating}
              >
                {containers.map((container) => (
                  <option key={container.id} value={container.id}>
                    {container.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="purchase-url">{t('purchase_url') || 'Purchase URL (optional)'}</label>
              <input
                id="purchase-url"
                type="url"
                className="form-input"
                value={newDollPurchaseUrl}
                onChange={(e) => setNewDollPurchaseUrl(e.target.value)}
                placeholder="https://..."
                disabled={creating}
              />
            </div>

            <button type="submit" className="btn-primary" disabled={creating}>
              {creating ? t('creating') : t('create_doll')}
            </button>
          </form>
        </div>
      )}

      {/* Container Management Section */}
      {hasPerm('container:manage') && (
        <div className="admin-section">
          <h2 className="section-title">{t('manage_containers') || 'Manage Containers'}</h2>

          {/* Create Container Form */}
          <form className="create-container-form" onSubmit={handleCreateContainer}>
            <div className="form-group-inline">
              <input
                type="text"
                className="form-input"
                value={newContainerName}
                onChange={(e) => setNewContainerName(e.target.value)}
                placeholder={t('new_container_name') || 'New container name'}
                disabled={creatingContainer}
              />
              <button type="submit" className="btn-primary" disabled={creatingContainer}>
                {creatingContainer ? t('creating') : t('create_container') || 'Create'}
              </button>
            </div>
          </form>

          {/* Container List */}
          <div className="containers-list">
            {containers.map((container, index) => (
              <div key={container.id} className="container-item">
                <div className="container-info">
                  {editingContainerId === container.id ? (
                    <input
                      type="text"
                      className="form-input"
                      value={editContainerName}
                      onChange={(e) => setEditContainerName(e.target.value)}
                      onBlur={() => {
                        if (editContainerName.trim() && editContainerName !== container.name) {
                          handleRenameContainer(container.id, editContainerName);
                        } else {
                          setEditingContainerId(null);
                        }
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          if (editContainerName.trim() && editContainerName !== container.name) {
                            handleRenameContainer(container.id, editContainerName);
                          } else {
                            setEditingContainerId(null);
                          }
                        } else if (e.key === 'Escape') {
                          setEditingContainerId(null);
                        }
                      }}
                      autoFocus
                    />
                  ) : (
                    <span className="container-name">
                      {container.name}
                      {container.is_system && <span className="system-badge"> (System)</span>}
                    </span>
                  )}
                </div>

                <div className="container-actions">
                  {/* Move Up/Down */}
                  <button
                    className="btn-icon"
                    onClick={() => handleMoveContainer(container.id, 'up')}
                    disabled={index === 0}
                    title={t('move_up') || 'Move up'}
                  >
                    ↑
                  </button>
                  <button
                    className="btn-icon"
                    onClick={() => handleMoveContainer(container.id, 'down')}
                    disabled={index === containers.length - 1}
                    title={t('move_down') || 'Move down'}
                  >
                    ↓
                  </button>

                  {/* Rename */}
                  {!container.is_system && (
                    <button
                      className="btn-icon"
                      onClick={() => {
                        setEditingContainerId(container.id);
                        setEditContainerName(container.name);
                      }}
                      title={t('rename') || 'Rename'}
                    >
                      ✏️
                    </button>
                  )}

                  {/* Delete */}
                  {!container.is_system && (
                    <button
                      className="btn-icon btn-danger"
                      onClick={() => handleDeleteContainer(container.id)}
                      title={t('delete') || 'Delete'}
                    >
                      🗑️
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
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