import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FlaskConical,
  Bot,
  Package,
  FolderTree,
  Github,
} from 'lucide-react';
import { cn } from '../../lib/utils';
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

  return (
    <div className="flex h-screen w-48 flex-col bg-card">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-3 py-3 border-b border-border">
        <Link to="/" className="flex items-center gap-2.5">
          <img
            src={logoImage}
            alt="AlphaTrion Logo"
            className="h-8 w-8"
          />
          <h1 className="text-lg font-bold text-foreground">AlphaTrion</h1>
        </Link>
      </div>

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

      {/* Footer - GitHub and Version */}
      <div className="px-3 py-3 border-t border-border mt-auto">
        <div className="flex items-center gap-2 px-1 justify-center">
          <a
            href="https://github.com/InftyAI/alphatrion"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center h-6 w-6 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
            title="View on GitHub"
          >
            <Github className="h-4 w-4" />
          </a>
          <span className="text-xs text-muted-foreground font-mono">{__APP_VERSION__}</span>
        </div>
      </div>
    </div>
  );
}
