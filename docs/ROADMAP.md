# 🗺️ Roadmap

Kafka-Gov feature roadmap and development plans.

## ✅ Completed (v1.0)

### Backend Core
- ✅ Multi-cluster connection management with encryption
- ✅ Environment-specific policy enforcement
- ✅ Policy version management (draft/active/archived)
- ✅ Schema Registry integration with MinIO storage
- ✅ Multi-cluster connection management backend API
- ✅ Complete audit trail with event sourcing
- ✅ Backend test coverage maintained above the enforced threshold

### Governance Visibility (🔥 New in v1.0)
- ✅ Governance dashboard for schema and cluster health
- ✅ Approval-aware audit history
- ✅ Naming-derived known topic hints
- ✅ Connection visibility for active broker and registry endpoints

### Frontend Core
- ✅ React 19 frontend with TailwindCSS
- ✅ Dashboard with cluster health monitoring
- ✅ Policy version management UI
- ✅ Schema inventory and detail flows
- ✅ Connections management surface

---

## 🚧 In Progress (v1.1)

### Frontend Enhancements
- 🔄 Connections page: richer broker and registry diagnostics
- 🔄 Policy Versions: Enhanced version management features

---

## 🔮 Planned (v2.0)

### Monitoring & Observability
- 📅 Prometheus metrics export
- 📅 Grafana dashboard templates
- 📅 Real-time cluster metrics (throughput, latency)
- 📅 Schema governance health trend reporting
- 📅 Predictive policy-risk alerting with ML models

### Governance & Security
- 📅 Role-based access control (RBAC)
- 📅 Multi-tenancy support
- 📅 Approval workflows for production changes
- 📅 Slack/Discord notifications for policy violations

### Advanced Features
- 📅 Schema migration wizard
- 📅 GitOps integration (sync with Git repository)

---

## 💡 Ideas (Future)

- 📈 Advanced analytics dashboard (usage patterns, trends)
- 🔄 Automated schema evolution recommendations
- 🔍 Full-text search across schemas/docs
- 📱 Mobile app for alerts and quick actions
- 🌐 Multi-language support (i18n)

---

## Version History

### v1.0 (2025-01)
- Initial release with core governance features
- Schema governance dashboard and audit visibility
- Policy enforcement and audit trail

### v0.9 (2024-12)
- Beta release for internal testing
- Core CRUD operations
- Batch processing foundation

---

## Contributing

Have ideas for new features? [Create an issue](https://github.com/limhaneul12/kafka-gov/issues) or check our [Contributing Guide](../CONTRIBUTING.md).
