import React from 'react';
import { cn } from '../../utils/cn';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success';
    size?: 'sm' | 'md' | 'lg';
    icon?: React.ElementType;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant = 'primary', size = 'md', icon: Icon, children, ...props }, ref) => {
        const variants = {
            primary: 'bg-[#0969da] text-white hover:bg-[#0861cc] shadow-sm',
            secondary: 'bg-[#f6f8fa] text-[#24292f] border border-[#d0d7de] hover:bg-[#f3f4f6] shadow-sm',
            outline: 'border border-[#d0d7de] text-[#0969da] hover:bg-[#f6f8fa]',
            ghost: 'text-slate-500 hover:text-slate-900 hover:bg-slate-100',
            danger: 'bg-[#cf222e] text-white hover:bg-[#a40e26] shadow-sm',
            success: 'bg-[#1a7f37] text-white hover:bg-[#11632c] shadow-sm',
        };

        const sizes = {
            sm: 'px-3 py-1.5 text-xs',
            md: 'px-4 py-2 text-sm',
            lg: 'px-6 py-3 text-base',
        };

        return (
            <button
                ref={ref}
                className={cn(
                    'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed',
                    variants[variant],
                    sizes[size],
                    className
                )}
                {...props}
            >
                {Icon && <Icon className={cn('w-4 h-4', size === 'lg' && 'w-5 h-5')} />}
                {children}
            </button>
        );
    }
);
