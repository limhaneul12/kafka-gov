import React from 'react';
import { cn } from '../../utils/cn';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
    variant?: 'default' | 'success' | 'warning' | 'error' | 'info' | 'outline' | 'secondary';
}

export const Badge = ({ className, variant = 'default', children, ...props }: BadgeProps) => {
    const variants = {
        default: 'bg-[#f6f8fa] text-[#24292f] border border-[#d0d7de]',
        success: 'bg-[#dafbe1] text-[#1a7f37] border border-[#d0d7de]',
        warning: 'bg-[#fff8c5] text-[#9a6700] border border-[#d0d7de]',
        error: 'bg-[#ffebe9] text-[#cf222e] border border-[#d0d7de]',
        info: 'bg-[#ddf4ff] text-[#0969da] border border-[#d0d7de]',
        outline: 'border border-[#d0d7de] text-[#57606a] bg-transparent',
        secondary: 'bg-[#afb8c133] text-[#24292f]',
    };

    return (
        <span
            className={cn(
                'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium tracking-tight border',
                variants[variant],
                className
            )}
            {...props}
        >
            {children}
        </span>
    );
};
