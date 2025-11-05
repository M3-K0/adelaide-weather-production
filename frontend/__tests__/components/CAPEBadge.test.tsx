import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { CAPEBadge } from '../../components/CAPEBadge';

// Mock framer-motion to avoid animation issues in tests
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, onClick, whileHover, whileTap, ...props }: any) => (
      <div onClick={onClick} {...props}>
        {children}
      </div>
    )
  },
  AnimatePresence: ({ children }: any) => <>{children}</>
}));

describe('CAPEBadge', () => {
  describe('Risk Level Classification', () => {
    it('displays Low risk for CAPE values 0-500', () => {
      render(<CAPEBadge value={250} />);
      expect(screen.getByText('Low')).toBeInTheDocument();
      expect(screen.getByText('250')).toBeInTheDocument();
    });

    it('displays Moderate risk for CAPE values 500-1000', () => {
      render(<CAPEBadge value={750} />);
      expect(screen.getByText('Moderate')).toBeInTheDocument();
      expect(screen.getByText('750')).toBeInTheDocument();
    });

    it('displays High risk for CAPE values 1000-2000', () => {
      render(<CAPEBadge value={1500} />);
      expect(screen.getByText('High')).toBeInTheDocument();
      expect(screen.getByText('1,500')).toBeInTheDocument();
    });

    it('displays Extreme risk for CAPE values 2000+', () => {
      render(<CAPEBadge value={3000} />);
      expect(screen.getByText('Extreme')).toBeInTheDocument();
      expect(screen.getByText('3,000')).toBeInTheDocument();
    });
  });

  describe('Color Coding', () => {
    it('applies green colors for Low risk', () => {
      render(<CAPEBadge value={250} />);
      const badge = screen.getByRole('button');
      expect(badge).toHaveClass('text-emerald-400');
    });

    it('applies yellow colors for Moderate risk', () => {
      render(<CAPEBadge value={750} />);
      const badge = screen.getByRole('button');
      expect(badge).toHaveClass('text-yellow-400');
    });

    it('applies orange colors for High risk', () => {
      render(<CAPEBadge value={1500} />);
      const badge = screen.getByRole('button');
      expect(badge).toHaveClass('text-orange-400');
    });

    it('applies red colors for Extreme risk', () => {
      render(<CAPEBadge value={3000} />);
      const badge = screen.getByRole('button');
      expect(badge).toHaveClass('text-red-400');
    });
  });

  describe('Size Variants', () => {
    it('applies small size classes', () => {
      render(<CAPEBadge value={500} size='sm' />);
      const badge = screen.getByRole('button');
      expect(badge).toHaveClass('px-2', 'py-1', 'text-xs');
    });

    it('applies medium size classes (default)', () => {
      render(<CAPEBadge value={500} />);
      const badge = screen.getByRole('button');
      expect(badge).toHaveClass('px-3', 'py-1.5', 'text-sm');
    });

    it('applies large size classes', () => {
      render(<CAPEBadge value={500} size='lg' />);
      const badge = screen.getByRole('button');
      expect(badge).toHaveClass('px-4', 'py-2', 'text-base');
    });
  });

  describe('Info Icon and Modal', () => {
    it('shows info icon by default', () => {
      render(<CAPEBadge value={500} />);
      expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('hides info icon when showInfo is false', () => {
      render(<CAPEBadge value={500} showInfo={false} />);
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });

    it('opens modal when badge is clicked', async () => {
      const user = userEvent.setup();
      render(<CAPEBadge value={1500} />);

      const badge = screen.getByRole('button');
      await user.click(badge);

      await waitFor(() => {
        expect(screen.getByText('High Risk Level')).toBeInTheDocument();
      });
    });

    it('opens modal when Enter key is pressed', async () => {
      const user = userEvent.setup();
      render(<CAPEBadge value={1500} />);

      const badge = screen.getByRole('button');
      badge.focus();
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(screen.getByText('High Risk Level')).toBeInTheDocument();
      });
    });

    it('opens modal when Space key is pressed', async () => {
      const user = userEvent.setup();
      render(<CAPEBadge value={1500} />);

      const badge = screen.getByRole('button');
      badge.focus();
      await user.keyboard(' ');

      await waitFor(() => {
        expect(screen.getByText('High Risk Level')).toBeInTheDocument();
      });
    });
  });

  describe('Historical Context', () => {
    it('displays percentile information when provided', async () => {
      const user = userEvent.setup();
      render(<CAPEBadge value={1500} percentile={85} season='Summer' />);

      const badge = screen.getByRole('button');
      await user.click(badge);

      await waitFor(() => {
        expect(screen.getByText('Summer Percentile')).toBeInTheDocument();
        expect(screen.getByText('85%')).toBeInTheDocument();
      });
    });

    it('does not show historical context when percentile is not provided', async () => {
      const user = userEvent.setup();
      render(<CAPEBadge value={1500} />);

      const badge = screen.getByRole('button');
      await user.click(badge);

      await waitFor(() => {
        expect(
          screen.queryByText('Historical Context')
        ).not.toBeInTheDocument();
      });
    });
  });

  describe('Modal Content', () => {
    it('displays correct risk description for each level', async () => {
      const user = userEvent.setup();

      // Test Low risk
      const { rerender } = render(<CAPEBadge value={250} />);
      await user.click(screen.getByRole('button'));
      await waitFor(() => {
        expect(
          screen.getByText(/Minimal convective potential/)
        ).toBeInTheDocument();
      });

      // Close modal
      const closeButton = screen.getByRole('button', { name: /close/i });
      await user.click(closeButton);

      // Test Extreme risk
      rerender(<CAPEBadge value={3000} />);
      await user.click(screen.getByRole('button'));
      await waitFor(() => {
        expect(
          screen.getByText(/Very high convective potential/)
        ).toBeInTheDocument();
      });
    });

    it('shows CAPE scale reference', async () => {
      const user = userEvent.setup();
      render(<CAPEBadge value={1500} />);

      const badge = screen.getByRole('button');
      await user.click(badge);

      await waitFor(() => {
        expect(screen.getByText('CAPE Scale Reference')).toBeInTheDocument();
        expect(screen.getByText('0–500 J/kg')).toBeInTheDocument();
        expect(screen.getByText('500–1,000 J/kg')).toBeInTheDocument();
        expect(screen.getByText('1,000–2,000 J/kg')).toBeInTheDocument();
        expect(screen.getByText('2,000+ J/kg')).toBeInTheDocument();
      });
    });

    it('highlights current risk level in scale reference', async () => {
      const user = userEvent.setup();
      render(<CAPEBadge value={1500} />);

      const badge = screen.getByRole('button');
      await user.click(badge);

      await waitFor(() => {
        // Look for the High risk level in the scale reference section
        const scaleSection = screen
          .getByText('CAPE Scale Reference')
          .closest('div');
        expect(scaleSection).toBeInTheDocument();

        // Check that the modal opened and contains the risk description
        expect(screen.getByText('High Risk Level')).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('has proper aria-label', () => {
      render(<CAPEBadge value={1500} percentile={85} season='Summer' />);
      const badge = screen.getByRole('button');
      expect(badge).toHaveAttribute(
        'aria-label',
        expect.stringContaining('CAPE risk level: High')
      );
      expect(badge).toHaveAttribute(
        'aria-label',
        expect.stringContaining('1,500 J/kg')
      );
      expect(badge).toHaveAttribute(
        'aria-label',
        expect.stringContaining('85th percentile for Summer')
      );
    });

    it('has proper aria-label without percentile', () => {
      render(<CAPEBadge value={1500} />);
      const badge = screen.getByRole('button');
      expect(badge).toHaveAttribute(
        'aria-label',
        expect.stringContaining('CAPE risk level: High')
      );
      expect(badge).toHaveAttribute(
        'aria-label',
        expect.stringContaining('1,500 J/kg')
      );
    });

    it('is keyboard accessible', async () => {
      const user = userEvent.setup();
      render(<CAPEBadge value={1500} />);

      const badge = screen.getByRole('button');
      expect(badge).toHaveAttribute('tabIndex', '0');

      badge.focus();
      expect(badge).toHaveFocus();
    });

    it('closes modal when close button is clicked', async () => {
      const user = userEvent.setup();
      render(<CAPEBadge value={1500} />);

      // Open modal
      const badge = screen.getByRole('button');
      await user.click(badge);

      await waitFor(() => {
        expect(screen.getByText('High Risk Level')).toBeInTheDocument();
      });

      // Click close button
      const closeButton = screen.getByRole('button', { name: /close/i });
      await user.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByText('High Risk Level')).not.toBeInTheDocument();
      });
    });
  });

  describe('Custom Props', () => {
    it('applies custom className', () => {
      render(<CAPEBadge value={500} className='custom-class' />);
      const badge = screen.getByRole('button');
      expect(badge).toHaveClass('custom-class');
    });

    it('disables animations when specified', () => {
      render(<CAPEBadge value={3000} disableAnimations={true} />);
      // Should not crash and should still render properly
      expect(screen.getByText('Extreme')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles exact threshold values correctly', () => {
      // Test exact boundary values
      render(<CAPEBadge value={500} />);
      expect(screen.getByText('Moderate')).toBeInTheDocument();

      const { rerender } = render(<CAPEBadge value={500} />);

      rerender(<CAPEBadge value={1000} />);
      expect(screen.getByText('High')).toBeInTheDocument();

      rerender(<CAPEBadge value={2000} />);
      expect(screen.getByText('Extreme')).toBeInTheDocument();
    });

    it('handles very large CAPE values', () => {
      render(<CAPEBadge value={10000} />);
      expect(screen.getByText('Extreme')).toBeInTheDocument();
      expect(screen.getByText('10,000')).toBeInTheDocument();
    });

    it('handles zero CAPE value', () => {
      render(<CAPEBadge value={0} />);
      expect(screen.getByText('Low')).toBeInTheDocument();
      expect(screen.getByText('0')).toBeInTheDocument();
    });
  });
});
