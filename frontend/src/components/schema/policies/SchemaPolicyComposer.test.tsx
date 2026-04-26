import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import SchemaPolicyComposer from './SchemaPolicyComposer';

const mocks = vi.hoisted(() => ({
  toastError: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: {
    error: mocks.toastError,
    success: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  },
}));

describe('SchemaPolicyComposer', () => {
  it('shows a toast instead of submitting when JSON content is invalid', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    render(
      <SchemaPolicyComposer
        isOpen
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    await user.click(screen.getByRole('button', { name: /Strict Production \(Shield\)/ }));
    fireEvent.change(screen.getByLabelText('Policy Content (JSON)'), {
      target: { value: '{invalid json' },
    });
    await user.click(screen.getByRole('button', { name: 'Save Policy' }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(mocks.toastError).toHaveBeenCalledWith('Policy content must be valid JSON', expect.any(Object));
  });

  it('submits parsed policy content for a valid policy draft', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn();

    render(
      <SchemaPolicyComposer
        isOpen
        onClose={onClose}
        onSubmit={onSubmit}
      />,
    );

    await user.click(screen.getByRole('button', { name: /Strict Production \(Shield\)/ }));
    await user.click(screen.getByRole('button', { name: 'Save Policy' }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      name: 'Strict Production (Shield)',
      policy_type: 'lint',
      target_environment: 'total',
      created_by: 'admin@example.com',
    });
    expect(onClose).toHaveBeenCalled();
  });
});
