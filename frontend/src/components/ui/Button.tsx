import { forwardRef, type ButtonHTMLAttributes, type ElementType } from "react";
import { cn } from "../../utils/cn";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger" | "success";
  size?: "sm" | "md" | "lg";
  icon?: ElementType;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", icon: Icon, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50",
          {
            "bg-[#0969da] text-white shadow-sm hover:bg-[#0861cc]": variant === "primary",
            "border border-[#d0d7de] bg-[#f6f8fa] text-[#24292f] shadow-sm hover:bg-[#f3f4f6]":
              variant === "secondary",
            "border border-[#d0d7de] text-[#0969da] hover:bg-[#f6f8fa]":
              variant === "outline",
            "text-slate-500 hover:bg-slate-100 hover:text-slate-900": variant === "ghost",
            "bg-[#cf222e] text-white shadow-sm hover:bg-[#a40e26]": variant === "danger",
            "bg-[#1a7f37] text-white shadow-sm hover:bg-[#11632c]": variant === "success",
          },
          {
            "px-3 py-1.5 text-xs": size === "sm",
            "px-4 py-2 text-sm": size === "md",
            "px-6 py-3 text-base": size === "lg",
          },
          className,
        )}
        {...props}
      >
        {Icon && <Icon className={cn("h-4 w-4", size === "lg" && "h-5 w-5")} />}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";

export default Button;
