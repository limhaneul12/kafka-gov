import { Settings, User } from "lucide-react";
import { Link } from "react-router-dom";

export default function Header() {
  return (
    <header className="fixed top-0 left-64 right-0 h-16 bg-white border-b border-gray-200 z-10">
      <div className="flex h-full items-center justify-between px-6">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-semibold text-gray-800">
            Kafka Governance Platform
          </h1>
        </div>

        <div className="flex items-center gap-4">
          <Link
            to="/settings"
            className="rounded-lg p-2 text-gray-600 hover:bg-gray-100 transition-colors"
            title="Settings"
          >
            <Settings className="h-5 w-5" />
          </Link>
          
          <div className="flex items-center gap-2 rounded-lg bg-gray-100 px-3 py-2">
            <User className="h-5 w-5 text-gray-600" />
            <span className="text-sm font-medium text-gray-700">Admin</span>
          </div>
        </div>
      </div>
    </header>
  );
}
