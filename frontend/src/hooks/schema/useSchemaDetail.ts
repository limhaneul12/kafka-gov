import { useEffect, useState } from 'react';

import schemaApi from '../../services/schemaApi';
import type { SchemaDriftResponse, SchemaHistoryResponse } from '../../types/schema';
import { NO_ACTIVE_SCHEMA_REGISTRY_MESSAGE, resolveActiveRegistry, toastGovernanceError } from '../../utils/schemaGovernance';
import { toast } from 'sonner';

export function useSchemaDetail(subject: string | undefined, activeTab: string) {
    const [detailData, setDetailData] = useState<unknown>(null);
    const [historyData, setHistoryData] = useState<SchemaHistoryResponse | null>(null);
    const [driftData, setDriftData] = useState<SchemaDriftResponse | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!subject) return;

        const loadData = async () => {
            if (activeTab === 'history' && historyData) return;
            if (activeTab === 'overview' && detailData) return;

            setLoading(true);
            try {
                const activeRegistry = await resolveActiveRegistry();

                if (!activeRegistry) {
                    console.error('No Schema Registry found');
                    toast.error(NO_ACTIVE_SCHEMA_REGISTRY_MESSAGE);
                    return;
                }

                if (activeTab === 'overview') {
                    const [detail, drift] = await Promise.all([
                        schemaApi.getDetail(subject, activeRegistry.registry_id),
                        schemaApi.getDrift(subject, activeRegistry.registry_id),
                    ]);
                    setDetailData(detail);
                    setDriftData(drift);
                } else if (activeTab === 'history') {
                    const res = await schemaApi.getHistory(subject, activeRegistry.registry_id);
                    setHistoryData(res);
                }
            } catch (e) {
                console.error('Failed to load detail data', e);
                toastGovernanceError(
                    activeTab === 'history' ? 'Failed to load schema history' : 'Failed to load schema overview',
                    e,
                );
            } finally {
                setLoading(false);
            }
        };

        void loadData();
    }, [subject, activeTab, historyData, detailData]);

    const reload = () => {
        setDetailData(null);
        setHistoryData(null);
        setDriftData(null);
    };

    return { detailData, historyData, driftData, loading, reload };
}
