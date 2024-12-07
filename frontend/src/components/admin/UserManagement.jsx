import React, {useState, useEffect} from 'react';
import {Plus, Edit2, Save, X, RefreshCw} from 'lucide-react';
import {api} from '../../lib/api';

const UserManagement = () => {
    const [users, setUsers] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [editingUser, setEditingUser] = useState(null);
    const [newUser, setNewUser] = useState({
        username: '',
        name: '',
        password: '',
        role: 'user'
    });
    const [showNewUserForm, setShowNewUserForm] = useState(false);

    useEffect(() => {
        fetchUsers();
    }, []);

    const fetchUsers = async () => {
        try {
            setIsLoading(true);
            const response = await api.getUsers();
            setUsers(response.users);
        } catch (error) {
            console.error('Error fetching users:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleCreateUser = async (e) => {
        e.preventDefault();
        try {
            await api.createUser(newUser);
            setShowNewUserForm(false);
            setNewUser({username: '', name: '', password: '', role: 'user'});
            fetchUsers();
        } catch (error) {
            console.error('Error creating user:', error);
        }
    };

    const handleUpdateUser = async (userId) => {
        try {
            await api.updateUser(userId, editingUser);
            setEditingUser(null);
            fetchUsers();
        } catch (error) {
            console.error('Error updating user:', error);
        }
    };

    return (
        <div className="space-y-6">
            {/* Add New User Button */}
            <div className="flex justify-end">
                <button
                    onClick={() => setShowNewUserForm(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                    <Plus className="h-4 w-4"/>
                    Add New User
                </button>
            </div>

            {/* New User Form */}
            {showNewUserForm && (
                <form onSubmit={handleCreateUser} className="space-y-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    {/* Form fields */}
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
                        <th className="px-6 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Last
                            Login
                        </th>
                        <th className="px-6 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Actions</th>
                    </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {users.map(user => (
                        <tr key={user.email} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                            {/* User data cells */}
                        </tr>
                    ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default UserManagement; 