import { useState, useEffect } from 'react';
import schemaApi from '../../services/schemaApi';
import { clustersAPI } from '../../services/api';
import type { SchemaHistoryResponse, ImpactGraphResponse } from '../../types/schema';

export function useSchemaDetail(subject: string | undefined, activeTab: string) {
    const [detailData, setDetailData] = useState<any>(null);
    const [historyData, setHistoryData] = useState<SchemaHistoryResponse | null>(null);
    const [graphData, setGraphData] = useState<ImpactGraphResponse | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!subject) return;

        const loadData = async () => {
            // 이미 데이터가 있으면 로딩하지 않음
            if (activeTab === 'history' && historyData) return;
            if (activeTab === 'impact' && graphData) return;
            if (activeTab === 'overview' && detailData) return;

            setLoading(true);
            try {
                // 1. Fetch available registries to find active one
                const registriesRes = await clustersAPI.listRegistries();
                const registries = registriesRes.data;
                const activeRegistry = registries?.find((r: any) => r.is_active) || registries?.[0];

                if (!activeRegistry) {
                    console.error('No Schema Registry found');
                    setLoading(false);
                    return;
                }

                if (activeTab === 'overview') {
                    const res = await schemaApi.getDetail(subject, activeRegistry.registry_id);
                    setDetailData(res);
                } else if (activeTab === 'history') {
                    const res = await schemaApi.getHistory(subject, activeRegistry.registry_id);
                    setHistoryData(res);
                } else if (activeTab === 'impact') {
                    const res = await schemaApi.getImpactGraph(subject, activeRegistry.registry_id);
                    setGraphData(res);
                }
            } catch (e) {
                console.error('Failed to load detail data', e);
            } finally {
                setLoading(false);
            }
        };

        loadData();
    }, [subject, activeTab, historyData, graphData, detailData]);

    const reload = () => {
        setDetailData(null);
        setHistoryData(null);
        setGraphData(null);
    };

    return { detailData, historyData, graphData, loading, reload };
}
