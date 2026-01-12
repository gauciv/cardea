import { useEffect } from 'react';
import { XCircle, CheckCircle2, X } from 'lucide-react';

interface ToastProps {
  message: string;
  type: "error" | "success";
  onDismiss: () => void;
}

export const Toast: React.FC<ToastProps> = ({ message, type, onDismiss }) => {
  useEffect(() => {
    if (type === "success") {
      const t = setTimeout(onDismiss, 3000);
      return () => clearTimeout(t);
    }
  }, [type, onDismiss]);

  return (
    <div className={`fixed bottom-4 right-4 z-50 ${type === "error" ? "bg-red-950/95 border-red-800" : "bg-green-950/95 border-green-800"} border rounded-lg px-4 py-3 flex items-center gap-3 animate-in slide-in-from-bottom-2`}>
      {type === "error" ? <XCircle className="w-4 h-4 text-red-400" /> : <CheckCircle2 className="w-4 h-4 text-green-400" />}
      <span className="text-sm">{message}</span>
      <button onClick={onDismiss} className="text-slate-500 hover:text-white ml-2">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};
