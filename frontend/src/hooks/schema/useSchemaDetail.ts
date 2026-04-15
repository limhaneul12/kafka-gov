import { useEffect, useState } from 'react';

import { registryAPI } from '../../services/api';
import schemaApi from '../../services/schemaApi';
import type { SchemaRegistry } from '../../types';
import type { SchemaHistoryResponse } from '../../types/schema';

export function useSchemaDetail(subject: string | undefined, activeTab: string) {
    const [detailData, setDetailData] = useState<unknown>(null);
    const [historyData, setHistoryData] = useState<SchemaHistoryResponse | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!subject) return;

        const loadData = async () => {
            if (activeTab === 'history' && historyData) return;
            if (activeTab === 'overview' && detailData) return;

            setLoading(true);
            try {
                const registriesRes = await registryAPI.list();
                const registries = registriesRes.data as SchemaRegistry[] | undefined;
                const activeRegistry = registries?.find((registry) => registry.is_active) ?? registries?.[0];

                if (!activeRegistry) {
                    console.error('No Schema Registry found');
                    return;
                }

                if (activeTab === 'overview') {
                    const res = await schemaApi.getDetail(subject, activeRegistry.registry_id);
                    setDetailData(res);
                } else if (activeTab === 'history') {
                    const res = await schemaApi.getHistory(subject, activeRegistry.registry_id);
                    setHistoryData(res);
                }
            } catch (e) {
                console.error('Failed to load detail data', e);
            } finally {
                setLoading(false);
            }
        };

        void loadData();
    }, [subject, activeTab, historyData, detailData]);

    const reload = () => {
        setDetailData(null);
        setHistoryData(null);
    };

    return { detailData, historyData, loading, reload };
}
