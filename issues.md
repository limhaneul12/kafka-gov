# Drift Matrix

| Area | Verified State | Decision |
| --- | --- | --- |
| Frontend routing | `frontend/src/App.tsx` routed topics/schemas/connections/policies but omitted `Consumers` and `ConsumerDetail` even though `frontend/src/pages/TopicDetail.tsx` linked into `/consumers/:groupId` | Add consumer routes and keep consumers in core surface |
| Sidebar surface | `frontend/src/components/layout/Sidebar.tsx` exposed `/settings` with no matching route | Remove the dead settings link and expose core `Consumers` navigation |
| Duplicate Connections UI | Both `frontend/src/pages/Connections.tsx` and `frontend/src/pages/Connections/index.tsx` existed | Keep the directory-based Connections page and delete the duplicate top-level page |
| Duplicate layout surface | `frontend/src/components/layout/Sidebar.tsx` exported the active layout while `frontend/src/components/layout/Layout.tsx` and `frontend/src/components/layout/Header.tsx` duplicated layout concerns | Keep the active Sidebar layout and delete the unused duplicates |
| API namespace drift | `app/topic/interface/routers/metrics_router.py` used `/metrics` and `app/schema/interface/routers/policy_router.py` used `/schemas/policies` while the rest of core APIs used `/api/v1/...` | Normalize both to `/api/v1/...` |
| Dead analysis client | `frontend/src/services/api.ts` exported `analysisAPI`, but `app/main.py` had no analysis router | Remove the dead client and the unused legacy dashboard page that depended on it |
| Redis/Celery drift | `app/celery_app.py` and `app/shared/cache.py` hardcoded separate Redis URLs while `docker-compose.yml` set multiple overlapping env values | Resolve all runtime URLs from shared settings |
| Approval gate gap | Topic and schema apply paths audited results but did not require explicit approval evidence for risky changes | Add approval override validation and audit metadata on topic/schema apply success paths |
