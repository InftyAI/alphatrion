import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, ChevronDown, Building2, Check, Users, Key } from 'lucide-react';
import { useCurrentUser } from '../../context/user-context';
import { useTeams } from '../../hooks/use-teams';
import { useTeamContext } from '../../context/team-context';
import { useOrganization } from '../../hooks/use-organization';
import { cn } from '../../lib/utils';

// Use runtime config (Kubernetes) > build-time env (Docker) > localhost dev
const getApiBaseUrl = () => {
  // @ts-ignore - window.ENV is injected at runtime by entrypoint.sh
  if (typeof window !== 'undefined' && window.ENV?.VITE_API_URL) {
    // @ts-ignore
    return window.ENV.VITE_API_URL;
  }
  return import.meta.env.VITE_API_URL || 'http://localhost:8000';
};

export function UserProfile() {
  const [isOpen, setIsOpen] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const currentUser = useCurrentUser();
  const navigate = useNavigate();
  const { data: teams } = useTeams();
  const { selectedTeamId, setSelectedTeamId } = useTeamContext();

  // Get selected team and organization
  const selectedTeam = teams?.find((team) => team.id === selectedTeamId);
  const { data: organization } = useOrganization(selectedTeam?.orgId);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    // Clear authentication data
    localStorage.removeItem('alphatrion_token');
    localStorage.removeItem('alphatrion_user');
    localStorage.removeItem('alphatrion_user_id');
    localStorage.removeItem('alphatrion_org_id');
    localStorage.removeItem('alphatrion_team_id');

    // Redirect to login
    navigate('/login');
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError('');
    setPasswordSuccess(false);

    // Validation
    if (passwordForm.newPassword.length < 6) {
      setPasswordError('New password must be at least 6 characters');
      return;
    }

    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setPasswordError('New passwords do not match');
      return;
    }

    setIsChangingPassword(true);

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/auth/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('alphatrion_token')}`,
        },
        body: JSON.stringify({
          current_password: passwordForm.currentPassword,
          new_password: passwordForm.newPassword,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to change password');
      }

      setPasswordSuccess(true);
      setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });

      // Close modal after 2 seconds
      setTimeout(() => {
        setShowPasswordModal(false);
        setPasswordSuccess(false);
      }, 2000);
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : 'Failed to change password');
    } finally {
      setIsChangingPassword(false);
    }
  };

  // Get user initials for avatar
  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(part => part[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* User Profile Button - Avatar Only */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1 p-1 rounded-md hover:bg-muted transition-colors"
        title={currentUser.name}
      >
        {/* Avatar */}
        {currentUser.avatarUrl ? (
          <img
            src={currentUser.avatarUrl}
            alt={currentUser.name}
            className="w-8 h-8 rounded-full"
          />
        ) : (
          <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-medium">
            {getInitials(currentUser.name)}
          </div>
        )}

        {/* Chevron */}
        <ChevronDown className={`h-3 w-3 text-muted-foreground transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 z-50 overflow-hidden">
          {/* User Info */}
          <div className="px-3 py-2 bg-gray-50">
            <div className="flex items-center gap-2">
              {/* Avatar */}
              {currentUser.avatarUrl ? (
                <img
                  src={currentUser.avatarUrl}
                  alt={currentUser.name}
                  className="w-8 h-8 rounded-full flex-shrink-0"
                />
              ) : (
                <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-[11px] font-medium flex-shrink-0">
                  {getInitials(currentUser.name)}
                </div>
              )}
              {/* Name and Email */}
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-gray-900 truncate">{currentUser.name}</p>
                <p className="text-[11px] text-gray-500 truncate">{currentUser.email}</p>
              </div>
            </div>
          </div>

          {/* Organization */}
          {organization && (
            <div className="px-3 py-2 border-b border-gray-200">
              <div className="flex items-center gap-1.5 text-gray-600 mb-1.5">
                <Building2 className="h-3.5 w-3.5 flex-shrink-0" />
                <p className="text-[10px] text-gray-500 uppercase tracking-wide font-medium">Organization</p>
              </div>
              <div className="flex w-full items-center gap-2 px-2 py-1.5 rounded-md text-xs bg-gray-50 text-gray-900 font-medium">
                <span className="truncate">{organization.name}</span>
              </div>
            </div>
          )}

          {/* Team Switcher */}
          {teams && teams.length > 0 && (
            <div className="px-3 py-2 border-b border-gray-200">
              <div className="flex items-center gap-1.5 text-gray-600 mb-1.5">
                <Users className="h-3.5 w-3.5 flex-shrink-0" />
                <p className="text-[10px] text-gray-500 uppercase tracking-wide font-medium">Team</p>
              </div>
              <div className="space-y-0.5 max-h-40 overflow-y-auto">
                {teams.map((team) => {
                  const isSelected = team.id === selectedTeamId;
                  return (
                    <button
                      key={team.id}
                      onClick={() => {
                        setSelectedTeamId(team.id, currentUser.id);
                        localStorage.setItem('alphatrion_org_id', team.orgId);
                        localStorage.setItem('alphatrion_team_id', team.id);
                        setIsOpen(false);
                        navigate('/');
                      }}
                      className={cn(
                        "flex w-full items-center justify-between gap-2 px-2 py-1.5 rounded-md text-xs transition-all",
                        isSelected
                          ? "bg-blue-50 text-blue-900 font-medium shadow-sm"
                          : "hover:bg-gray-50 text-gray-700"
                      )}
                    >
                      <span className="truncate">{team.name || 'Unnamed Team'}</span>
                      {isSelected && (
                        <Check className="h-3.5 w-3.5 flex-shrink-0 text-blue-600" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="p-1.5 space-y-0.5">
            <button
              onClick={() => {
                setShowPasswordModal(true);
                setIsOpen(false);
              }}
              className="w-full flex items-center gap-2 px-2 py-1.5 text-xs text-gray-700 hover:bg-gray-50 rounded-md transition-colors font-medium"
            >
              <Key className="h-3.5 w-3.5" />
              <span>Change Password</span>
            </button>
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-2 px-2 py-1.5 text-xs text-red-600 hover:bg-red-50 rounded-md transition-colors font-medium"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span>Logout</span>
            </button>
          </div>
        </div>
      )}

      {/* Change Password Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-4 w-80 max-w-md">
            <h2 className="text-base font-semibold text-gray-900 mb-3">Change Password</h2>

            <form onSubmit={handleChangePassword} className="space-y-3">
              {/* Current Password */}
              <div>
                <label htmlFor="currentPassword" className="block text-xs font-medium text-gray-700 mb-1">
                  Current Password
                </label>
                <input
                  id="currentPassword"
                  type="password"
                  required
                  value={passwordForm.currentPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
                  className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* New Password */}
              <div>
                <label htmlFor="newPassword" className="block text-xs font-medium text-gray-700 mb-1">
                  New Password
                </label>
                <input
                  id="newPassword"
                  type="password"
                  required
                  value={passwordForm.newPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
                  className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Confirm Password */}
              <div>
                <label htmlFor="confirmPassword" className="block text-xs font-medium text-gray-700 mb-1">
                  Confirm New Password
                </label>
                <input
                  id="confirmPassword"
                  type="password"
                  required
                  value={passwordForm.confirmPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
                  className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Error Message */}
              {passwordError && (
                <div className="text-xs text-red-600 bg-red-50 px-2.5 py-1.5 rounded-md">
                  {passwordError}
                </div>
              )}

              {/* Success Message */}
              {passwordSuccess && (
                <div className="text-xs text-green-600 bg-green-50 px-2.5 py-1.5 rounded-md">
                  Password changed successfully!
                </div>
              )}

              {/* Buttons */}
              <div className="flex gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => {
                    setShowPasswordModal(false);
                    setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
                    setPasswordError('');
                    setPasswordSuccess(false);
                  }}
                  className="flex-1 px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isChangingPassword}
                  className="flex-1 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isChangingPassword ? 'Changing...' : 'Change Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
