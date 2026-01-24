import React from 'react';
import { cn } from '../../utils/cn';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    icon?: React.ElementType;
    containerClassName?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
    ({ className, icon: Icon, containerClassName, ...props }, ref) => {
        return (
            <div className={cn('relative', containerClassName)}>
                {Icon && (
                    <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
                        <Icon className="w-5 h-5" />
                    </div>
                )}
                <input
                    ref={ref}
                    className={cn(
                        'w-full rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50',
                        Icon && 'pl-10',
                        className
                    )}
                    {...props}
                />
            </div>
        );
    }
);
