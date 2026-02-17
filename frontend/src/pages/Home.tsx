import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LanguageSwitcher } from '../components/LanguageSwitcher';
import { SearchBox } from '../components/SearchBox';
import { getContainers, Container } from '../api/containers';
import { useMe } from '../hooks/useMe';

export function Home() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { hasAnyPerm } = useMe();
  const [searchQuery, setSearchQuery] = useState('');
  const [containers, setContainers] = useState<Container[]>([]);
  const [loading, setLoading] = useState(true);

  // Load containers on mount
  useEffect(() => {
    loadContainers();
  }, []);

  const loadContainers = async () => {
    try {
      const response = await getContainers();
      setContainers(response.items);
    } catch (err) {
      console.error('Failed to load containers:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleContainerClick = (containerId: number) => {
    navigate(`/list/container-${containerId}`);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/list/all?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  const showAdmin = hasAnyPerm('doll:create', 'doll:rename', 'event:read');

  return (
    <div className="page home-page">
      <div className="home-header">
        <h1 className="app-title">{t('app_title')}</h1>
        <div className="home-header-actions">
          <LanguageSwitcher />
          {showAdmin && (
            <button className="admin-link-btn" onClick={() => navigate('/admin')}>
              ⚙️ {t('admin')}
            </button>
          )}
        </div>
      </div>

      <SearchBox
        value={searchQuery}
        onChange={setSearchQuery}
        onSubmit={handleSearch}
        showButton={true}
      />

      {loading ? (
        <div className="loading">{t('loading')}</div>
      ) : (
        <div className="location-buttons">
          {containers.map((container) => {
            // Determine icon and style based on container name
            let icon = '📦';
            let btnClass = 'location-btn';

            if (container.name === 'Home') {
              icon = '🏠';
              btnClass = 'location-btn location-btn-home';
            } else if (container.name === 'Wishlist') {
              icon = '⭐';
              btnClass = 'location-btn location-btn-wishlist';
            } else if (container.name.startsWith('Bag')) {
              icon = '👜';
              btnClass = 'location-btn location-btn-bag';
            }

            return (
              <button
                key={container.id}
                className={btnClass}
                onClick={() => handleContainerClick(container.id)}
              >
                <span className="location-icon">{icon}</span>
                <span className="location-label">{container.name}</span>
              </button>
            );
          })}

          <button
            className="location-btn location-btn-all"
            onClick={() => navigate('/list/all')}
          >
            <span className="location-icon">✨</span>
            <span className="location-label">{t('all')}</span>
          </button>
        </div>
      )}
    </div>
  );
}

