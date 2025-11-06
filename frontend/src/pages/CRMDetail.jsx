import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Separator } from '../components/ui/separator';
import {
  ArrowLeft,
  ExternalLink,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  RefreshCw,
  Copy,
  FileText,
  Activity,
  Link as LinkIcon,
  User
} from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../context/AuthContext';

export default function CRMDetail() {
  const { call_id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState(null);
  const [resyncing, setResyncing] = useState(false);

  useEffect(() => {
    fetchDetail();
  }, [call_id]);

  const fetchDetail = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/crm/calls/${call_id}`);
      setDetail(response.data);
    } catch (error) {
      console.error('Error fetching CRM detail:', error);
      toast.error(error.response?.status === 403 ? 'Access denied' : 'Failed to load CRM record');
      navigate('/crm');
    } finally {
      setLoading(false);
    }
  };

  const handleResync = async () => {
    if (!['manager', 'admin'].includes(user?.role)) {
      toast.error('Only managers and admins can resync records');
      return;
    }

    try {
      setResyncing(true);
      await axios.post(`${API}/crm/calls/${call_id}/resync`);
      toast.success('Record resynced successfully');
      await fetchDetail();
    } catch (error) {
      console.error('Error resyncing:', error);
      toast.error('Failed to resync record');
    } finally {
      setResyncing(false);
    }
  };

  const handleValidateMapping = async () => {
    if (!['manager', 'admin'].includes(user?.role)) {
      toast.error('Only managers and admins can validate mappings');
      return;
    }

    try {
      const response = await axios.post(`${API}/crm/calls/${call_id}/validate-mapping`);
      toast.success(response.data.message || 'Mapping validated');
      await fetchDetail();
    } catch (error) {
      console.error('Error validating mapping:', error);
      toast.error('Failed to validate mapping');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const getStatusBadge = (status, type = 'transcript') => {
    const configs = {
      transcript: {
        available: { icon: CheckCircle, label: 'Available', className: 'bg-green-500' },
        missing: { icon: XCircle, label: 'Missing', className: 'bg-red-500' },
        processing: { icon: Clock, label: 'Processing', className: 'bg-yellow-500' },
        error: { icon: AlertCircle, label: 'Error', className: 'bg-red-600' },
      },
      sync: {
        synced: { icon: CheckCircle, label: 'Synced', className: 'bg-green-500' },
        error: { icon: XCircle, label: 'Error', className: 'bg-red-600' },
        stale: { icon: Clock, label: 'Stale', className: 'bg-yellow-600' },
        pending: { icon: Clock, label: 'Pending', className: 'bg-gray-500' },
      },
    };

    const configSet = type === 'transcript' ? configs.transcript : configs.sync;
    const config = configSet[status] || configSet.missing || configSet.pending;
    const Icon = config.icon;

    return (
      <Badge className={`${config.className} text-white flex items-center gap-1 w-fit`}>
        <Icon className="w-3 h-3" />
        {config.label}
      </Badge>
    );
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

  if (loading) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        </div>
      </div>
    );
  }

  if (!detail) {
    return null;
  }

  const { record, sync_logs = [], agent_mapping, audit_info } = detail;

  return (
    <div className="container mx-auto py-8 px-4 max-w-6xl">
      {/* Header */}
      <div className="mb-6">
        <Button variant="ghost" onClick={() => navigate('/crm')} className="mb-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to CRM List
        </Button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">{record.call_id}</h1>
            <p className="text-gray-600 mt-1">CRM Call Record Details</p>
          </div>
          <div className="flex gap-2">
            {getStatusBadge(record.sync_status, 'sync')}
          </div>
        </div>
      </div>

      {/* Primary Metadata */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Call Information</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-6">
          <div>
            <label className="text-sm font-semibold text-gray-600">CRM User ID</label>
            <div className="flex items-center gap-2 mt-1">
              <p className="font-mono">{record.crm_user_id}</p>
              <Button variant="ghost" size="sm" onClick={() => copyToClipboard(record.crm_user_id)}>
                <Copy className="w-4 h-4" />
              </Button>
            </div>
          </div>
          <div>
            <label className="text-sm font-semibold text-gray-600">Agent</label>
            <div className="mt-1">
              <p className="font-medium">{record.agent_name || 'Unknown'}</p>
              <p className="text-sm text-gray-500 font-mono">{record.agent_id}</p>
            </div>
          </div>
          <div>
            <label className="text-sm font-semibold text-gray-600">Campaign</label>
            <div className="mt-1">
              <p className="font-medium">{record.campaign_name}</p>
              <p className="text-sm text-gray-500">{record.campaign_id}</p>
            </div>
          </div>
          <div>
            <label className="text-sm font-semibold text-gray-600">Queue</label>
            <p className="mt-1">{record.queue_name || 'N/A'}</p>
          </div>
          <div>
            <label className="text-sm font-semibold text-gray-600">Call Date & Time</label>
            <p className="mt-1">{formatDateTime(record.call_datetime)}</p>
          </div>
          <div>
            <label className="text-sm font-semibold text-gray-600">Duration</label>
            <p className="mt-1">{formatDuration(record.call_duration_seconds)}</p>
          </div>
        </CardContent>
      </Card>

      {/* Recording & Transcript */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Recording & Transcript
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-semibold text-gray-600">Recording URL</label>
            <div className="flex items-center gap-2 mt-1">
              <code className="text-sm bg-gray-100 px-3 py-1 rounded flex-1 truncate">
                {record.recording_url || 'N/A'}
              </code>
              {record.recording_url && (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => copyToClipboard(record.recording_url)}
                  >
                    <Copy className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => window.open(record.recording_url, '_blank')}
                  >
                    <ExternalLink className="w-4 h-4" />
                  </Button>
                </>
              )}
            </div>
          </div>
          <div>
            <label className="text-sm font-semibold text-gray-600">Recording Reference</label>
            <code className="text-sm bg-gray-100 px-3 py-1 rounded block mt-1">
              {record.recording_ref || 'N/A'}
            </code>
          </div>
          <Separator />
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-semibold text-gray-600">Transcript Status</label>
              {getStatusBadge(record.transcript_status, 'transcript')}
            </div>
            {record.transcript_word_count && (
              <p className="text-sm text-gray-600">Word Count: {record.transcript_word_count}</p>
            )}
            {record.transcript_last_updated && (
              <p className="text-sm text-gray-600">Last Updated: {formatDateTime(record.transcript_last_updated)}</p>
            )}
          </div>
          {record.transcript_preview && (
            <div>
              <label className="text-sm font-semibold text-gray-600 block mb-2">Transcript Preview</label>
              <div className="bg-gray-50 border rounded-lg p-4 max-h-64 overflow-y-auto">
                <pre className="text-sm whitespace-pre-wrap">{record.transcript_preview}</pre>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Agent Mapping */}
      {agent_mapping && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="w-5 h-5" />
              Agent Mapping
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-semibold text-gray-600">CRM Agent ID</label>
              <p className="mt-1 font-mono">{agent_mapping.crm_agent_id}</p>
            </div>
            <div>
              <label className="text-sm font-semibold text-gray-600">App User ID</label>
              <p className="mt-1 font-mono">{agent_mapping.app_user_id}</p>
            </div>
            <div>
              <label className="text-sm font-semibold text-gray-600">Agent Name</label>
              <p className="mt-1 font-medium">{agent_mapping.agent_name}</p>
            </div>
            <div>
              <label className="text-sm font-semibold text-gray-600">Team ID</label>
              <p className="mt-1">{agent_mapping.team_id || 'N/A'}</p>
            </div>
            <div>
              <label className="text-sm font-semibold text-gray-600">Status</label>
              <Badge className={agent_mapping.is_active ? 'bg-green-500' : 'bg-gray-500'}>
                {agent_mapping.is_active ? 'Active' : 'Inactive'}
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Linked Audit */}
      {audit_info && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <LinkIcon className="w-5 h-5" />
              Linked Audit
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold">Audit ID: {audit_info.id}</p>
                <p className="text-sm text-gray-600">
                  Status: <Badge>{audit_info.status}</Badge>
                </p>
                <p className="text-sm text-gray-600 mt-1">
                  Assigned: {formatDateTime(audit_info.assigned_at)}
                </p>
              </div>
              <Button onClick={() => navigate(`/audits/${audit_info.id}`)}>
                Open Audit
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sync Logs */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5" />
            Sync Logs (Last 10)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {sync_logs.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No sync logs available</p>
          ) : (
            <div className="space-y-3">
              {sync_logs.map((log, idx) => (
                <div
                  key={log.id || idx}
                  className="border rounded-lg p-3 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Badge variant={log.status === 'success' ? 'default' : 'destructive'}>
                        {log.action}
                      </Badge>
                      <span className="text-sm font-semibold">
                        {log.status === 'success' ? '✓ Success' : '✗ Failed'}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500">
                      {formatDateTime(log.timestamp)}
                      {log.duration_ms && ` • ${log.duration_ms}ms`}
                    </span>
                  </div>
                  {log.result && (
                    <p className="text-sm text-gray-700">{log.result}</p>
                  )}
                  {log.error_message && (
                    <p className="text-sm text-red-600 mt-1">Error: {log.error_message}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Actions (Manager/Admin only) */}
      {['manager', 'admin'].includes(user?.role) && (
        <Card>
          <CardHeader>
            <CardTitle>Actions</CardTitle>
            <CardDescription>Manager/Admin operations</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-3">
            <Button onClick={handleResync} disabled={resyncing}>
              <RefreshCw className={`w-4 h-4 mr-2 ${resyncing ? 'animate-spin' : ''}`} />
              {resyncing ? 'Resyncing...' : 'Resync from CRM'}
            </Button>
            <Button variant="outline" onClick={handleValidateMapping}>
              <CheckCircle className="w-4 h-4 mr-2" />
              Validate Mapping
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
