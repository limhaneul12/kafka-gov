import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import History from './History';

const { recentMock } = vi.hoisted(() => ({
  recentMock: vi.fn(),
}));

vi.mock('../services/api', () => ({
  auditAPI: {
    recent: recentMock,
  },
}));

const auditLogs = [
  {
    activity_type: 'topic',
    action: 'APPLY',
    target: 'prod.orders.created',
    message: 'Topic apply completed',
    actor: 'alice',
    team: 'platform',
    timestamp: '2026-03-10T10:00:00Z',
    metadata: {
      approval: {
        approval_required: true,
        approval_override_present: true,
        summary: 'approval override supplied for 1 rule(s)',
      },
      approval_override: {
        approver: 'approver-1',
        reason: 'urgent production fix',
      },
      risk: {
        risk_level: 'high',
        reasons: ['production topic change'],
      },
    },
  },
  {
    activity_type: 'schema',
    action: 'APPLY',
    target: 'prod.orders-value',
    message: 'Schema apply pending approval',
    actor: 'bob',
    team: 'data',
    timestamp: '2026-03-10T11:00:00Z',
    metadata: {
      approval: {
        approval_required: true,
        approval_override_present: false,
        summary: 'approval required before apply for 1 rule(s)',
      },
      risk: {
        risk_level: 'critical',
        reasons: ['compatibility NONE'],
      },
    },
  },
  {
    activity_type: 'policy',
    action: 'UPDATE',
    target: 'retention-policy',
    message: 'Policy updated',
    actor: 'carol',
    team: null,
    timestamp: '2026-03-10T12:00:00Z',
    metadata: {
      approval: {
        approval_required: false,
        approval_override_present: false,
        summary: 'approval gate not required for this evaluation',
      },
      risk: {
        risk_level: 'low',
        reasons: ['metadata update'],
      },
    },
  },
  {
    activity_type: 'approval',
    action: 'REQUESTED',
    target: 'prod.orders.created',
    message: 'approval required for topic apply',
    actor: 'alice',
    team: null,
    timestamp: '2026-03-10T12:30:00Z',
    metadata: {
      approval_request: {
        request_id: 'req-123',
        resource_type: 'topic',
        change_type: 'apply',
        change_ref: 'chg-approval-001',
        status: 'pending',
        requested_by: 'alice',
      },
      approval: {
        approval_required: true,
        approval_override_present: false,
        summary: 'approval required before apply for 1 rule(s)',
      },
      risk: {
        risk_level: 'high',
        reasons: ['production topic change'],
      },
    },
  },
] as const;

describe('History', () => {
  beforeEach(() => {
    recentMock.mockResolvedValue({ data: auditLogs });
  });

  it('loads and renders audit activity rows with approval state', async () => {
    render(<History />);

    expect(await screen.findByText('Topic apply completed')).toBeInTheDocument();
    expect(screen.getByText('Schema apply pending approval')).toBeInTheDocument();
    expect(screen.getByText('Policy updated')).toBeInTheDocument();
    expect(screen.getByText('approval required for topic apply')).toBeInTheDocument();
    expect(screen.getByText('OVERRIDDEN')).toBeInTheDocument();
    expect(screen.getAllByText('REQUIRED')).toHaveLength(2);
    expect(screen.getByText('CHECKED')).toBeInTheDocument();
    expect(recentMock).toHaveBeenCalledWith(50);
  });

  it('filters by resource, approval state, and risk level', async () => {
    const user = userEvent.setup();

    render(<History />);

    await screen.findByText('Topic apply completed');

    const selects = screen.getAllByRole('combobox');
    await user.selectOptions(selects[1], 'schema');
    await user.selectOptions(selects[2], 'required');
    await user.selectOptions(selects[3], 'critical');

    expect(screen.getByText('Schema apply pending approval')).toBeInTheDocument();
    expect(screen.queryByText('Topic apply completed')).not.toBeInTheDocument();
    expect(screen.queryByText('Policy updated')).not.toBeInTheDocument();
    expect(screen.queryByText('approval required for topic apply')).not.toBeInTheDocument();
  });

  it('filters approval activities explicitly', async () => {
    const user = userEvent.setup();

    render(<History />);

    await screen.findByText('approval required for topic apply');

    const selects = screen.getAllByRole('combobox');
    await user.selectOptions(selects[1], 'approval');

    expect(screen.getByText('approval required for topic apply')).toBeInTheDocument();
    expect(screen.queryByText('Topic apply completed')).not.toBeInTheDocument();
    expect(screen.queryByText('Schema apply pending approval')).not.toBeInTheDocument();
  });

  it('expands a row to show approval, risk, and raw metadata details', async () => {
    const user = userEvent.setup();

    render(<History />);

    await screen.findByText('Topic apply completed');

    const buttons = screen.getAllByRole('button');
    await user.click(buttons[1]);

    expect(await screen.findByText('Raw Metadata')).toBeInTheDocument();
    expect(screen.getByText('Approver: approver-1')).toBeInTheDocument();
    expect(screen.getAllByText('Reason: urgent production fix')).toHaveLength(2);
    expect(screen.getByText('Level: high')).toBeInTheDocument();
    expect(screen.getAllByText(/production topic change/)).toHaveLength(4);
  });

  it('reloads activity data when the limit changes', async () => {
    const user = userEvent.setup();

    render(<History />);

    await screen.findByText('Topic apply completed');

    const selects = screen.getAllByRole('combobox');
    await user.selectOptions(selects[0], '100');

    await waitFor(() => {
      expect(recentMock).toHaveBeenLastCalledWith(100);
    });
  });
});
