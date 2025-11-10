# 🗺️ Roadmap

Kafka-Gov feature roadmap and development plans.

## ✅ Completed (v1.0)

### Backend Core
- ✅ Multi-cluster connection management with encryption
- ✅ Topic CRUD with rich metadata (owner, tags, docs)
- ✅ YAML-based batch operations with dry-run
- ✅ Environment-specific policy enforcement
- ✅ Policy version management (draft/active/archived)
- ✅ Schema Registry integration with MinIO storage
- ✅ Kafka Connect connector management (backend API)
- ✅ Complete audit trail with event sourcing
- ✅ 64%+ test coverage with pytest

### Real-time Monitoring (🔥 New in v1.0)
- ✅ Topic detail view with consumer health insights
- ✅ Real-time consumer group list with lag statistics
- ✅ Lag metrics calculation (p50, p95, max, total)
- ✅ Group state tracking (Stable, Rebalancing, Empty, Dead)
- ✅ Governance alerts and recommendations per topic
- ✅ Member-level partition assignments
- ✅ Fairness index (Gini coefficient) calculation
- ✅ Rebalance stability scoring with time windows
- ✅ Stuck partition detection with configurable thresholds
- ✅ Historical lag tracking via DB snapshots
- ✅ WebSocket-based live lag streaming
- ✅ Policy advisor for assignor & scaling recommendations

### Frontend Core
- ✅ React 19 frontend with TailwindCSS
- ✅ Dashboard with cluster health monitoring
- ✅ Topic list with search functionality
- ✅ Create Topic modal (single vs batch toggle)
- ✅ YAML batch upload interface
- ✅ Policy version management UI
- ✅ Team Analytics page
- ✅ Consumer Group list page with metrics
- ✅ Consumer Group detail page with live lag charts

---

## 🚧 In Progress (v1.1)

### Frontend Enhancements
- 🔄 Topics page: Owner/Team filtering UI
- 🔄 Topics page: Tags filtering UI  
- 🔄 Topics page: Doc field display
- 🔄 Topics page: Environment filter implementation
- 🔄 Create Topic modal: Dry-run button
- 🔄 Create Topic modal: Preset selection (dev/stg/prod/custom)
- 🔄 Dashboard: Topic/Schema sync functionality
- 🔄 Dashboard: Manual sync button
- 🔄 Policy page: Frontend integration with preset_spec.py
- 🔄 Connections page: Kafka Connect tab UI
- 🔄 Policy Versions: Enhanced version management features

---

## 🔮 Planned (v2.0)

### Monitoring & Observability
- 📅 Topic retention policy recommendations
- 📅 Prometheus metrics export
- 📅 Grafana dashboard templates
- 📅 Real-time cluster metrics (throughput, latency)
- 📅 Consumer group SLO compliance monitoring
- 📅 Predictive lag alerting with ML models

### Governance & Security
- 📅 Role-based access control (RBAC)
- 📅 Multi-tenancy support
- 📅 Approval workflows for production changes
- 📅 Slack/Discord notifications for policy violations

### Advanced Features
- 📅 Schema migration wizard
- 📅 GitOps integration (sync with Git repository)
- 📅 Cross-cluster topic migration tool
- 📅 Topic usage analytics (hot partitions, consumer lag)

---

## 💡 Ideas (Future)

- 🤖 AI-powered topic naming suggestions
- 💰 Cost estimation for topic configurations
- 📈 Advanced analytics dashboard (usage patterns, trends)
- 🔄 Automated schema evolution recommendations
- 🔍 Full-text search across topics/schemas/docs
- 📱 Mobile app for alerts and quick actions
- 🌐 Multi-language support (i18n)

---

## Version History

### v1.0 (2025-01)
- Initial release with core governance features
- Real-time monitoring and consumer analytics
- Policy enforcement and audit trail

### v0.9 (2024-12)
- Beta release for internal testing
- Core CRUD operations
- Batch processing foundation

---

## Contributing

Have ideas for new features? [Create an issue](https://github.com/limhaneul12/kafka-gov/issues) or check our [Contributing Guide](../CONTRIBUTING.md).
