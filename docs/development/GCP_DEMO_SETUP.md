# GCP demo setup (real VM metrics)

By default, Zenith **simulates** VM assignment when GCP credentials are missing (`vm/manager.py`).

## Enable real GCP

1. Create a service account with Compute Admin (or minimal VM read/create for your demo).
2. Download JSON key file.
3. Set in `backend/.env`:

```env
GCP_SERVICE_ACCOUNT_JSON_PATH=/absolute/path/to/service-account.json
USE_REAL_METRICS=true
```

4. Restart backend and open **VM Cluster** in the dashboard.

## Demo without GCP

The UI still works with simulated VMs. Label the demo clearly: “Simulated cluster — connect GCP for live metrics.”

## Verification

```bash
cd backend
source ../venv/bin/activate
python -c "from app.vm.manager import list_user_vms; print('ok')"
```

Check backend logs for `GCP not configured` vs real API calls.

**See also:** [ZERO_COST_DEMO_SETUP.md](./ZERO_COST_DEMO_SETUP.md), [CLOUD_CREDENTIAL_SETUP_GUIDE.md](../setup/CLOUD_CREDENTIAL_SETUP_GUIDE.md)
