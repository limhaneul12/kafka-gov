import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "../../utils/cn";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?:
    | "default"
    | "success"
    | "warning"
    | "danger"
    | "error"
    | "info"
    | "secondary"
    | "outline";
}

const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = "default", children, ...props }, ref) => {
    return (
      <span
        ref={ref}
        className={cn(
          "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
          {
            "bg-gray-100 text-gray-800": variant === "default",
            "bg-green-100 text-green-800": variant === "success",
            "bg-yellow-100 text-yellow-800": variant === "warning",
            "bg-red-100 text-red-800": variant === "danger" || variant === "error",
            "bg-blue-100 text-blue-800": variant === "info",
            "bg-slate-100 text-slate-700": variant === "secondary",
            "bg-white text-gray-700 ring-1 ring-inset ring-gray-200": variant === "outline",
          },
          className
        )}
        {...props}
      >
        {children}
      </span>
    );
  }
);

Badge.displayName = "Badge";

export default Badge;
