import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  List,
  FileCode,
  Plug,
  Server,
  Shield,
  Activity,
} from "lucide-react";
import { cn } from "../../utils/cn";

const navigation = [
  { name: "Dashboard", to: "/", icon: LayoutDashboard },
  { name: "Topics", to: "/topics", icon: List },
  { name: "Schemas", to: "/schemas", icon: FileCode },
  { name: "Kafka Connect", to: "/connect", icon: Plug },
  { name: "Connections", to: "/connections", icon: Server },
  { name: "Policies", to: "/policies", icon: Shield },
  { name: "Analysis", to: "/analysis", icon: Activity },
];

export default function Sidebar() {
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
