import React, {useState} from 'react';
import {Card, CardContent, CardHeader, CardTitle} from '../ui/card';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '../ui/tabs';
import UserManagement from './UserManagement';
import SystemStatus from './SystemStatus';
import ActivityLogs from './ActivityLogs';
import {useAuth} from '../../lib/auth';
import {Navigate} from 'react-router-dom';

const AdminDashboard = () => {
    const {user} = useAuth();
    const [activeTab, setActiveTab] = useState('users');

    // Redirect if not admin
    if (!user || user.role !== 'admin') {
        return <Navigate to="/" replace/>;
    }

    return (
        <div className="container mx-auto space-y-8 px-4 py-6 max-w-[90rem]">
            <Card className="bg-white dark:bg-[#1f2937] shadow-xl border border-gray-200 dark:border-gray-700">
                <CardHeader>
                    <CardTitle className="text-2xl font-bold">Admin Dashboard</CardTitle>
                </CardHeader>
                <CardContent>
                    <Tabs value={activeTab} onValueChange={setActiveTab}>
                        <TabsList className="grid grid-cols-3 gap-4 mb-8">
                            <TabsTrigger value="users">User Management</TabsTrigger>
                            <TabsTrigger value="system">System Status</TabsTrigger>
                            <TabsTrigger value="logs">Activity Logs</TabsTrigger>
                        </TabsList>

                        <TabsContent value="users">
                            <UserManagement/>
                        </TabsContent>

                        <TabsContent value="system">
                            <SystemStatus/>
                        </TabsContent>

                        <TabsContent value="logs">
                            <ActivityLogs/>
                        </TabsContent>
                    </Tabs>
                </CardContent>
            </Card>
        </div>
    );
};

export default AdminDashboard; 