import React, {useState, useEffect} from 'react';
import {Plus, Edit2, Save, X, RefreshCw, Lock, UserX, UserCheck, Clock} from 'lucide-react';
import {api} from '../../lib/api';

// Helper function to parse UTC timestamp
const parseUTCTimestamp = (timestamp) => {
    if (!timestamp) return null;
    try {
        const date = new Date(timestamp);
        return isNaN(date.getTime()) ? null : date;
    } catch (e) {
        console.error('Error parsing timestamp:', e);
        return null;
    }
};

// Helper function to format date with timezone
const formatDateTime = (timestamp) => {
    if (!timestamp) return null;

    const date = timestamp instanceof Date ? timestamp : parseUTCTimestamp(timestamp);
    if (!date) return null;

    // Get timezone
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

    return {
        relative: formatRelativeTime(date),
        full: date.toLocaleString('en-US', {
            timeZone,
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            timeZoneName: 'short'
        })
    };
};

// Format relative time with more granular recent time handling
const formatRelativeTime = (date) => {
    if (!date) return 'Never';

    const now = new Date();
    const diffInMilliseconds = now - date;
    const diffInSeconds = Math.floor(diffInMilliseconds / 1000);
    const diffInMinutes = Math.floor(diffInSeconds / 60);
    const diffInHours = Math.floor(diffInMinutes / 60);
    const diffInDays = Math.floor(diffInHours / 24);

    // More granular handling of recent times
    if (diffInSeconds < 5) {
        return 'Just now';
    } else if (diffInSeconds < 60) {
        return `${diffInSeconds} seconds ago`;
    } else if (diffInMinutes === 1) {
        return '1 minute ago';
    } else if (diffInMinutes < 60) {
        return `${diffInMinutes} minutes ago`;
    } else if (diffInHours === 1) {
        return '1 hour ago';
    } else if (diffInHours < 24) {
        return `${diffInHours} hours ago`;
    } else if (diffInDays === 1) {
        return 'Yesterday';
    } else if (diffInDays <= 30) {
        return `${diffInDays} days ago`;
    } else {
        // For older dates, show the actual date
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }
};

// Tooltip component remains the same
const Tooltip = ({children, text}) => (
    <div className="group relative inline-block">
        {children}
        <div className="absolute bottom-full left-1/2 mb-2 hidden -translate-x-1/2 transform group-hover:block z-50">
            <div className="rounded bg-gray-900 px-2 py-1 text-xs text-white whitespace-nowrap">
                {text}
            </div>
        </div>
    </div>
);

