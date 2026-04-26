import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import SchemaPolicies from './SchemaPolicies';
import type { SchemaPolicyRecord } from '../types/schemaPolicy';

const mocks = vi.hoisted(() => ({
  listPolicies: vi.fn(),
  getPolicyHistory: vi.fn(),
  updatePolicyStatus: vi.fn(),
  createPolicy: vi.fn(),
  deletePolicy: vi.fn(),
  confirmSchemaGovernanceAction: vi.fn(),
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: {
    error: mocks.toastError,
    success: mocks.toastSuccess,
  },
}));

vi.mock('../services/schemaApi', async () => {
  const actual = await vi.importActual<typeof import('../services/schemaApi')>('../services/schemaApi');

  return {
    ...actual,
    default: {
      ...actual.default,
      listPolicies: mocks.listPolicies,
      getPolicyHistory: mocks.getPolicyHistory,
      updatePolicyStatus: mocks.updatePolicyStatus,
      createPolicy: mocks.createPolicy,
      deletePolicy: mocks.deletePolicy,
    },
  };
});

vi.mock('../utils/schemaGovernancePrompts', async () => {
  const actual = await vi.importActual<typeof import('../utils/schemaGovernancePrompts')>('../utils/schemaGovernancePrompts');

  return {
    ...actual,
    confirmSchemaGovernanceAction: mocks.confirmSchemaGovernanceAction,
  };
});

vi.mock('../components/schema/policies/SchemaPolicyList', () => ({
  default: ({
    policies,
    onActivate,
    onDelete,
  }: {
    policies: SchemaPolicyRecord[];
    onActivate: (policy: SchemaPolicyRecord) => void;
    onDelete: (policy: SchemaPolicyRecord) => void;
  }) => (
    <div>
      <div data-testid="policy-count">{policies.length}</div>
      <button type="button" onClick={() => onActivate(policies[0])}>
        Activate Policy
      </button>
      <button type="button" onClick={() => onDelete(policies[0])}>
        Delete Policy
      </button>
    </div>
  ),
}));

vi.mock('../components/schema/policies/SchemaPolicyDetailModal', () => ({
  default: () => null,
}));

vi.mock('../components/schema/policies/SchemaPolicyComposer', () => ({
  default: () => null,
}));

const policyRecord = {
  policy_id: 'policy-1',
  name: 'Orders Policy',
  description: 'Policy for orders schemas',
  policy_type: 'lint' as const,
  status: 'draft' as const,
  version: 1,
  target_environment: 'prod',
  content: {},
  created_by: 'schema-admin',
  created_at: '2026-04-25T12:00:00Z',
};

describe('SchemaPolicies', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.listPolicies.mockResolvedValue([policyRecord]);
    mocks.updatePolicyStatus.mockResolvedValue(undefined);
    mocks.deletePolicy.mockResolvedValue(undefined);
    mocks.confirmSchemaGovernanceAction.mockReturnValue(true);
  });

  it('activates a draft policy and refetches the list', async () => {
    const user = userEvent.setup();

    render(<SchemaPolicies />);

    await screen.findByText('Policy Inventory');
    await user.click(screen.getByRole('button', { name: 'Activate Policy' }));

    await waitFor(() => {
      expect(mocks.updatePolicyStatus).toHaveBeenCalledWith('policy-1', 1, 'active');
    });
    await waitFor(() => {
      expect(mocks.listPolicies).toHaveBeenCalledTimes(2);
    });
    expect(mocks.toastSuccess).toHaveBeenCalledWith('Policy activated', {
      description: 'Orders Policy v1 is now ACTIVE',
    });
  });

  it('confirms before deleting and refetches after delete', async () => {
    const user = userEvent.setup();

    render(<SchemaPolicies />);

    await screen.findByText('Policy Inventory');
    await user.click(screen.getByRole('button', { name: 'Delete Policy' }));

    await waitFor(() => {
      expect(mocks.confirmSchemaGovernanceAction).toHaveBeenCalledWith(
        'Are you sure you want to delete policy "Orders Policy"?',
      );
    });
    expect(mocks.deletePolicy).toHaveBeenCalledWith('policy-1');
    await waitFor(() => {
      expect(mocks.listPolicies).toHaveBeenCalledTimes(2);
    });
    expect(mocks.toastSuccess).toHaveBeenCalledWith('Policy deleted', {
      description: 'Orders Policy deleted',
    });
  });
});
