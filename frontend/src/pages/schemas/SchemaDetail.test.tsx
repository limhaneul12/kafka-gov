import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import SchemaDetail from './SchemaDetail';

const mocks = vi.hoisted(() => ({
  listRegistries: vi.fn(),
  planChange: vi.fn(),
  applySchema: vi.fn(),
  promptApprovalOverride: vi.fn(),
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
  reload: vi.fn(),
  useSchemaDetail: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: {
    error: mocks.toastError,
    success: mocks.toastSuccess,
  },
}));

vi.mock('../../components/schema/ImpactGraph', () => ({
  default: () => null,
}));

vi.mock('../../hooks/schema/useSchemaDetail', () => ({
  useSchemaDetail: mocks.useSchemaDetail,
}));

vi.mock('../../services/api', () => ({
  clustersAPI: {
    listRegistries: mocks.listRegistries,
  },
  schemasAPI: {
    planChange: mocks.planChange,
    apply: mocks.applySchema,
    delete: vi.fn(),
    planRollback: vi.fn(),
  },
}));

vi.mock('../../utils/approvalOverride', () => ({
  promptApprovalOverride: mocks.promptApprovalOverride,
}));

const detailData = {
  subject: 'prod.orders-value',
  version: 1,
  schema_id: 100,
  schema_str: '{"type":"record","name":"Order","fields":[]}',
  schema_type: 'AVRO',
  compatibility_mode: 'BACKWARD',
  owner: 'team-data',
  updated_at: '2026-03-10T10:00:00Z',
  violations: [],
  policy_score: 0.9,
};

const planResult = {
  change_id: 'chg-123',
  plan: [
    {
      subject: 'prod.orders-value',
      current_version: 1,
      target_version: 2,
      diff: {
        schema_type: 'AVRO',
        changes: ['Added optional field'],
      },
      current_schema: '{"type":"record","name":"Order","fields":[]}',
      schema: '{"type":"record","name":"Order","fields":[{"name":"status","type":["null","string"],"default":null}]}',
    },
  ],
  compatibility: [
    {
      subject: 'prod.orders-value',
      mode: 'BACKWARD',
      is_compatible: true,
      issues: [],
    },
  ],
  impacts: [
    {
      status: 'ok',
      topics: ['prod.orders.created'],
      consumers: ['orders-consumer'],
    },
  ],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/schemas/prod.orders-value']}>
      <Routes>
        <Route path="/schemas/:subject" element={<SchemaDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('SchemaDetail approval flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.listRegistries.mockResolvedValue({
      data: [{ registry_id: 'registry-1', is_active: true, name: 'Primary', url: 'http://registry' }],
    });
    mocks.planChange.mockResolvedValue({ data: planResult });
    mocks.applySchema.mockResolvedValue({ data: {} });
    mocks.useSchemaDetail.mockReturnValue({
      detailData,
      historyData: null,
      graphData: null,
      loading: false,
      reload: mocks.reload,
    });
  });

  it('blocks apply when approval evidence is missing', async () => {
    const user = userEvent.setup();
    mocks.promptApprovalOverride.mockReturnValue(null);

    renderPage();

    await user.click(screen.getByRole('button', { name: 'Edit' }));
    await user.click(screen.getByRole('button', { name: 'Analyze Changes' }));
    await screen.findByRole('button', { name: 'Apply v2' });
    await user.click(screen.getByRole('button', { name: 'Apply v2' }));

    expect(mocks.promptApprovalOverride).toHaveBeenCalledWith('schema apply for prod.orders-value');
    expect(mocks.applySchema).not.toHaveBeenCalled();
    expect(mocks.toastError).toHaveBeenCalledWith('Approval evidence is required for this schema change');
  });

  it('submits schema apply with approval evidence', async () => {
    const user = userEvent.setup();
    mocks.promptApprovalOverride.mockReturnValue({
      reason: 'approved change',
      approver: 'schema-admin',
      expiresAt: '2026-03-11T00:00:00.000Z',
    });

    renderPage();

    await user.click(screen.getByRole('button', { name: 'Edit' }));
    await user.click(screen.getByRole('button', { name: 'Analyze Changes' }));
    await screen.findByRole('button', { name: 'Apply v2' });
    await user.click(screen.getByRole('button', { name: 'Apply v2' }));

    await waitFor(() => {
      expect(mocks.applySchema).toHaveBeenCalledWith('registry-1', {
        env: 'prod',
        change_id: 'chg-123',
        approvalOverride: {
          reason: 'approved change',
          approver: 'schema-admin',
          expiresAt: '2026-03-11T00:00:00.000Z',
        },
        items: [
          {
            subject: 'prod.orders-value',
            type: 'AVRO',
            compatibility: 'BACKWARD',
            schema: '{\n  "type": "record",\n  "name": "Order",\n  "fields": []\n}',
          },
        ],
      });
    });

    expect(mocks.reload).toHaveBeenCalled();
    expect(mocks.toastSuccess).toHaveBeenCalledWith('Schema successfully updated to next version');
  });
});
