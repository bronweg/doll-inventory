import { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { getDolls, Doll } from '../api/dolls';
import { getContainers } from '../api/containers';
import { DollCard } from '../components/DollCard';
import { SearchBox } from '../components/SearchBox';
import { Toast } from '../components/Toast';

export function DollsList() {
  const { scope } = useParams<{ scope: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();

  const [dolls, setDolls] = useState<Doll[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState(searchParams.get('q') || '');
  const [containerName, setContainerName] = useState<string>('');
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Sync search query from URL params
  useEffect(() => {
    const q = searchParams.get('q') || '';
    setSearchQuery(q);
  }, [searchParams]);

  // Load dolls when scope or search params change
  useEffect(() => {
    loadDolls();
  }, [scope, searchParams]);

  const loadDolls = async () => {
    setLoading(true);
    setError(null);

    try {
      const params: any = { limit: 200 };

      // Add filters based on scope
      if (scope?.startsWith('container-')) {
        // New container-based routing
        const containerId = parseInt(scope.split('-')[1], 10);
        params.container_id = containerId;

        // Fetch container name for display
        try {
          const containersResponse = await getContainers();
          const container = containersResponse.items.find(c => c.id === containerId);
          if (container) {
            setContainerName(container.name);
          }
        } catch (err) {
          console.error('Failed to fetch container name:', err);
        }
      } else if (scope === 'home') {
        // Legacy: map to HOME location
        params.location = 'HOME';
        setContainerName('Home');
      } else if (scope?.startsWith('bag-')) {
        // Legacy: map to BAG location
        const bagNum = parseInt(scope.split('-')[1], 10);
        params.location = 'BAG';
        params.bag = bagNum;
        setContainerName(`Bag ${bagNum}`);
      } else {
        // 'all' scope has no filters
        setContainerName('');
      }

      // Add search query if present
      const q = searchParams.get('q');
      if (q && q.trim()) {
        params.q = q.trim();
      }

      const response = await getDolls(params);
      setDolls(response.items);
    } catch (err: any) {
      setError(err.message || t('error_loading'));
    } finally {
      setLoading(false);
    }
  };

  // Handle search input change with debouncing
  const handleSearchChange = (value: string) => {
    setSearchQuery(value);

    // Clear existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Set new timer to update URL params after 300ms
    debounceTimerRef.current = setTimeout(() => {
      const newParams = new URLSearchParams(searchParams);
      if (value.trim()) {
        newParams.set('q', value.trim());
      } else {
        newParams.delete('q');
      }
      setSearchParams(newParams);
    }, 300);
  };

  // Clear search
  const handleClearSearch = () => {
    setSearchQuery('');
    const newParams = new URLSearchParams(searchParams);
    newParams.delete('q');
    setSearchParams(newParams);
  };

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  const getTitle = () => {
    if (scope?.startsWith('container-')) {
      return containerName || t('loading');
    }
    if (scope === 'home') return t('location_home');
    if (scope === 'all') return t('all');
    if (scope?.startsWith('bag-')) {
      const bagNum = parseInt(scope.split('-')[1], 10);
      return t('location_bag', { number: bagNum });
    }
    return t('all');
  };

  // Get location/container params for suggestions
  const getScopeParams = () => {
    if (scope?.startsWith('container-')) {
      const containerId = parseInt(scope.split('-')[1], 10);
      return { container_id: containerId };
    }
    if (scope === 'home') return { location: 'HOME' as const };
    if (scope?.startsWith('bag-')) {
      const bagNum = parseInt(scope.split('-')[1], 10);
      return { location: 'BAG' as const, bag: bagNum };
    }
    return {};
  };

  return (
    <div className="page list-page">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate('/')}>
          ← {t('back')}
        </button>
        <h1 className="page-title">{getTitle()}</h1>
      </div>

      <SearchBox
        value={searchQuery}
        onChange={handleSearchChange}
        onClear={handleClearSearch}
        {...getScopeParams()}
      />

      {loading && <div className="loading">{t('loading')}</div>}

      {error && (
        <Toast
          message={error}
          type="error"
          onClose={() => setError(null)}
        />
      )}

      {!loading && dolls.length === 0 && (
        <div className="no-results">{t('no_dolls')}</div>
      )}

      {!loading && dolls.length > 0 && (
        <div className="dolls-grid">
          {dolls.map((doll) => (
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

