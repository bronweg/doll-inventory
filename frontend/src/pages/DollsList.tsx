import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { getDolls, Doll } from '../api/dolls';
import { DollCard } from '../components/DollCard';
import { Toast } from '../components/Toast';

export function DollsList() {
  const { scope } = useParams<{ scope: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const [dolls, setDolls] = useState<Doll[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadDolls();
  }, [scope]);

  const loadDolls = async () => {
    setLoading(true);
    setError(null);

    try {
      const params: any = { limit: 100 };

      if (scope === 'home') {
        params.location = 'HOME';
      } else if (scope?.startsWith('bag-')) {
        const bagNum = parseInt(scope.split('-')[1], 10);
        params.location = 'BAG';
        params.bag = bagNum;
      }
      // 'all' scope has no filters

      const response = await getDolls(params);
      setDolls(response.items);
    } catch (err: any) {
      setError(err.message || t('error_loading'));
    } finally {
      setLoading(false);
    }
  };

  const filteredDolls = dolls.filter((doll) =>
    doll.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getTitle = () => {
    if (scope === 'home') return t('location_home');
    if (scope === 'all') return t('all');
    if (scope?.startsWith('bag-')) {
      const bagNum = parseInt(scope.split('-')[1], 10);
      return t('location_bag', { number: bagNum });
    }
    return t('all');
  };

  return (
    <div className="page list-page">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate('/')}>
          ← {t('back')}
        </button>
        <h1 className="page-title">{getTitle()}</h1>
      </div>

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

      {error && (
        <Toast
          message={error}
          type="error"
          onClose={() => setError(null)}
        />
      )}

      {!loading && filteredDolls.length === 0 && (
        <div className="no-results">{t('no_dolls')}</div>
      )}

      {!loading && filteredDolls.length > 0 && (
        <div className="dolls-grid">
          {filteredDolls.map((doll) => (
            <DollCard
              key={doll.id}
              doll={doll}
              onClick={() => navigate(`/doll/${doll.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

