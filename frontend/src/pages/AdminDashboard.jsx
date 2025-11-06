import { useState, useEffect } from "react";
import axios from "axios";
import { API } from "../App";
import { useAuth } from "../context/AuthContext";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { toast } from "sonner";
import { 
  Users, 
  Shield, 
  Settings, 
  UserPlus, 
  Edit, 
  Trash2,
  Key,
  CheckCircle,
  XCircle,
  Crown
} from "lucide-react";

export default function AdminDashboard() {
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState({});
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    full_name: "",
    role: "auditor",
    team_id: "",
    status: "active"
  });

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      const [usersRes, rolesRes, statsRes] = await Promise.all([
        axios.get(`${API}/admin/users`),
        axios.get(`${API}/rbac/roles`),
        axios.get(`${API}/admin/stats`)
      ]);
      
      setUsers(usersRes.data);
      setRoles(rolesRes.data);
      setStats(statsRes.data);
    } catch (error) {
      console.error("Failed to fetch admin data", error);
      toast.error("Failed to load admin data");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/admin/users`, formData);
      toast.success("User created successfully");
      setDialogOpen(false);
      resetForm();
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create user");
    }
  };

  const handleUpdateUser = async (userId) => {
    try {
      await axios.put(`${API}/admin/users/${userId}`, formData);
      toast.success("User updated successfully");
      setDialogOpen(false);
      resetForm();
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update user");
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm("Are you sure you want to delete this user?")) return;

    try {
      await axios.delete(`${API}/admin/users/${userId}`);
      toast.success("User deleted successfully");
      fetchAllData();
    } catch (error) {
      toast.error("Failed to delete user");
    }
  };

  const handleToggleStatus = async (userId, currentStatus) => {
    const newStatus = currentStatus === "active" ? "inactive" : "active";
    try {
      await axios.patch(`${API}/admin/users/${userId}/status`, { status: newStatus });
      toast.success(`User ${newStatus === "active" ? "activated" : "deactivated"}`);
      fetchAllData();
    } catch (error) {
      toast.error("Failed to update user status");
    }
  };

  const resetForm = () => {
    setFormData({
      email: "",
      password: "",
      full_name: "",
      role: "auditor",
      team_id: "",
      status: "active"
    });
    setEditingUser(null);
  };

  const openEditDialog = (user) => {
    setEditingUser(user);
    setFormData({
      email: user.email,
      password: "",
      full_name: user.full_name,
      role: user.role,
      team_id: user.team_id || "",
      status: user.status
    });
    setDialogOpen(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div data-testid="admin-dashboard-page">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold mb-2 flex items-center" style={{ fontFamily: 'Space Grotesk' }}>
              <Crown className="w-10 h-10 mr-3 text-yellow-500" />
              Admin Control Panel
            </h1>
            <p className="text-gray-600">Full system administration and user management</p>
            <Badge className="mt-2 bg-yellow-500 text-white">Administrator</Badge>
          </div>
          <Dialog open={dialogOpen} onOpenChange={(open) => {
            setDialogOpen(open);
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button data-testid="create-user-button" className="bg-gradient-to-r from-yellow-600 to-orange-600">
                <UserPlus className="w-4 h-4 mr-2" />
                Create User
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>{editingUser ? "Edit User" : "Create New User"}</DialogTitle>
                <DialogDescription>
                  {editingUser ? "Update user information" : "Add a new user to the system"}
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={editingUser ? (e) => { e.preventDefault(); handleUpdateUser(editingUser.id); } : handleCreateUser} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="full_name">Full Name</Label>
                  <Input
                    id="full_name"
                    data-testid="user-name-input"
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    data-testid="user-email-input"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                    disabled={editingUser !== null}
                  />
                </div>

                {!editingUser && (
                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <Input
                      id="password"
                      data-testid="user-password-input"
                      type="password"
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      required
                    />
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="role">Role</Label>
                  <Select value={formData.role} onValueChange={(value) => setFormData({ ...formData, role: value })}>
                    <SelectTrigger data-testid="user-role-select">
                      <SelectValue placeholder="Select role" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="auditor">Auditor (Team Lead)</SelectItem>
                      <SelectItem value="manager">Manager</SelectItem>
                      <SelectItem value="admin">Admin</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="team_id">Team ID (Optional)</Label>
                  <Input
                    id="team_id"
                    data-testid="user-team-input"
                    value={formData.team_id}
                    onChange={(e) => setFormData({ ...formData, team_id: e.target.value })}
                    placeholder="e.g., TEAM-A"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="status">Status</Label>
                  <Select value={formData.status} onValueChange={(value) => setFormData({ ...formData, status: value })}>
                    <SelectTrigger data-testid="user-status-select">
                      <SelectValue placeholder="Select status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="inactive">Inactive</SelectItem>
                      <SelectItem value="suspended">Suspended</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex justify-end space-x-2">
                  <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button data-testid="save-user-button" type="submit" className="bg-gradient-to-r from-yellow-600 to-orange-600">
                    {editingUser ? "Update" : "Create"}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <Tabs defaultValue="users" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3 max-w-2xl">
          <TabsTrigger value="users" data-testid="tab-users">
            <Users className="w-4 h-4 mr-2" />
            Users
          </TabsTrigger>
          <TabsTrigger value="roles" data-testid="tab-roles">
            <Shield className="w-4 h-4 mr-2" />
            Roles & Permissions
          </TabsTrigger>
          <TabsTrigger value="system" data-testid="tab-system">
            <Settings className="w-4 h-4 mr-2" />
            System Stats
          </TabsTrigger>
        </TabsList>

        {/* USERS TAB */}
        <TabsContent value="users" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <Card className="border-2 border-blue-200">
              <CardContent className="pt-6">
                <div className="text-center">
                  <Users className="w-8 h-8 mx-auto mb-2 text-blue-600" />
                  <div className="text-3xl font-bold text-blue-600">{users.length}</div>
                  <p className="text-sm text-gray-600">Total Users</p>
                </div>
              </CardContent>
            </Card>
            <Card className="border-2 border-green-200">
              <CardContent className="pt-6">
                <div className="text-center">
                  <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-600" />
                  <div className="text-3xl font-bold text-green-600">
                    {users.filter(u => u.status === 'active').length}
                  </div>
                  <p className="text-sm text-gray-600">Active Users</p>
                </div>
              </CardContent>
            </Card>
            <Card className="border-2 border-orange-200">
              <CardContent className="pt-6">
                <div className="text-center">
                  <XCircle className="w-8 h-8 mx-auto mb-2 text-orange-600" />
                  <div className="text-3xl font-bold text-orange-600">
                    {users.filter(u => u.status !== 'active').length}
                  </div>
                  <p className="text-sm text-gray-600">Inactive</p>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>User Management</CardTitle>
              <CardDescription>Manage all system users and their roles</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {users.map((usr) => (
                  <Card key={usr.id} className="border-2">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                            usr.role === 'admin' ? 'bg-yellow-100' :
                            usr.role === 'manager' ? 'bg-blue-100' :
                            'bg-gray-100'
                          }`}>
                            {usr.role === 'admin' ? <Crown className="w-6 h-6 text-yellow-600" /> :
                             usr.role === 'manager' ? <Shield className="w-6 h-6 text-blue-600" /> :
                             <Users className="w-6 h-6 text-gray-600" />}
                          </div>
                          <div>
                            <h3 className="font-semibold">{usr.full_name}</h3>
                            <p className="text-sm text-gray-600">{usr.email}</p>
                            <div className="flex space-x-2 mt-1">
                              <Badge variant={
                                usr.role === 'admin' ? 'default' :
                                usr.role === 'manager' ? 'secondary' :
                                'outline'
                              }>
                                {usr.role.toUpperCase()}
                              </Badge>
                              {usr.team_id && (
                                <Badge variant="outline">{usr.team_id}</Badge>
                              )}
                              <Badge variant={usr.status === 'active' ? 'default' : 'destructive'}>
                                {usr.status}
                              </Badge>
                            </div>
                          </div>
                        </div>
                        <div className="flex space-x-2">
                          <Button
                            data-testid={`toggle-status-${usr.id}`}
                            size="sm"
                            variant="outline"
                            onClick={() => handleToggleStatus(usr.id, usr.status)}
                          >
                            {usr.status === 'active' ? 'Deactivate' : 'Activate'}
                          </Button>
                          <Button
                            data-testid={`edit-user-${usr.id}`}
                            size="sm"
                            variant="outline"
                            onClick={() => openEditDialog(usr)}
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button
                            data-testid={`delete-user-${usr.id}`}
                            size="sm"
                            variant="destructive"
                            onClick={() => handleDeleteUser(usr.id)}
                            disabled={usr.id === user?.id}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ROLES TAB */}
        <TabsContent value="roles" className="space-y-4">
          {Object.entries(roles).map(([roleKey, roleData]) => (
            <Card key={roleKey} className="border-2">
              <CardHeader className={
                roleKey === 'admin' ? 'bg-yellow-50' :
                roleKey === 'manager' ? 'bg-blue-50' :
                'bg-gray-50'
              }>
                <CardTitle className="flex items-center">
                  {roleKey === 'admin' ? <Crown className="w-5 h-5 mr-2 text-yellow-600" /> :
                   roleKey === 'manager' ? <Shield className="w-5 h-5 mr-2 text-blue-600" /> :
                   <Key className="w-5 h-5 mr-2 text-gray-600" />}
                  {roleData.name}
                </CardTitle>
                <CardDescription>{roleData.description}</CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="space-y-4">
                  <div>
                    <h4 className="font-semibold text-green-700 mb-2">✓ Capabilities</h4>
                    <ul className="space-y-1">
                      {roleData.capabilities?.map((cap, idx) => (
                        <li key={idx} className="text-sm flex items-start">
                          <CheckCircle className="w-4 h-4 text-green-600 mr-2 mt-0.5 flex-shrink-0" />
                          <span>{cap}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  {roleData.restrictions?.length > 0 && (
                    <div>
                      <h4 className="font-semibold text-red-700 mb-2">✗ Restrictions</h4>
                      <ul className="space-y-1">
                        {roleData.restrictions.map((res, idx) => (
                          <li key={idx} className="text-sm flex items-start">
                            <XCircle className="w-4 h-4 text-red-600 mr-2 mt-0.5 flex-shrink-0" />
                            <span>{res}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        {/* SYSTEM STATS TAB */}
        <TabsContent value="system" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>User Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-3 bg-yellow-50 rounded-lg">
                    <span className="font-medium">Admins</span>
                    <span className="text-2xl font-bold text-yellow-600">
                      {users.filter(u => u.role === 'admin').length}
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                    <span className="font-medium">Managers</span>
                    <span className="text-2xl font-bold text-blue-600">
                      {users.filter(u => u.role === 'manager').length}
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                    <span className="font-medium">Auditors</span>
                    <span className="text-2xl font-bold text-gray-600">
                      {users.filter(u => u.role === 'auditor').length}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>System Statistics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                    <span className="font-medium">Total Audits</span>
                    <span className="text-2xl font-bold">{stats.total_audits || 0}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                    <span className="font-medium">Total Scripts</span>
                    <span className="text-2xl font-bold">{stats.total_scripts || 0}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                    <span className="font-medium">Active Teams</span>
                    <span className="text-2xl font-bold">
                      {new Set(users.filter(u => u.team_id).map(u => u.team_id)).size}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
