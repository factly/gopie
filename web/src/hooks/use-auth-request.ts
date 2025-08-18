import { useState, useEffect } from 'react';

interface UseAuthRequestReturn {
  isInitializing: boolean;
  error: string | null;
}

export function useAuthRequest(setError: (error: string | null) => void): UseAuthRequestReturn {
  const [isInitializing, setIsInitializing] = useState(true);
  const [error, setLocalError] = useState<string | null>(null);

  //TODO maintain return_to url
  const initializeAuthRequest = async () => {
    try {
      setIsInitializing(true);

      // If no auth request ID in URL, generate one via OAuth authorize endpoint
      const response = await fetch('/api/oauth/authorize');
      const data = await response.json();

      if (!data.authRequestId) {
        const errorMsg = 'Failed to initialize authentication request';
        setLocalError(errorMsg);
        setError(errorMsg);
      }
    } catch (error) {
      console.error('Auth request initialization error:', error);
      const errorMsg = 'Failed to initialize authentication';
      setLocalError(errorMsg);
      setError(errorMsg);
    } finally {
      setIsInitializing(false);
    }
  };
  useEffect(() => {
    initializeAuthRequest();
  }, []);

  return {
    isInitializing,
    error,
  };
}
