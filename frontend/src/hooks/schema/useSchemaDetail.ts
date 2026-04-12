import { useState, useEffect } from 'react';
import schemaApi from '../../services/schemaApi';
import { clustersAPI } from '../../services/api';
import type { SchemaRegistry } from '../../types';
import type { KnownTopicNamesResponse, SchemaHistoryResponse } from '../../types/schema';

export function useSchemaDetail(subject: string | undefined, activeTab: string) {
    const [detailData, setDetailData] = useState<unknown>(null);
    const [historyData, setHistoryData] = useState<SchemaHistoryResponse | null>(null);
    const [topicHintsData, setTopicHintsData] = useState<KnownTopicNamesResponse | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!subject) return;

        const loadData = async () => {
            // 이미 데이터가 있으면 로딩하지 않음
            if (activeTab === 'history' && historyData) return;
            if (activeTab === 'knownTopics' && topicHintsData) return;
            if (activeTab === 'overview' && detailData) return;

            setLoading(true);
            try {
                // 1. Fetch available registries to find active one
                const registriesRes = await clustersAPI.listRegistries();
                const registries = registriesRes.data as SchemaRegistry[] | undefined;
                const activeRegistry = registries?.find((registry) => registry.is_active) ?? registries?.[0];

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
                } else if (activeTab === 'knownTopics') {
                    const res = await schemaApi.getKnownTopicNames(subject, activeRegistry.registry_id);
                    setTopicHintsData(res);
                }
            } catch (e) {
                console.error('Failed to load detail data', e);
            } finally {
                setLoading(false);
            }
        };

        loadData();
    }, [subject, activeTab, historyData, topicHintsData, detailData]);

    const reload = () => {
        setDetailData(null);
        setHistoryData(null);
        setTopicHintsData(null);
    };

    return { detailData, historyData, topicHintsData, loading, reload };
}
