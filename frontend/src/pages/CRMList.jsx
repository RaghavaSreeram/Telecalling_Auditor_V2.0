import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Search, ExternalLink, CheckCircle, XCircle, Clock, AlertCircle, ChevronLeft, ChevronRight, Activity } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../context/AuthContext';

export default function CRMList() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState({
    campaign: '',
    transcriptStatus: '',
    syncStatus: '',
  });
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
  });

  useEffect(() => {
    fetchRecords();
  }, [pagination.page, filters]);

  const fetchRecords = async () => {
    try {
      setLoading(true);
      const params = {
        page: pagination.page,
        page_size: pagination.pageSize,
      };

      if (search) params.search = search;
      if (filters.campaign) params.campaign = filters.campaign;
      if (filters.transcriptStatus) params.transcript_status = filters.transcriptStatus;
      if (filters.syncStatus) params.sync_status = filters.syncStatus;

      const response = await axios.get(`${API}/crm/calls`, { params });
      setRecords(response.data.records);
      setPagination(prev => ({
        ...prev,
        total: response.data.total,
        totalPages: response.data.total_pages,
      }));
    } catch (error) {
      console.error('Error fetching CRM records:', error);
      toast.error('Failed to load CRM records');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setPagination(prev => ({ ...prev, page: 1 }));
    fetchRecords();
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      available: { variant: 'default', icon: CheckCircle, label: 'Available', className: 'bg-green-500' },
      missing: { variant: 'destructive', icon: XCircle, label: 'Missing', className: 'bg-red-500' },
      processing: { variant: 'secondary', icon: Clock, label: 'Processing', className: 'bg-yellow-500' },
      error: { variant: 'destructive', icon: AlertCircle, label: 'Error', className: 'bg-red-600' },
      synced: { variant: 'default', icon: CheckCircle, label: 'Synced', className: 'bg-green-500' },
      stale: { variant: 'secondary', icon: Clock, label: 'Stale', className: 'bg-yellow-600' },
    };

    const config = statusConfig[status] || statusConfig.missing;
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

  return (
    <div className="container mx-auto py-8 px-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-2xl font-bold">CRM Integration</CardTitle>
              <CardDescription>
                View CRM call records with sync status and audit linkage
              </CardDescription>
            </div>
            {['manager', 'admin'].includes(user?.role) && (
              <Button variant="outline" onClick={() => navigate('/crm/status')}>
                <Activity className="w-4 h-4 mr-2" />
                Health Status
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {/* Search and Filters */}
          <div className="mb-6 space-y-4">
            <form onSubmit={handleSearch} className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <Input
                  type="text"
                  placeholder="Search by Call ID, Agent ID, CRM User ID..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
              <Button type="submit">Search</Button>
            </form>

            <div className="flex gap-4">
              <Select
                value={filters.transcriptStatus}
                onValueChange={(value) => handleFilterChange('transcriptStatus', value)}
              >
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Transcript Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Transcripts</SelectItem>
                  <SelectItem value="available">Available</SelectItem>
                  <SelectItem value="missing">Missing</SelectItem>
                  <SelectItem value="processing">Processing</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                </SelectContent>
              </Select>

              <Select
                value={filters.syncStatus}
                onValueChange={(value) => handleFilterChange('syncStatus', value)}
              >
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Sync Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Sync Status</SelectItem>
                  <SelectItem value="synced">Synced</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                  <SelectItem value="stale">Stale</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                </SelectContent>
              </Select>

              {filters.transcriptStatus || filters.syncStatus || search ? (
                <Button
                  variant="outline"
                  onClick={() => {
                    setSearch('');
                    setFilters({ campaign: '', transcriptStatus: '', syncStatus: '' });
                    setPagination(prev => ({ ...prev, page: 1 }));
                  }}
                >
                  Clear Filters
                </Button>
              ) : null}
            </div>
          </div>

          {/* Table */}
          {loading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
            </div>
          ) : records.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              No CRM records found. {user?.role === 'admin' ? 'Try seeding data from the Admin dashboard.' : ''}
            </div>
          ) : (
            <>
              <div className="rounded-md border overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Call ID</TableHead>
                      <TableHead>CRM User</TableHead>
                      <TableHead>Agent</TableHead>
                      <TableHead>Campaign</TableHead>
                      <TableHead>Call Date/Time</TableHead>
                      <TableHead>Recording</TableHead>
                      <TableHead>Transcript</TableHead>
                      <TableHead>Sync Status</TableHead>
                      <TableHead>Audit</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {records.map((record) => (
                      <TableRow
                        key={record.id}
                        className="cursor-pointer hover:bg-gray-50"
                        onClick={() => navigate(`/crm/${record.call_id}`)}
                      >
                        <TableCell className="font-mono text-sm">
                          {record.call_id}
                        </TableCell>
                        <TableCell>{record.crm_user_id}</TableCell>
                        <TableCell>
                          <div>
                            <div className="font-medium">{record.agent_name || 'Unknown'}</div>
                            <div className="text-xs text-gray-500">{record.agent_id}</div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div>
                            <div className="font-medium">{record.campaign_name}</div>
                            <div className="text-xs text-gray-500">{record.queue_name}</div>
                          </div>
                        </TableCell>
                        <TableCell className="text-sm">
                          {formatDateTime(record.call_datetime)}
                        </TableCell>
                        <TableCell>
                          {record.recording_url ? (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                window.open(record.recording_url, '_blank');
                              }}
                            >
                              <ExternalLink className="w-4 h-4 mr-1" />
                              Open
                            </Button>
                          ) : (
                            <span className="text-gray-400 text-sm">N/A</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {getStatusBadge(record.transcript_status)}
                        </TableCell>
                        <TableCell>
                          {getStatusBadge(record.sync_status)}
                        </TableCell>
                        <TableCell>
                          {record.audit_id ? (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(`/audits/${record.audit_id}`);
                              }}
                            >
                              View Audit
                            </Button>
                          ) : (
                            <span className="text-gray-400 text-sm">No Audit</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between mt-4">
                <div className="text-sm text-gray-600">
                  Showing {((pagination.page - 1) * pagination.pageSize) + 1} to{' '}
                  {Math.min(pagination.page * pagination.pageSize, pagination.total)} of{' '}
                  {pagination.total} records
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPagination(prev => ({ ...prev, page: prev.page - 1 }))}
                    disabled={pagination.page === 1}
                  >
                    <ChevronLeft className="w-4 h-4" />
                    Previous
                  </Button>
                  <div className="flex items-center px-3 text-sm">
                    Page {pagination.page} of {pagination.totalPages}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPagination(prev => ({ ...prev, page: prev.page + 1 }))}
                    disabled={pagination.page >= pagination.totalPages}
                  >
                    Next
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
