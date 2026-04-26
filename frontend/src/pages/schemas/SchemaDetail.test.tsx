import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import SchemaDetail from './SchemaDetail';

const mocks = vi.hoisted(() => ({
  listRegistries: vi.fn(),
  planChange: vi.fn(),
  planRollback: vi.fn(),
  applySchema: vi.fn(),
  compareVersions: vi.fn(),
  getVersion: vi.fn(),
  exportLatest: vi.fn(),
  exportVersion: vi.fn(),
  rollbackExecute: vi.fn(),
  updateSettings: vi.fn(),
  promptApprovalOverride: vi.fn(),
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
  reload: vi.fn(),
  useSchemaDetail: vi.fn(),
  downloadText: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: {
    error: mocks.toastError,
    success: mocks.toastSuccess,
  },
}));

vi.mock('../../hooks/schema/useSchemaDetail', () => ({
  useSchemaDetail: mocks.useSchemaDetail,
}));

vi.mock('../../services/api', () => ({
  registryAPI: {
    list: mocks.listRegistries,
  },
  schemasAPI: {
    planChange: mocks.planChange,
    apply: mocks.applySchema,
    delete: vi.fn(),
    planRollback: mocks.planRollback,
    rollbackExecute: mocks.rollbackExecute,
    updateSettings: mocks.updateSettings,
    compareVersions: mocks.compareVersions,
    getVersion: mocks.getVersion,
    exportLatest: mocks.exportLatest,
    exportVersion: mocks.exportVersion,
  },
}));

vi.mock('../../utils/approvalOverride', () => ({
  promptApprovalOverride: mocks.promptApprovalOverride,
}));

