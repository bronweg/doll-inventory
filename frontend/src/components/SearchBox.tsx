import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { getSuggestions, SuggestionItem } from '../api/dolls';
import { getMediaUrl } from '../api/client';

interface SearchBoxProps {
  value: string;
  onChange: (value: string) => void;
  onClear?: () => void;
  onSubmit?: (e: React.FormEvent) => void;
  placeholder?: string;
  showButton?: boolean;
  location?: 'HOME' | 'BAG';
  bag?: number;
  className?: string;
}

export function SearchBox({
  value,
  onChange,
  onClear,
  onSubmit,
  placeholder,
  showButton = false,
  location,
  bag,
  className = '',
}: SearchBoxProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loading, setLoading] = useState(false);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Fetch suggestions when value changes
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    if (!value.trim()) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    setLoading(true);
    debounceTimerRef.current = setTimeout(async () => {
      try {
        const params: any = { q: value.trim(), limit: 10 };
        if (location) params.location = location;
        if (bag !== undefined) params.bag = bag;

        const response = await getSuggestions(params);
        setSuggestions(response.suggestions);
        setShowSuggestions(true);
      } catch (error) {
        console.error('Failed to fetch suggestions:', error);
        setSuggestions([]);
      } finally {
        setLoading(false);
      }
    }, 250);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [value, location, bag]);

  // Close suggestions when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleSuggestionClick = (suggestion: SuggestionItem) => {
    setShowSuggestions(false);
    navigate(`/doll/${suggestion.id}`);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.value);
  };

  const handleClearClick = () => {
    if (onClear) {
      onClear();
    } else {
      onChange('');
    }
    setSuggestions([]);
    setShowSuggestions(false);
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setShowSuggestions(false);
    if (onSubmit) {
      onSubmit(e);
    }
  };

  return (
    <div ref={wrapperRef} className={`search-box-wrapper ${className}`}>
      <form className={showButton ? 'home-search-form' : 'search-box'} onSubmit={handleFormSubmit}>
        <div className="search-input-wrapper">
          <input
            type="text"
            className={showButton ? 'home-search-input' : 'search-input'}
            placeholder={placeholder || t('search_placeholder')}
            value={value}
            onChange={handleInputChange}
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="none"
            spellCheck={false}
          />
          {value && (
            <button
              type="button"
              className="search-clear-btn"
              onClick={handleClearClick}
              title={t('search_clear')}
            >
              ✕
            </button>
          )}
        </div>
        {showButton && (
          <button type="submit" className="home-search-btn" disabled={!value.trim()}>
            🔍 {t('search_button')}
          </button>
        )}
      </form>

      {showSuggestions && (
        <div className="suggestions-dropdown">
          {loading && (
            <div className="suggestion-item suggestion-loading">
              {t('search_suggestions_loading')}
            </div>
          )}
          {!loading && suggestions.length === 0 && (
            <div className="suggestion-item suggestion-empty">
              {t('search_no_suggestions')}
            </div>
          )}
          {!loading && suggestions.map((suggestion) => (
            <div
              key={suggestion.id}
              className="suggestion-item"
              onClick={() => handleSuggestionClick(suggestion)}
            >
              <div className="suggestion-photo">
                {suggestion.primary_photo_url ? (
                  <img
                    src={getMediaUrl(suggestion.primary_photo_url)}
                    alt={suggestion.name}
                    onError={(e) => {
                      e.currentTarget.style.display = 'none';
                      const placeholder = e.currentTarget.nextElementSibling as HTMLElement;
                      if (placeholder) placeholder.style.display = 'flex';
                    }}
                  />
                ) : null}
                <div
                  className="suggestion-photo-placeholder"
                  style={{ display: suggestion.primary_photo_url ? 'none' : 'flex' }}
                >
                  👧
                </div>
              </div>
              <div className="suggestion-info">
                <div className="suggestion-name">{suggestion.name}</div>
                <div className="suggestion-location">
                  {suggestion.location === 'HOME' ? t('location_home') : t('location_bag', { number: suggestion.bag_number })}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

