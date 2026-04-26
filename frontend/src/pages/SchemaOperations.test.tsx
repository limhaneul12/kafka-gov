import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import SchemaOperations from './SchemaOperations';

const mocks = vi.hoisted(() => ({
  listApprovalRequests: vi.fn(),
  getAuditHistory: vi.fn(),
  approveApprovalRequest: vi.fn(),
  rejectApprovalRequest: vi.fn(),
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: {
    error: mocks.toastError,
    success: mocks.toastSuccess,
  },
}));

vi.mock('../services/schemaApi', () => ({
  default: {
    listApprovalRequests: mocks.listApprovalRequests,
    getAuditHistory: mocks.getAuditHistory,
    approveApprovalRequest: mocks.approveApprovalRequest,
    rejectApprovalRequest: mocks.rejectApprovalRequest,
  },
}));

describe('SchemaOperations', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.listApprovalRequests.mockResolvedValue([
      {
        request_id: 'req-1',
        resource_type: 'schema',
        resource_name: 'prod.orders-value',
        change_type: 'apply',
        change_ref: 'chg-1',
        summary: 'Schema apply requires approval',
        justification: 'High risk schema change',
        requested_by: 'alice',
        status: 'pending',
        approver: null,
        decision_reason: null,
        metadata: null,
        requested_at: '2026-04-25T12:00:00Z',
        decided_at: null,
      },
      {
        request_id: 'req-2',
        resource_type: 'schema',
        resource_name: 'prod.payments-value',
        change_type: 'delete',
        change_ref: 'chg-2',
        summary: 'Schema delete requires approval',
        justification: 'decommission legacy flow',
        requested_by: 'bob',
        status: 'approved',
        approver: 'schema-admin',
        decision_reason: 'reviewed',
        metadata: null,
        requested_at: '2026-04-24T12:00:00Z',
        decided_at: '2026-04-24T13:00:00Z',
      },
    ]);
    mocks.getAuditHistory.mockResolvedValue([
      {
        activity_type: 'approval',
        action: 'REQUESTED',
        target: 'prod.orders-value',
        message: 'approval required for schema apply',
        actor: 'alice',
        team: null,
        timestamp: '2026-04-25T12:00:00Z',
        metadata: null,
      },
      {
        activity_type: 'schema',
        action: 'SYNC',
        target: 'prod.payments-value',
        message: 'sync completed',
        actor: 'sync-bot',
        team: null,
        timestamp: '2026-04-24T12:00:00Z',
        metadata: null,
      },
    ]);
    mocks.approveApprovalRequest.mockResolvedValue({});
  });

  it('renders approval requests and audit activity', async () => {
    render(<SchemaOperations />);

    await screen.findByText('Pending Approval Requests');
    expect(await screen.findAllByText('prod.orders-value')).toHaveLength(2);
    expect(screen.getByText('approval required for schema apply')).toBeInTheDocument();
  });

  it('filters and paginates approval and audit lists', async () => {
    const user = userEvent.setup();

    render(<SchemaOperations />);

    await screen.findByText('Pending Approval Requests');

    await user.selectOptions(screen.getByDisplayValue('All statuses'), 'approved');
    expect(screen.getAllByText('prod.payments-value').length).toBeGreaterThan(0);
    expect(screen.queryByText('Schema apply requires approval')).not.toBeInTheDocument();

    await user.clear(screen.getByPlaceholderText('Search target, message, actor...'));
    await user.type(screen.getByPlaceholderText('Search target, message, actor...'), 'sync');
    expect(screen.getByText('sync completed')).toBeInTheDocument();
    expect(screen.queryByText('approval required for schema apply')).not.toBeInTheDocument();
  });

  it('approves a request and refreshes data', async () => {
    const user = userEvent.setup();
    const promptSpy = vi.spyOn(window, 'prompt');
    promptSpy.mockReturnValueOnce('schema-admin').mockReturnValueOnce('reviewed');

    render(<SchemaOperations />);
    await screen.findByText('Schema apply requires approval');

    await user.click(screen.getAllByRole('button', { name: /Approve/i })[0]);

    await waitFor(() => {
      expect(mocks.approveApprovalRequest).toHaveBeenCalledWith('req-1', {
        approver: 'schema-admin',
        decision_reason: 'reviewed',
      });
    });
    expect(mocks.toastSuccess).toHaveBeenCalledWith('Approval request approved');
    promptSpy.mockRestore();
  });
});
