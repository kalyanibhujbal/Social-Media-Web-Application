import React, { createContext, useContext, useEffect, useState } from 'react';
import { AuthContext } from './AuthContext';
import { api } from '../services/api';

const emptyCounts = {
  total: 0,
  sections: {},
  error: '',
};

export const NotificationCountContext = createContext(emptyCounts);

export const NotificationCountProvider = ({ children }) => {
  const { user } = useContext(AuthContext);
  const [counts, setCounts] = useState(emptyCounts);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) {
      setCounts(emptyCounts);
      setError('');
      return undefined;
    }

    let active = true;
    const refresh = async () => {
      try {
        const result = await api.getNotifications(0, 1);
        if (active) {
          setCounts({
            total: result.unread_count || 0,
            sections: result.unread_by_section || {},
            error: '',
          });
          setError('');
        }
      } catch (err) {
        if (active) setError(err.message || 'Notification counts could not be refreshed.');
      }
    };

    refresh();
    const timer = window.setInterval(refresh, 30000);
    window.addEventListener('openvibe:notifications-updated', refresh);
    return () => {
      active = false;
      window.clearInterval(timer);
      window.removeEventListener('openvibe:notifications-updated', refresh);
    };
  }, [user]);

  return <NotificationCountContext.Provider value={{ ...counts, error }}>{children}</NotificationCountContext.Provider>;
};