const UserManagement = () => {
    const [users, setUsers] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [editingUser, setEditingUser] = useState(null);
    const [newUser, setNewUser] = useState({
        username: '',
        name: '',
        password: '',
        role: 'user',
        is_active: true
    });
    const [showNewUserForm, setShowNewUserForm] = useState(false);
    const [error, setError] = useState(null);
    const [successMessage, setSuccessMessage] = useState(null);

    useEffect(() => {
        fetchUsers();
    }, []);

    const showSuccess = (message) => {
        setSuccessMessage(message);
        setTimeout(() => setSuccessMessage(null), 3000);
    };

    const showError = (message) => {
        setError(message);
        setTimeout(() => setError(null), 3000);
    };

    const validateUser = (user) => {
        if (!user) return null;

        // Parse timestamps (they should be in UTC format)
        const createdAt = parseUTCTimestamp(user.createdAt);
        const lastLogin = parseUTCTimestamp(user.lastLogin);

        return {
            ...user,
            id: user.user_id || user.uid || Math.random().toString(),
            name: user.name || 'N/A',
            username: user.username || 'N/A',
            role: user.role || 'user',
            is_active: typeof user.is_active === 'boolean' ? user.is_active : true,
            createdAt,
            lastLogin
        };
    };

    const fetchUsers = async () => {
        try {
            setIsLoading(true);
            const response = await api.listUsers();
            if (response?.users) {
                // Filter out null values and validate each user
                const validUsers = response.users
                    .filter(user => user !== null)
                    .map(validateUser)
                    .filter(user => user !== null);
                setUsers(validUsers);
            } else {
                setUsers([]);
            }
        } catch (error) {
            showError('Error fetching users: ' + error.message);
            setUsers([]); // Set empty array on error
        } finally {
            setIsLoading(false);
        }
    };

    const handleCreateUser = async (e) => {
        e.preventDefault();
        try {
            const response = await api.createUser({
                ...newUser,
                email: newUser.username // Use username as email if needed
            });

            if (response.success) {
                showSuccess('User created successfully!');
                setShowNewUserForm(false);
                setNewUser({username: '', name: '', password: '', role: 'user', is_active: true});
                fetchUsers();
            } else {
                showError(response.message || 'Failed to create user');
            }
        } catch (error) {
            showError('Error creating user: ' + (error.message || 'Unknown error'));
        }
    };

    const handleUpdateUser = async (userId) => {
        try {
            if (!editingUser || !userId) {
                throw new Error('Invalid user data for update');
            }
            const response = await api.updateUser(userId, {
                name: editingUser.name,
                role: editingUser.role,
                is_active: editingUser.is_active
            });

            if (response.success) {
                showSuccess('User updated successfully!');
                setEditingUser(null);
                fetchUsers();
            } else {
                showError(response.message || 'Failed to update user');
            }
        } catch (error) {
            showError('Error updating user: ' + (error.message || 'Unknown error'));
        }
    };

    const handleToggleUserStatus = async (user) => {
        if (!user?.id) {
            showError('Invalid user ID');
            return;
        }
        try {
            const response = await api.toggleUserStatus(user.id, !user.isActive);
            if (response.success) {
                showSuccess(`User ${user.isActive ? 'deactivated' : 'activated'} successfully!`);
                fetchUsers();
            } else {
                showError(response.message || 'Failed to update user status');
            }
        } catch (error) {
            showError('Error updating user status: ' + (error.message || 'Unknown error'));
        }
    };

    const handleResetPassword = async (userId) => {
        if (!userId) {
            showError('Invalid user ID');
            return;
        }
        try {
            const response = await api.resetUserPassword(userId);
            if (response.success) {
                showSuccess('Password reset email sent to user!');
            } else {
                showError(response.message || 'Failed to reset password');
            }
        } catch (error) {
            showError('Error resetting password: ' + (error.message || 'Unknown error'));
        }
    };

    const roles = ['admin', 'manager', 'user'];

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    // Early return if users is not an array
    if (!Array.isArray(users)) {
        return (
            <div className="p-6">
                <div className="text-red-600">Error loading users</div>
            </div>
        );
    }

    return (
        <div className="space-y-6 p-6">
            {/* Notifications */}
            {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative">
                    {error}
                </div>
            )}
            {successMessage && (
                <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative">
                    {successMessage}
                </div>
            )}

            {/* Header */}
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">User Management</h2>
                <div className="flex gap-2">
                    <button
                        onClick={fetchUsers}
                        className="flex items-center gap-2 px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors dark:bg-gray-700 dark:text-gray-200"
                    >
                        <RefreshCw className="h-4 w-4"/>
                        Refresh
                    </button>
                    <button
                        onClick={() => setShowNewUserForm(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        <Plus className="h-4 w-4"/>
                        Add New User
                    </button>
                </div>
            </div>

            {/* New User Form */}
            {showNewUserForm && (
                <form onSubmit={handleCreateUser} className="space-y-4 p-6 bg-white dark:bg-gray-800 rounded-lg shadow">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label
                                className="block text-sm font-medium text-gray-700 dark:text-gray-200">Username</label>
                            <input
                                type="text"
                                value={newUser.username}
                                onChange={(e) => setNewUser(prev => ({...prev, username: e.target.value}))}
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                required
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">Full
                                Name</label>
                            <input
                                type="text"
                                value={newUser.name}
                                onChange={(e) => setNewUser(prev => ({...prev, name: e.target.value}))}
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                required
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">Role</label>
                            <select
                                value={newUser.role}
                                onChange={(e) => setNewUser(prev => ({...prev, role: e.target.value}))}
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                            >
                                {roles.map(role => (
                                    <option key={role}
                                            value={role}>{role.charAt(0).toUpperCase() + role.slice(1)}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label
                                className="block text-sm font-medium text-gray-700 dark:text-gray-200">Password</label>
                            <input
                                type="password"
                                value={newUser.password}
                                onChange={(e) => setNewUser(prev => ({...prev, password: e.target.value}))}
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                required
                            />
                        </div>
                    </div>
                    <div className="flex justify-end gap-2">
                        <button
                            type="button"
                            onClick={() => setShowNewUserForm(false)}
                            className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-200"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                        >
                            Create User
                        </button>
                    </div>
                </form>
            )}

            {/* Users Table */}
            <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
                <table className="w-full">
                    <thead>
                    <tr className="bg-gray-50 dark:bg-gray-800">
                        <th className="px-6 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Name</th>
                        <th className="px-6 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Username</th>
                        <th className="px-6 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Role</th>
                        <th className="px-6 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Status</th>
                        <th className="px-6 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Activity</th>
                        <th className="px-6 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Actions</th>
                    </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {users.map(user => {
                        const validUser = validateUser(user);
                        if (!validUser) return null;

                        const lastLoginTime = formatDateTime(validUser.lastLogin);
                        const createdAtTime = formatDateTime(validUser.createdAt);

                        return (
                            <tr key={validUser.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                                <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-200">
                                    {editingUser?.id === validUser.id ? (
                                        <input
                                            type="text"
                                            value={editingUser.name}
                                            onChange={(e) => setEditingUser(prev => ({...prev, name: e.target.value}))}
                                            className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                        />
                                    ) : validUser.name}
                                </td>
                                <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-200">
                                    {validUser.username}
                                </td>
                                <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-200">
                                    {editingUser?.id === validUser.id ? (
                                        <select
                                            value={editingUser.role}
                                            onChange={(e) => setEditingUser(prev => ({...prev, role: e.target.value}))}
                                            className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                        >
                                            {roles.map(role => (
                                                <option key={role} value={role}>
                                                    {role.charAt(0).toUpperCase() + role.slice(1)}
                                                </option>
                                            ))}
                                        </select>
                                    ) : (
                                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                                                ${validUser.role === 'admin' ? 'bg-purple-100 text-purple-800' :
                                            validUser.role === 'manager' ? 'bg-blue-100 text-blue-800' :
                                                'bg-green-100 text-green-800'}`}>
                                                {validUser.role.charAt(0).toUpperCase() + validUser.role.slice(1)}
                                            </span>
                                    )}
                                </td>
                                <td className="px-6 py-4 text-sm">
                                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                                            ${validUser.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                            {validUser.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                </td>
                                <td className="px-6 py-4 text-sm">
                                    <div className="flex flex-col gap-1">
                                        <Tooltip text={lastLoginTime?.full || 'Never logged in'}>
                                            <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
                                                <Clock className="h-3 w-3"/>
                                                <span>Last login: {lastLoginTime?.relative || 'Never'}</span>
                                            </div>
                                        </Tooltip>
                                        <Tooltip text={createdAtTime?.full || 'Unknown'}>
                                            <div
                                                className="flex items-center gap-1 text-gray-500 dark:text-gray-500 text-xs">
                                                Created: {createdAtTime?.relative || 'Unknown'}
                                            </div>
                                        </Tooltip>
                                    </div>
                                </td>
                                <td className="px-6 py-4 text-sm">
                                    <div className="flex items-center gap-2">
                                        {editingUser?.id === validUser.id ? (
                                            <>
                                                <button
                                                    onClick={() => handleUpdateUser(validUser.id)}
                                                    className="text-green-600 hover:text-green-900"
                                                >
                                                    <Save className="h-4 w-4"/>
                                                </button>
                                                <button
                                                    onClick={() => setEditingUser(null)}
                                                    className="text-gray-600 hover:text-gray-900"
                                                >
                                                    <X className="h-4 w-4"/>
                                                </button>
                                            </>
                                        ) : (
                                            <>
                                                <button
                                                    onClick={() => setEditingUser(validUser)}
                                                    className="text-blue-600 hover:text-blue-900"
                                                >
                                                    <Edit2 className="h-4 w-4"/>
                                                </button>
                                                <button
                                                    onClick={() => handleResetPassword(validUser.id)}
                                                    className="text-orange-600 hover:text-orange-900"
                                                >
                                                    <Lock className="h-4 w-4"/>
                                                </button>
                                                <button
                                                    onClick={() => handleToggleUserStatus(validUser)}
                                                    className={validUser.is_active ? "text-red-600 hover:text-red-900" : "text-green-600 hover:text-green-900"}
                                                >
                                                    {validUser.is_active ? <UserX className="h-4 w-4"/> :
                                                        <UserCheck className="h-4 w-4"/>}
                                                </button>
                                            </>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        );
                    })}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default UserManagement; 