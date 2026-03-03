import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FlaskConical,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import logoImage from '../../assets/logo.svg';

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
];

export function Sidebar() {
  const location = useLocation();

  return (
    <div className="flex h-screen w-48 flex-col bg-card">
      {/* Logo */}
      <Link to="/" className="flex h-12 items-center px-3 hover:bg-accent/50 transition-colors">
        <img
          src={logoImage}
          alt="Hiverge Logo"
          className="h-6 w-auto"
        />
      </Link>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {navItems.map((item) => {
          const Icon = item.icon;

          // Check if current route matches this nav item
          // Special case: /runs/[id] should also highlight "Experiments" nav item
          const isActive =
            location.pathname === item.href ||
            (item.href !== '/' && location.pathname.startsWith(item.href)) ||
            (item.href === '/experiments' && location.pathname.startsWith('/runs'));

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
    </div>
  );
}
