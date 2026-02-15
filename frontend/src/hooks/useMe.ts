import { useState, useEffect } from 'react';
import { getMe, MeResponse } from '../api/me';

export function useMe() {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadMe();
  }, []);

  const loadMe = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getMe();
      setMe(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load user information');
    } finally {
      setLoading(false);
    }
  };

  const hasPerm = (permission: string): boolean => {
    return me?.permissions.includes(permission) || false;
  };

  const hasAnyPerm = (...permissions: string[]): boolean => {
    return permissions.some(p => hasPerm(p));
  };

  return {
    me,
    loading,
    error,
    hasPerm,
    hasAnyPerm,
    retry: loadMe,
  };
}

