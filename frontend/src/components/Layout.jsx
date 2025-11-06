import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { PhoneCall, LogOut, LayoutDashboard, FileText, Upload, FileAudio, BarChart2, User } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, isManager, isAuditor } = useAuth();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  // Dynamic menu items based on role
  const getMenuItems = () => {
    const items = [];
    
    if (isManager()) {
      items.push(
        { path: "/manager", label: "Manager Analytics", icon: BarChart2, testId: "nav-manager" }
      );
    }
    
    if (isAuditor()) {
      items.push(
        { path: "/auditor", label: "My Performance", icon: LayoutDashboard, testId: "nav-auditor" }
      );
    }
    
    // Common items
    items.push(
      { path: "/scripts", label: "Scripts", icon: FileText, testId: "nav-scripts" },
      { path: "/upload", label: "Upload Audio", icon: Upload, testId: "nav-upload" },
      { path: "/audits", label: "Audit Results", icon: FileAudio, testId: "nav-audits" }
    );
    
    return items;
  };

  const menuItems = getMenuItems();

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-lg flex items-center justify-center">
              <PhoneCall className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-lg" style={{ fontFamily: 'Space Grotesk' }}>Telecalling</h1>
              <p className="text-xs text-gray-600">Auditor</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <button
                key={item.path}
                data-testid={item.testId}
                onClick={() => navigate(item.path)}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                  isActive
                    ? "bg-gradient-to-r from-indigo-600 to-purple-600 text-white"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="font-medium">{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="p-4 border-t border-gray-200">
          <Button
            data-testid="logout-button"
            onClick={handleLogout}
            variant="outline"
            className="w-full"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Logout
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-8 overflow-auto" style={{ background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)' }}>
        <Outlet />
      </main>
    </div>
  );
}