vi.mock('../../utils/download', () => ({
  downloadText: mocks.downloadText,
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
    mocks.compareVersions.mockResolvedValue({
      data: {
        subject: 'prod.orders-value',
        from_version: 1,
        to_version: 2,
        changed: true,
        diff_type: 'update',
        changes: ['Added field: status'],
        schema_type: 'AVRO',
        compatibility_mode: 'BACKWARD',
        from_schema: '{"type":"record","name":"Order","fields":[]}',
        to_schema: '{"type":"record","name":"Order","fields":[{"name":"status","type":"string"}]}',
      },
    });
    mocks.rollbackExecute.mockResolvedValue({ data: {} });
    mocks.updateSettings.mockResolvedValue({ data: {} });
    mocks.getVersion.mockResolvedValue({
      data: {
        subject: 'prod.orders-value',
        version: 1,
        schema_id: 100,
        schema_str: '{"type":"record","name":"Order","fields":[]}',
        schema_type: 'AVRO',
        hash: 'hash-1',
        canonical_hash: 'canonical-hash-1',
        references: [],
        owner: 'team-data',
        compatibility_mode: 'BACKWARD',
        created_at: '2026-03-10T10:00:00Z',
        author: 'schema-admin',
        commit_message: 'Initial schema',
      },
    });
    mocks.exportLatest.mockResolvedValue({
      data: '{"type":"record","name":"Order","fields":[]}',
      headers: { 'content-disposition': 'attachment; filename="prod.orders-value.v1.avsc"' },
    });
    mocks.exportVersion.mockResolvedValue({
      data: '{"type":"record","name":"Order","fields":[]}',
      headers: { 'content-disposition': 'attachment; filename="prod.orders-value.v1.avsc"' },
    });
    mocks.useSchemaDetail.mockReturnValue({
      detailData,
      historyData: {
        subject: 'prod.orders-value',
        history: [
          {
            version: 1,
            schema_id: 100,
            created_at: '2026-03-10T10:00:00Z',
            diff_type: 'CREATE',
            author: 'schema-admin',
            commit_message: 'Initial schema',
          },
        ],
      },
      driftData: null,
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

  it('surfaces backend detail when change planning fails', async () => {
    const user = userEvent.setup();
    mocks.planChange.mockRejectedValue({
      response: {
        data: {
          detail: 'Schema is not backward compatible',
        },
      },
    });

    renderPage();

    await user.click(screen.getByRole('button', { name: 'Edit' }));
    await user.click(screen.getByRole('button', { name: 'Analyze Changes' }));

    await waitFor(() => {
      expect(mocks.toastError).toHaveBeenCalledWith('Schema is not backward compatible');
    });
    expect(mocks.applySchema).not.toHaveBeenCalled();
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

  it('surfaces backend detail when schema apply fails', async () => {
    const user = userEvent.setup();
    mocks.promptApprovalOverride.mockReturnValue({
      reason: 'approved change',
      approver: 'schema-admin',
      expiresAt: '2026-03-11T00:00:00.000Z',
    });
    mocks.applySchema.mockRejectedValue({
      response: {
        data: {
          detail: 'Registry rejected schema apply',
        },
      },
    });

    renderPage();

    await user.click(screen.getByRole('button', { name: 'Edit' }));
    await user.click(screen.getByRole('button', { name: 'Analyze Changes' }));
    await screen.findByRole('button', { name: 'Apply v2' });
    await user.click(screen.getByRole('button', { name: 'Apply v2' }));

    await waitFor(() => {
      expect(mocks.toastError).toHaveBeenCalledWith('Registry rejected schema apply');
    });
    expect(mocks.reload).not.toHaveBeenCalled();
  });

  it('downloads the latest schema from overview actions', async () => {
    const user = userEvent.setup();

    renderPage();

    await user.click(screen.getByRole('button', { name: 'Download Latest' }));

    expect(mocks.exportLatest).toHaveBeenCalledWith('registry-1', 'prod.orders-value');
    expect(mocks.downloadText).toHaveBeenCalledWith(
      '{"type":"record","name":"Order","fields":[]}',
      'prod.orders-value.v1.avsc',
    );
  });

  it('previews and downloads a specific version from history', async () => {
    const user = userEvent.setup();

    renderPage();

    await user.click(screen.getByRole('button', { name: 'History' }));
    await user.click(screen.getByRole('button', { name: 'Preview' }));

    await screen.findByText('prod.orders-value v1');
    expect(mocks.getVersion).toHaveBeenCalledWith('registry-1', 'prod.orders-value', 1);

    await user.click(screen.getAllByRole('button', { name: 'Download' })[0]);
    expect(mocks.exportVersion).toHaveBeenCalledWith('registry-1', 'prod.orders-value', 1);
  });

  it('executes rollback through the dedicated rollback endpoint', async () => {
    const user = userEvent.setup();
    mocks.promptApprovalOverride.mockReturnValue({
      reason: 'approved rollback',
      approver: 'schema-admin',
      expiresAt: '2026-03-11T00:00:00.000Z',
    });
    mocks.planRollback.mockResolvedValue({
      data: {
        change_id: 'rollback-1',
        plan: [
          {
            subject: 'prod.orders-value',
            current_version: 2,
            target_version: 3,
            diff: { schema_type: 'AVRO', changes: ['Rollback to previous version'] },
            current_schema: '{"type":"record","name":"Order","fields":[{"name":"status","type":"string"}]}',
            schema_definition: '{"type":"record","name":"Order","fields":[]}',
          },
        ],
        compatibility: [{ subject: 'prod.orders-value', mode: 'BACKWARD', is_compatible: true, issues: [] }],
        impacts: [{ status: 'ok' }],
      },
    });
    mocks.useSchemaDetail.mockReturnValue({
      detailData,
      historyData: {
        subject: 'prod.orders-value',
        history: [
          {
            version: 2,
            schema_id: 101,
            created_at: '2026-03-11T10:00:00Z',
            diff_type: 'UPDATE',
            author: 'schema-admin',
            commit_message: 'Add status',
          },
          {
            version: 1,
            schema_id: 100,
            created_at: '2026-03-10T10:00:00Z',
            diff_type: 'CREATE',
            author: 'schema-admin',
            commit_message: 'Initial schema',
          },
        ],
      },
      driftData: null,
      loading: false,
      reload: mocks.reload,
    });
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    renderPage();

    await user.click(screen.getByRole('button', { name: 'History' }));
    await user.click(screen.getByRole('button', { name: 'Restore this version' }));
    await screen.findByRole('button', { name: 'Apply v3' });
    await user.click(screen.getByRole('button', { name: 'Apply v3' }));

    await waitFor(() => {
      expect(mocks.rollbackExecute).toHaveBeenCalledWith('registry-1', {
        subject: 'prod.orders-value',
        version: 1,
        reason: 'Rollback to v1',
        approvalOverride: {
          reason: 'approved rollback',
          approver: 'schema-admin',
          expiresAt: '2026-03-11T00:00:00.000Z',
        },
      });
    });

    expect(confirmSpy).toHaveBeenCalled();
    expect(mocks.applySchema).not.toHaveBeenCalled();
    expect(mocks.toastSuccess).toHaveBeenCalledWith('Schema rollback executed from v1');
    confirmSpy.mockRestore();
  });

  it('compares a historical version to the latest version', async () => {
    const user = userEvent.setup();
    mocks.useSchemaDetail.mockReturnValue({
      detailData,
      historyData: {
        subject: 'prod.orders-value',
        history: [
          {
            version: 2,
            schema_id: 101,
            created_at: '2026-03-11T10:00:00Z',
            diff_type: 'UPDATE',
            author: 'schema-admin',
            commit_message: 'Add status',
          },
          {
            version: 1,
            schema_id: 100,
            created_at: '2026-03-10T10:00:00Z',
            diff_type: 'CREATE',
            author: 'schema-admin',
            commit_message: 'Initial schema',
          },
        ],
      },
      driftData: null,
      loading: false,
      reload: mocks.reload,
    });

    renderPage();

    await user.click(screen.getByRole('button', { name: 'History' }));
    await user.click(screen.getByRole('button', { name: 'Compare to Latest' }));

    await screen.findByText('prod.orders-value comparison v1 → v2');
    expect(mocks.compareVersions).toHaveBeenCalledWith('registry-1', 'prod.orders-value', 1, 2);
    expect(
      screen.getByText((content) => content.includes('Added field: status')),
    ).toBeInTheDocument();
  });

  it('updates schema metadata and compatibility settings', async () => {
    const user = userEvent.setup();
    mocks.useSchemaDetail.mockReturnValue({
      detailData: {
        ...detailData,
        doc: 'https://old-docs.example/schema',
        tags: ['legacy'],
        description: 'Old schema description',
      },
      historyData: {
        subject: 'prod.orders-value',
        history: [
          {
            version: 1,
            schema_id: 100,
            created_at: '2026-03-10T10:00:00Z',
            diff_type: 'CREATE',
            author: 'schema-admin',
            commit_message: 'Initial schema',
          },
        ],
      },
      driftData: null,
      loading: false,
      reload: mocks.reload,
    });

    renderPage();

    await user.click(screen.getByRole('button', { name: 'Edit Metadata' }));
    await user.clear(screen.getByDisplayValue('team-data'));
    await user.type(screen.getByLabelText(/Owner/i), 'team-updated');
    await user.clear(screen.getByDisplayValue('https://old-docs.example/schema'));
    await user.type(screen.getByLabelText(/Documentation URL \/ Notes/i), 'https://docs.example/schema');
    await user.clear(screen.getByDisplayValue('Old schema description'));
    await user.type(screen.getByLabelText(/Description/i), 'Updated schema metadata');
    await user.clear(screen.getByDisplayValue('legacy'));
    await user.type(screen.getByLabelText(/Tags/i), 'pii, critical');
    await user.selectOptions(screen.getByLabelText(/Compatibility/i), 'FULL');
    await user.click(screen.getByRole('button', { name: 'Save Metadata' }));

    expect(mocks.updateSettings).toHaveBeenCalledWith('registry-1', 'prod.orders-value', {
      owner: 'team-updated',
      doc: 'https://docs.example/schema',
      description: 'Updated schema metadata',
      tags: ['pii', 'critical'],
      compatibilityMode: 'FULL',
    });
    expect(mocks.toastSuccess).toHaveBeenCalledWith('Schema settings updated');
    expect(mocks.reload).toHaveBeenCalled();
  });

  it('keeps metadata editor open and surfaces backend detail when settings save fails', async () => {
    const user = userEvent.setup();
    mocks.updateSettings.mockRejectedValue({
      response: {
        data: {
          detail: 'Unable to refresh schema metadata',
        },
      },
    });

    renderPage();

    await user.click(screen.getByRole('button', { name: 'Edit Metadata' }));
    await user.click(screen.getByRole('button', { name: 'Save Metadata' }));

    await waitFor(() => {
      expect(mocks.toastError).toHaveBeenCalledWith('Unable to refresh schema metadata');
    });
    expect(mocks.reload).not.toHaveBeenCalled();
    expect(screen.getByRole('heading', { name: 'Edit Schema Metadata' })).toBeInTheDocument();
  });
});
