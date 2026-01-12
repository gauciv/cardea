import { Sidebar } from './Sidebar';
import { useAuth } from '../lib/useAuth';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      <Sidebar user={user} />
      <div className="pl-14 min-h-screen">
        {children}
      </div>
    </div>
  );
};
