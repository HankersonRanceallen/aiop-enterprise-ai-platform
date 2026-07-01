"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { MessageSquare, FileText, LayoutDashboard, LogOut, Workflow, FlaskConical } from "lucide-react";
import { clearTokens } from "@/lib/auth";
import clsx from "clsx";

const navItems = [
  { href: "/chat",      label: "Chat",      icon: MessageSquare },
  { href: "/agents",    label: "Agents",    icon: Workflow },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/mlops",     label: "MLOps",     icon: FlaskConical },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  function handleLogout() {
    clearTokens();
    router.push("/login");
  }

  return (
    <aside className="w-56 flex-shrink-0 bg-white border-r border-gray-100 flex flex-col h-screen">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
            <span className="text-white text-xs font-bold">AI</span>
          </div>
          <span className="font-semibold text-gray-900 text-sm">AIOP</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {navItems.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
              pathname.startsWith(href)
                ? "bg-primary-50 text-primary-700"
                : "text-gray-600 hover:bg-gray-50"
            )}
          >
            <Icon className="w-4 h-4" />
            {label}
          </Link>
        ))}
      </nav>

      {/* Logout */}
      <div className="px-2 py-4 border-t border-gray-100">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-gray-500 hover:bg-gray-50 w-full transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
