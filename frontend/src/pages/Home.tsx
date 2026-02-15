import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LanguageSwitcher } from '../components/LanguageSwitcher';
import { BAGS_COUNT } from '../api/client';
import { useMe } from '../hooks/useMe';

export function Home() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { hasAnyPerm } = useMe();
  const [searchQuery, setSearchQuery] = useState('');

  const handleLocationClick = (scope: string) => {
    navigate(`/list/${scope}`);
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

      <form className="home-search-form" onSubmit={handleSearch}>
        <input
          type="text"
          className="home-search-input"
          placeholder={t('search_placeholder')}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <button type="submit" className="home-search-btn" disabled={!searchQuery.trim()}>
          🔍 {t('search_button')}
        </button>
      </form>

      <div className="location-buttons">
        <button
          className="location-btn location-btn-home"
          onClick={() => handleLocationClick('home')}
        >
          <span className="location-icon">🏠</span>
          <span className="location-label">{t('home')}</span>
        </button>

        {Array.from({ length: BAGS_COUNT }, (_, i) => i + 1).map((num) => (
          <button
            key={num}
            className="location-btn location-btn-bag"
            onClick={() => handleLocationClick(`bag-${num}`)}
          >
            <span className="location-icon">👜</span>
            <span className="location-label">{t('bag', { number: num })}</span>
          </button>
        ))}

        <button
          className="location-btn location-btn-all"
          onClick={() => handleLocationClick('all')}
        >
          <span className="location-icon">✨</span>
          <span className="location-label">{t('all')}</span>
        </button>
      </div>
    </div>
  );
}

