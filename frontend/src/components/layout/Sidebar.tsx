import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Database, LayoutDashboard, MessageSquare, Link as LinkIcon, ShieldCheck, Languages, Users } from 'lucide-react';

// ... inside Sidebar ...
const Sidebar = () => {
  const { i18n } = useTranslation();
  const toggleLanguage = () => {
    i18n.changeLanguage(i18n.language === 'ko' ? 'en' : 'ko');
  };

  return (
    <aside className="w-64 bg-white border-r border-slate-200 min-h-screen flex flex-col fixed left-0 top-0 z-10">
      <div className="p-6 border-b border-slate-100 flex items-center gap-3">
        <div className="bg-indigo-600 p-2 rounded-lg">
          <Database className="w-6 h-6 text-white" />
        </div>
        <span className="font-bold text-xl text-slate-800 tracking-tight">Kafka Gov</span>
      </div>

      <nav className="flex-1 p-4 space-y-6">
          <div className="space-y-1">
            <NavItem to="/topics" icon={MessageSquare} label="Topics" />
            <NavItem to="/schemas" icon={Database} label="Schema Registry" />
            <NavItem to="/consumers" icon={Users} label="Consumers" />
          </div>

        <div className="space-y-4">
          <div className="px-4 flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            Governance
          </div>
          <div className="space-y-1">
            <NavItem to="/governance/dashboard" icon={LayoutDashboard} label="Dashboard" />
            <NavItem to="/schemas/policies" icon={ShieldCheck} label="Schema Policies" />
            <NavItem to="/policies" icon={ShieldCheck} label="Topic Policies" />
          </div>
        </div>

        <div className="space-y-1 pt-4 border-t border-slate-100">
          <NavItem to="/connections" icon={LinkIcon} label="Connections" />
        </div>
      </nav>

      <div className="p-4 border-t border-slate-100 space-y-2">
        <button
          type="button"
          onClick={toggleLanguage}
          className="flex items-center gap-3 px-4 py-2 w-full text-sm font-medium text-slate-600 hover:bg-slate-50 rounded-lg transition-colors"
        >
          <Languages className="w-5 h-5" />
          {i18n.language === 'ko' ? 'English' : '한국어'}
        </button>
        <div className="flex items-center gap-3 px-4 py-2">
          <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center font-bold text-slate-500 text-xs">
            AD
          </div>
          <div>
            <p className="text-sm font-medium text-slate-700">Admin User</p>
            <p className="text-xs text-slate-400">admin@example.com</p>
          </div>
        </div>
      </div>
    </aside>
  );
};

const NavItem = ({
  to,
  icon: Icon,
  label,
}: {
  to: string;
  icon: React.ElementType;
  label: string;
}) => (
  <NavLink
    to={to}
    className={({ isActive }) =>
      `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${isActive
        ? 'bg-indigo-50 text-indigo-700'
        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
      }`
    }
  >
    <Icon className="w-5 h-5" />
    {label}
  </NavLink>
);

export default function Layout() {
  return (
    <div className="min-h-screen bg-slate-50 flex">
      <Sidebar />
      <main className="flex-1 ml-64 p-8">
        <Outlet />
      </main>
    </div>
  );
}
