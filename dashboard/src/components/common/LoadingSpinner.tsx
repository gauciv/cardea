import { Shield, RefreshCw } from 'lucide-react';

interface LoadingSpinnerProps {
  fullScreen?: boolean;
  size?: 'sm' | 'md' | 'lg';
  showLogo?: boolean;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  fullScreen = false, 
  size = 'md',
  showLogo = false 
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-10 h-10'
  };

  const spinner = showLogo ? (
    <Shield className={`${sizeClasses[size]} text-cyan-500 animate-pulse`} />
  ) : (
    <RefreshCw className={`${sizeClasses[size]} text-slate-600 animate-spin`} />
  );

  if (fullScreen) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        {spinner}
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center py-20">
      {spinner}
    </div>
  );
};
