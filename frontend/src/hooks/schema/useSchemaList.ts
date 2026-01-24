import { useState, useCallback } from 'react';
import schemaApi from '../../services/schemaApi';
import type { SchemaArtifactResponse } from '../../types/schema';

export function useSchemaList() {
    const [schemas, setSchemas] = useState<SchemaArtifactResponse[]>([]);
    const [loading, setLoading] = useState(false);
    const [total, setTotal] = useState(0);

    const fetchSchemas = useCallback(async (query: string = '', owner: string | null = null) => {
        setLoading(true);
        try {
            const res = await schemaApi.searchSchemas({ query, owner: owner || undefined, limit: 100 });
            setSchemas(res.items);
            setTotal(res.total);
        } catch (error) {
            console.error('Search failed', error);
            // TODO: Handle error state (toast notification, etc.)
        } finally {
            setLoading(false);
        }
    }, []);

    return { schemas, loading, total, fetchSchemas };
}
