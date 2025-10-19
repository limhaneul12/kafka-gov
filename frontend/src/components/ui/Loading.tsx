import { Loader2 } from "lucide-react";
import { cn } from "../../utils/cn";

interface LoadingProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

export default function Loading({ size = "md", className }: LoadingProps) {
  return (
    <div className={cn("flex items-center justify-center", className)}>
      <Loader2
        className={cn("animate-spin text-blue-600", {
          "h-4 w-4": size === "sm",
          "h-8 w-8": size === "md",
          "h-12 w-12": size === "lg",
        })}
      />
    </div>
  );
}
