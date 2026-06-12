import { useEffect, useState } from 'react';
import { apiClient } from '../api';

/**
 * Loads organization membership for resource pages (VM, storage, provision).
 */
export function useOrgContext() {
  const [orgContext, setOrgContext] = useState({
    orgId: null,
    orgName: null,
    myRole: null,
    isAdmin: false,
    loading: true,
  });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await apiClient.get('/organizations/me');
        if (cancelled) return;
        const org = data?.organization;
        const role = data?.my_role;
        setOrgContext({
          orgId: org?.id || null,
          orgName: org?.name || null,
          myRole: role || null,
          isAdmin: role === 'owner' || role === 'admin',
          loading: false,
        });
      } catch {
        if (!cancelled) {
          setOrgContext({
            orgId: null,
            orgName: null,
            myRole: null,
            isAdmin: false,
            loading: false,
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return orgContext;
}
