import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { Badge } from '../components/ui/badge';
import { Upload, CheckCircle, XCircle, Clock, Database } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../context/AuthContext';

export default function ImportCallReference() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [recentImports, setRecentImports] = useState([]);
  const [formData, setFormData] = useState({
    call_id: '',
    source: 'crm',
    agent_id: '',
    customer_id: '',
    date_time: '',
    duration_seconds: '',
    campaign_id: '',
  });

  useEffect(() => {
    fetchRecentImports();
  }, []);

  const fetchRecentImports = async () => {
    try {
      // Fetch last 10 imported call references
      const response = await axios.get(`${API}/call-references?limit=10&sort=imported_at:desc`);
      setRecentImports(response.data.references || []);
    } catch (error) {
      console.error('Error fetching recent imports:', error);
      // Don't show error toast on initial load
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validation
    if (!formData.call_id || !formData.agent_id || !formData.date_time) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      setLoading(true);
      
      // Prepare data for API
      const importData = {
        call_id: formData.call_id,
        source: formData.source,
        agent_id: formData.agent_id,
        date_time: new Date(formData.date_time).toISOString(),
      };

      // Add optional fields
      if (formData.customer_id) importData.customer_id = formData.customer_id;
      if (formData.duration_seconds) importData.duration_seconds = parseInt(formData.duration_seconds);
      if (formData.campaign_id) importData.campaign_id = formData.campaign_id;

      const response = await axios.post(`${API}/audits/import-call`, importData);
      
      toast.success('Call reference imported successfully');
      
      // Reset form
      setFormData({
        call_id: '',
        source: 'crm',
        agent_id: '',
        customer_id: '',
        date_time: '',
        duration_seconds: '',
        campaign_id: '',
      });
      
      // Refresh recent imports
      await fetchRecentImports();
    } catch (error) {
      console.error('Error importing call reference:', error);
      toast.error(error.response?.data?.detail || 'Failed to import call reference');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const getSourceBadge = (source) => {
    const config = {
      crm: { label: 'CRM', className: 'bg-blue-500' },
      aws_s3: { label: 'AWS S3', className: 'bg-orange-500' },
      manual: { label: 'Manual', className: 'bg-gray-500' },
    };
    
    const { label, className } = config[source] || config.manual;
    return <Badge className={`${className} text-white`}>{label}</Badge>;
  };

  const formatDateTime = (isoString) => {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleString();
  };

  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  // Check if user has permission
  if (!['admin', 'manager'].includes(user?.role)) {
    return (
      <div className="container mx-auto py-8 px-4">
        <Card>
          <CardContent className="py-12 text-center">
            <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2">Access Denied</h2>
            <p className="text-gray-600">
              Only Managers and Admins can import call references.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Import Call Reference</h1>
        <p className="text-gray-600">Import call data from CRM or AWS S3 for audit assignment</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Import Form */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="w-5 h-5" />
              Import Call Data
            </CardTitle>
            <CardDescription>
              Import call reference from external sources (CRM/AWS)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="call_id">
                  Call ID <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="call_id"
                  placeholder="e.g., CRM-12345 or AWS-67890"
                  value={formData.call_id}
                  onChange={(e) => handleChange('call_id', e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="source">
                  Source Type <span className="text-red-500">*</span>
                </Label>
                <Select
                  value={formData.source}
                  onValueChange={(value) => handleChange('source', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select source" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="crm">CRM (Salesforce/HubSpot)</SelectItem>
                    <SelectItem value="aws_s3">AWS S3</SelectItem>
                    <SelectItem value="manual">Manual Entry</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="agent_id">
                  Agent ID <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="agent_id"
                  placeholder="e.g., AGENT-001 or SF-AGENT-123"
                  value={formData.agent_id}
                  onChange={(e) => handleChange('agent_id', e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="date_time">
                  Call Date & Time <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="date_time"
                  type="datetime-local"
                  value={formData.date_time}
                  onChange={(e) => handleChange('date_time', e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="customer_id">Customer ID (Optional)</Label>
                <Input
                  id="customer_id"
                  placeholder="e.g., CUST-12345"
                  value={formData.customer_id}
                  onChange={(e) => handleChange('customer_id', e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="duration_seconds">Duration (seconds)</Label>
                <Input
                  id="duration_seconds"
                  type="number"
                  placeholder="e.g., 300 (5 minutes)"
                  value={formData.duration_seconds}
                  onChange={(e) => handleChange('duration_seconds', e.target.value)}
                  min="0"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="campaign_id">Campaign ID (Optional)</Label>
                <Input
                  id="campaign_id"
                  placeholder="e.g., CAMP-2024-Q4"
                  value={formData.campaign_id}
                  onChange={(e) => handleChange('campaign_id', e.target.value)}
                />
              </div>

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? (
                  <>
                    <Clock className="w-4 h-4 mr-2 animate-spin" />
                    Importing...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4 mr-2" />
                    Import Call Reference
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Recent Imports */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="w-5 h-5" />
              Recent Imports
            </CardTitle>
            <CardDescription>Last 10 imported call references</CardDescription>
          </CardHeader>
          <CardContent>
            {recentImports.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Database className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                <p>No recent imports</p>
                <p className="text-sm mt-1">Import your first call reference to see it here</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[600px] overflow-y-auto">
                {recentImports.map((item) => (
                  <div
                    key={item.id}
                    className="border rounded-lg p-3 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="font-mono text-sm font-semibold mb-1">
                          {item.call_id}
                        </div>
                        <div className="text-xs text-gray-600">
                          Agent: {item.agent_id}
                        </div>
                      </div>
                      {getSourceBadge(item.source)}
                    </div>
                    <div className="text-xs text-gray-500 space-y-1">
                      <div>📅 {formatDateTime(item.date_time)}</div>
                      {item.duration_seconds && (
                        <div>⏱️ Duration: {formatDuration(item.duration_seconds)}</div>
                      )}
                      {item.campaign_id && <div>📢 Campaign: {item.campaign_id}</div>}
                      <div className="text-gray-400 pt-1">
                        Imported: {formatDateTime(item.imported_at)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
