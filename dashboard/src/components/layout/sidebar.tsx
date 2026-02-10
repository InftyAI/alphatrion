import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderKanban,
  Package,
  Github,
  User as UserIcon,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useCurrentUser } from '../../context/user-context';
import logoImage from '../../assets/logo.png';

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  description?: string;
}

const navItems: NavItem[] = [
  {
    title: 'Dashboard',
    href: '/',
    icon: LayoutDashboard,
    description: 'Overview and statistics',
  },
  {
    title: 'Projects',
    href: '/projects',
    icon: FolderKanban,
    description: 'Browse projects, experiments, and runs',
  },
  {
    title: 'Artifacts',
    href: '/artifacts',
    icon: Package,
    description: 'ORAS registry artifacts',
  },
];

export function Sidebar() {
  const location = useLocation();
  const user = useCurrentUser();
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  return (
    <div className="flex h-screen w-64 flex-col border-r bg-card">
      {/* Logo */}
      <Link to="/" className="flex h-16 items-center gap-3 border-b px-6 hover:bg-accent/50 transition-colors">
        <img
          src={logoImage}
          alt="AlphaTrion Logo"
          className="h-8 w-8"
        />
        <h1 className="text-xl font-bold text-foreground">AlphaTrion</h1>
      </Link>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            location.pathname === item.href ||
            (item.href !== '/' && location.pathname.startsWith(item.href));

          return (
            <Link
              key={item.href}
              to={item.href}
              className={cn(
                'flex flex-col gap-1 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
              )}
            >
              <div className="flex items-center gap-3">
                <Icon className="h-5 w-5" />
                {item.title}
              </div>
              {item.description && (
                <span className="text-xs text-muted-foreground pl-8">
                  {item.description}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer with User Avatar and GitHub */}
      <div className="relative border-t p-3">
        <div className="flex items-center justify-between gap-3">
          {/* User Avatar with Username (clickable) */}
          <button
            onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
            className="flex items-center gap-2.5 flex-1 min-w-0 hover:bg-accent/50 rounded-md px-2 py-1.5 transition-colors"
            title="User menu"
          >
            {user.avatarUrl ? (
              <img
                src={user.avatarUrl}
                alt={user.username}
                className="h-7 w-7 rounded-full object-cover flex-shrink-0"
              />
            ) : (
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground flex-shrink-0">
                <UserIcon className="h-3.5 w-3.5" />
              </div>
            )}
            <span className="text-xs font-medium text-foreground truncate">{user.username}</span>
          </button>

          {/* GitHub and Version */}
          <div className="flex items-center gap-1 flex-shrink-0">
            <a
              href="https://github.com/InftyAI/alphatrion"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center h-7 w-7 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
              title="View on GitHub"
            >
              <Github className="h-4 w-4" />
            </a>
            <span className="text-xs text-muted-foreground font-medium">{__APP_VERSION__}</span>
          </div>
        </div>

        {/* User Info Popup */}
        {isUserMenuOpen && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-40"
              onClick={() => setIsUserMenuOpen(false)}
            />

            {/* Popup Menu */}
            <div className="absolute bottom-full left-4 mb-2 z-50 w-72 rounded-lg border bg-card shadow-lg overflow-hidden">
              <div className="p-4">
                <div className="flex items-center gap-3">
                  {user.avatarUrl ? (
                    <img
                      src={user.avatarUrl}
                      alt={user.username}
                      className="h-12 w-12 rounded-full object-cover"
                    />
                  ) : (
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground">
                      <UserIcon className="h-6 w-6" />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-foreground break-words">{user.username}</p>
                    <p className="text-xs text-muted-foreground break-words">{user.email}</p>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
