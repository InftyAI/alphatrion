import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FlaskConical,
  Bot,
  Package,
  FolderTree,
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
  },
  {
    title: 'Experiments',
    href: '/experiments',
    icon: FlaskConical,
  },
  {
    title: 'Agents',
    href: '/agents',
    icon: Bot,
  },
  {
    title: 'Datasets',
    href: '/datasets',
    icon: FolderTree,
  },
  {
    title: 'Artifacts',
    href: '/artifacts',
    icon: Package,
  },
];

export function Sidebar() {
  const location = useLocation();
  const user = useCurrentUser();
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  return (
    <div className="flex h-screen w-48 flex-col bg-card">
      {/* Logo */}
      <Link to="/" className="flex h-14 items-center gap-2 px-3 hover:bg-accent/50 transition-colors">
        <img
          src={logoImage}
          alt="AlphaTrion Logo"
          className="h-6 w-6"
        />
        <h1 className="text-base font-bold text-foreground">AlphaTrion</h1>
      </Link>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {navItems.map((item) => {
          const Icon = item.icon;

          // Special handling for Experiments: also active when on runs pages
          // since runs are conceptually part of experiments
          let isActive =
            location.pathname === item.href ||
            (item.href !== '/' && location.pathname.startsWith(item.href));

          if (item.href === '/experiments') {
            isActive = isActive ||
              location.pathname.startsWith('/runs');
          }

          return (
            <Link
              key={item.href}
              to={item.href}
              className={cn(
                'flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors relative',
                isActive
                  ? 'bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400'
                  : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
              )}
            >
              {isActive && (
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-600 dark:bg-blue-400 rounded-r" />
              )}
              <Icon className={cn('h-4 w-4 ml-1', isActive && 'text-blue-600 dark:text-blue-400')} />
              {item.title}
            </Link>
          );
        })}
      </nav>

      {/* Footer with User Avatar and GitHub */}
      <div className="relative p-3 mt-auto">
        <div className="flex items-center justify-between gap-2 hover:bg-accent/50 rounded-lg px-2 py-2 transition-colors">
          {/* User Avatar (clickable) */}
          <button
            onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
            className="flex items-center"
            title="User menu"
          >
            {user.avatarUrl ? (
              <img
                src={user.avatarUrl}
                alt={user.name}
                className="h-7 w-7 rounded-full object-cover flex-shrink-0"
              />
            ) : (
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground flex-shrink-0">
                <UserIcon className="h-3.5 w-3.5" />
              </div>
            )}
          </button>

          {/* GitHub and Version */}
          <div className="flex items-center gap-0.5 flex-shrink-0">
            <a
              href="https://github.com/InftyAI/alphatrion"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center h-6 w-6 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
              title="View on GitHub"
            >
              <Github className="h-3.5 w-3.5" />
            </a>
            <span className="text-xs text-muted-foreground font-mono">{__APP_VERSION__}</span>
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
                      alt={user.name}
                      className="h-12 w-12 rounded-full object-cover"
                    />
                  ) : (
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground">
                      <UserIcon className="h-6 w-6" />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-foreground break-words">{user.name}</p>
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
