import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  LayoutDashboard,
  List,
  FileCode,
  Plug,
  Server,
  Shield,
  Activity,
  History as HistoryIcon,
  Users,
} from "lucide-react";
import { cn } from "../../utils/cn";

export default function Sidebar() {
  const { t } = useTranslation();
  
  const navigation = [
    { name: t("nav.dashboard"), to: "/", icon: LayoutDashboard },
    { name: t("nav.topics"), to: "/topics", icon: List },
    { name: t("nav.schemas"), to: "/schemas", icon: FileCode },
    { name: t("nav.kafkaConnect"), to: "/connect", icon: Plug },
    { name: t("nav.connections"), to: "/connections", icon: Server },
    { name: t("nav.policies"), to: "/policies", icon: Shield },
    { name: t("nav.analysis"), to: "/analysis", icon: Activity },
    { name: "Team Analytics", to: "/team-analytics", icon: Users },
    { name: t("nav.history"), to: "/history", icon: HistoryIcon },
  ];
  return (
    <div className="flex h-screen w-64 flex-col fixed left-0 top-0 bg-gray-900 text-white">
      {/* Logo */}
      <div className="flex h-16 items-center justify-center border-b border-gray-800">
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-blue-600 p-2">
            <Server className="h-6 w-6" />
          </div>
          <span className="text-xl font-bold">Kafka Gov</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-4 overflow-y-auto">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors",
                isActive
                  ? "bg-blue-600 text-white"
                  : "text-gray-300 hover:bg-gray-800 hover:text-white"
              )
            }
          >
            <item.icon className="h-5 w-5" />
            {item.name}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-800 p-4">
        <div className="text-xs text-gray-400">
          <div>Kafka Governance</div>
          <div className="mt-1">v0.1.0</div>
        </div>
      </div>
    </div>
  );
}
