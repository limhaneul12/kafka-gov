# Historical Drift Matrix (Resolved)

| Area | Verified State | Decision |
| --- | --- | --- |
| Frontend routing | Core routes previously exposed unsupported routes relative to the shipped backend | Remove unsupported routes from the active UI surface |
| Sidebar surface | `frontend/src/components/layout/Sidebar.tsx` previously exposed `/settings` and other unsupported navigation without matching shipped routes | Remove the dead settings link and unsupported navigation |
| Duplicate Connections UI | Both `frontend/src/pages/Connections.tsx` and `frontend/src/pages/Connections/index.tsx` existed | Keep the directory-based Connections page and delete the duplicate top-level page |
| Duplicate layout surface | `frontend/src/components/layout/Sidebar.tsx` exported the active layout while `frontend/src/components/layout/Layout.tsx` and `frontend/src/components/layout/Header.tsx` duplicated layout concerns | Keep the active Sidebar layout and delete the unused duplicates |
| API namespace drift | Legacy routers used mixed prefixes while the rest of core APIs used `/api/v1/...` | Normalize all active HTTP surfaces to `/api/v1/...` |
| Dead analysis client | A legacy analysis client existed without a matching backend router | Remove the dead client and the unused legacy dashboard page that depended on it |
| Redis config drift | Runtime URLs used overlapping Redis env values | Resolve all runtime URLs from shared settings |
| Approval gate gap | High-risk schema apply paths audited results but did not require explicit approval evidence | Add approval override validation and audit metadata on schema apply success paths |
