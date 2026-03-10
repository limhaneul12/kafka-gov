import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import Topics from './Topics';

const mocks = vi.hoisted(() => ({
  listKafka: vi.fn(),
  listTopics: vi.fn(),
  deleteTopic: vi.fn(),
  bulkDelete: vi.fn(),
  promptApprovalOverride: vi.fn(),
  toastError: vi.fn(),
  toastWarning: vi.fn(),
  toastSuccess: vi.fn(),
  toastInfo: vi.fn(),
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock('sonner', () => ({
  toast: {
    error: mocks.toastError,
    warning: mocks.toastWarning,
    success: mocks.toastSuccess,
    info: mocks.toastInfo,
  },
}));

vi.mock('../services/api', () => ({
  topicsAPI: {
    list: mocks.listTopics,
    delete: mocks.deleteTopic,
    bulkDelete: mocks.bulkDelete,
    updateMetadata: vi.fn(),
  },
  clustersAPI: {
    listKafka: mocks.listKafka,
  },
}));

vi.mock('../utils/approvalOverride', () => ({
  promptApprovalOverride: mocks.promptApprovalOverride,
}));

vi.mock('../utils/colors', () => ({
  getOwnerColor: () => 'bg-slate-100 text-slate-800',
  getTagColor: () => 'bg-slate-100 text-slate-800',
}));

vi.mock('../utils/format', () => ({
  formatRetention: (value: number | null) => (value === null ? '-' : `${value}`),
}));

vi.mock('../components/topic/EditTopicMetadataModal', () => ({
  default: () => null,
}));

vi.mock('../components/topic/CreateTopicModal', () => ({
  default: () => null,
}));

vi.mock('../components/topic/FailureReportModal', () => ({
  default: () => null,
}));

vi.mock('../components/topic/SuccessReportModal', () => ({
  default: () => null,
}));

vi.mock('../components/ui/Pagination', () => ({
  default: () => null,
}));

const topicRow = {
  name: 'prod.orders.created',
  owners: ['team-platform'],
  doc: null,
  tags: ['critical'],
  partition_count: 6,
  replication_factor: 3,
  retention_ms: 604800000,
  environment: 'prod',
  slo: null,
  sla: null,
};

describe('Topics approval flows', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.listKafka.mockResolvedValue({
      data: [{ cluster_id: 'cluster-1', name: 'Primary Cluster' }],
    });
    mocks.listTopics.mockResolvedValue({
      data: {
        items: [topicRow],
        total: 1,
      },
    });
    mocks.deleteTopic.mockResolvedValue({ data: {} });
    mocks.bulkDelete.mockResolvedValue({ data: {} });
  });

  it('blocks topic delete when approval evidence is missing', async () => {
    const user = userEvent.setup();
    mocks.promptApprovalOverride.mockReturnValue(null);

    render(
      <MemoryRouter>
        <Topics />
      </MemoryRouter>,
    );

    await screen.findByText('prod.orders.created');
    await user.click(screen.getByTitle('Delete topic'));

    expect(mocks.promptApprovalOverride).toHaveBeenCalledWith('topic delete for prod.orders.created');
    expect(mocks.deleteTopic).not.toHaveBeenCalled();
    expect(mocks.toastError).toHaveBeenCalled();
  });

  it('sends approval evidence for bulk delete', async () => {
    const user = userEvent.setup();
    mocks.promptApprovalOverride.mockReturnValue({
      reason: 'cleanup',
      approver: 'admin',
      expiresAt: '2026-03-11T00:00:00.000Z',
    });

    render(
      <MemoryRouter>
        <Topics />
      </MemoryRouter>,
    );

    await screen.findByText('prod.orders.created');

    const checkboxes = screen.getAllByRole('checkbox');
    await user.click(checkboxes[1]);
    await user.click(screen.getByRole('button', { name: '일괄 삭제' }));

    await waitFor(() => {
      expect(mocks.bulkDelete).toHaveBeenCalledWith(
        'cluster-1',
        ['prod.orders.created'],
        {
          reason: 'cleanup',
          approver: 'admin',
          expiresAt: '2026-03-11T00:00:00.000Z',
        },
      );
    });
  });
});
