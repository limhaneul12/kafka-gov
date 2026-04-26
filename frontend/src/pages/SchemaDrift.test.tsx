import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import SchemaDrift from './SchemaDrift';

const mocks = vi.hoisted(() => ({
  listRegistries: vi.fn(),
  searchSchemas: vi.fn(),
  getDrift: vi.fn(),
  toastError: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: {
    error: mocks.toastError,
  },
}));

vi.mock('../services/api', () => ({
  registryAPI: {
    list: mocks.listRegistries,
  },
}));

vi.mock('../services/schemaApi', () => ({
  default: {
    searchSchemas: mocks.searchSchemas,
    getDrift: mocks.getDrift,
  },
}));

describe('SchemaDrift', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.listRegistries.mockResolvedValue({
      data: [{ registry_id: 'registry-1', is_active: true, name: 'Primary', url: 'http://registry' }],
    });
    mocks.searchSchemas.mockResolvedValue({
      items: [
        {
          subject: 'prod.orders-value',
          version: 2,
          storage_url: null,
          checksum: null,
          schema_type: 'AVRO',
          compatibility_mode: 'FULL',
          owner: 'team-orders',
          created_at: null,
        },
        {
          subject: 'prod.payments-value',
          version: 3,
          storage_url: null,
          checksum: null,
          schema_type: 'AVRO',
          compatibility_mode: 'BACKWARD',
          owner: 'team-payments',
          created_at: null,
        },
      ],
      total: 2,
      page: 1,
      limit: 100,
    });
    mocks.getDrift.mockImplementation(async (subject: string) => ({
      subject,
      registry_latest_version: subject === 'prod.orders-value' ? 4 : 3,
      registry_canonical_hash: null,
      catalog_latest_version: subject === 'prod.orders-value' ? 2 : 3,
      catalog_canonical_hash: null,
      observed_version: subject === 'prod.orders-value' ? 2 : 3,
      last_synced_at: null,
      drift_flags:
        subject === 'prod.orders-value' ? ['catalog_snapshot_version_mismatch'] : [],
      has_drift: subject === 'prod.orders-value',
    }));
  });

  it('loads and filters drift results', async () => {
    const user = userEvent.setup();

    render(<SchemaDrift />);

    await screen.findByText('Schema Drift Monitor');
    expect(screen.getByText('prod.orders-value')).toBeInTheDocument();
    expect(screen.queryByText('prod.payments-value')).not.toBeInTheDocument();

    await user.click(screen.getByLabelText('Show drift only'));
    expect(screen.getByText('prod.payments-value')).toBeInTheDocument();

    await user.clear(screen.getByPlaceholderText('Search by subject, owner, compatibility...'));
    await user.type(
      screen.getByPlaceholderText('Search by subject, owner, compatibility...'),
      'payments',
    );

    await waitFor(() => {
      expect(screen.getByText('prod.payments-value')).toBeInTheDocument();
      expect(screen.queryByText('prod.orders-value')).not.toBeInTheDocument();
    });
  });
});
