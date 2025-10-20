import { useState, useCallback } from "react";
import type { Toast, ToastType } from "../components/ui/Toast";

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((type: ToastType, title: string, message?: string, duration?: number) => {
    const id = `toast-${Date.now()}-${Math.random()}`;
    const newToast: Toast = {
      id,
      type,
      title,
      message,
      duration: duration || 5000,
    };

    setToasts((prev) => [...prev, newToast]);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const toast = {
    success: (title: string, message?: string, duration?: number) => 
      addToast("success", title, message, duration),
    error: (title: string, message?: string, duration?: number) => 
      addToast("error", title, message, duration),
    info: (title: string, message?: string, duration?: number) => 
      addToast("info", title, message, duration),
    warning: (title: string, message?: string, duration?: number) => 
      addToast("warning", title, message, duration),
  };

  return {
    toasts,
    toast,
    removeToast,
  };
}
