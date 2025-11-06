import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { ArrowLeft, RefreshCw, Activity, Clock, CheckCircle, XCircle, TrendingUp } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../context/AuthContext';

export default function CRMHealth() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState(false);
  const [stats, setStats] = useState(null);
  const [trends, setTrends] = useState([]);

  useEffect(() => {
    // Check if user has access
    if (!['manager', 'admin'].includes(user?.role)) {
      toast.error('Access denied: Manager or Admin role required');
      navigate('/crm');
      return;
    }

    fetchHealthData();
  }, [user, navigate]);

  const fetchHealthData = async () => {
    try {
      setLoading(true);
      const [statsRes, trendsRes] = await Promise.all([
        axios.get(`${API}/crm/health`),
        axios.get(`${API}/crm/health/trends?days=7`)
      ]);
      setStats(statsRes.data);
      setTrends(trendsRes.data.trends || []);
    } catch (error) {
      console.error('Error fetching health data:', error);
      toast.error('Failed to load health statistics');
    } finally {
      setLoading(false);
    }
  };

  const handleRetryFailed = async () => {
    try {
      setRetrying(true);
      const response = await axios.post(`${API}/crm/retry-failed`);
      toast.success(
        `Retried ${response.data.total_attempted} syncs: ${response.data.success_count} succeeded, ${response.data.failure_count} failed`
      );
      await fetchHealthData();
    } catch (error) {
      console.error('Error retrying failed syncs:', error);
      toast.error('Failed to retry syncs');
    } finally {
      setRetrying(false);
    }
  };

  const formatDateTime = (isoString) => {
    if (!isoString) return 'Never';
    const date = new Date(isoString);
    return date.toLocaleString();
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

  if (!stats) {
    return null;
  }

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
            <h1 className="text-3xl font-bold">CRM Integration Health</h1>
            <p className="text-gray-600 mt-1">Monitor sync status and performance</p>
          </div>
          <Button onClick={fetchHealthData} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-600">Total Records</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <Activity className="w-8 h-8 text-indigo-600 mr-3" />
              <div>
                <p className="text-3xl font-bold">{stats.total_records}</p>
                <p className="text-xs text-gray-500 mt-1">CRM records tracked</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-600">Synced Today</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <CheckCircle className="w-8 h-8 text-green-600 mr-3" />
              <div>
                <p className="text-3xl font-bold">{stats.records_synced_today}</p>
                <p className="text-xs text-gray-500 mt-1">Successful syncs</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-600">Failures Today</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <XCircle className="w-8 h-8 text-red-600 mr-3" />
              <div>
                <p className="text-3xl font-bold">{stats.failures_today}</p>
                <p className="text-xs text-gray-500 mt-1">Failed syncs</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-600">Avg Latency</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <Clock className="w-8 h-8 text-blue-600 mr-3" />
              <div>
                <p className="text-3xl font-bold">{Math.round(stats.average_latency_ms)}</p>
                <p className="text-xs text-gray-500 mt-1">milliseconds</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Additional Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Success Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-4xl font-bold text-green-600">
                  {stats.success_rate.toFixed(1)}%
                </p>
                <p className="text-sm text-gray-500 mt-1">Overall sync success</p>
              </div>
              <TrendingUp className="w-12 h-12 text-green-600 opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Pending Syncs</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold text-yellow-600">{stats.pending_syncs}</p>
            <p className="text-sm text-gray-500 mt-1">Awaiting synchronization</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Error Count</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold text-red-600">{stats.error_count}</p>
            <p className="text-sm text-gray-500 mt-1">Total errors</p>
          </CardContent>
        </Card>
      </div>

      {/* Last Sync Time */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Last Sync Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Last successful sync:</p>
              <p className="text-lg font-semibold">{formatDateTime(stats.last_sync_time)}</p>
            </div>
            <Clock className="w-10 h-10 text-gray-400" />
          </div>
        </CardContent>
      </Card>

      {/* Sync Trends */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            7-Day Sync Trends
          </CardTitle>
          <CardDescription>Daily success vs failure counts</CardDescription>
        </CardHeader>
        <CardContent>
          {trends.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No trend data available</p>
          ) : (
            <div className="space-y-3">
              {trends.map((trend, idx) => {
                const total = trend.success_count + trend.failure_count;
                const successPercent = total > 0 ? (trend.success_count / total) * 100 : 0;
                const failurePercent = total > 0 ? (trend.failure_count / total) * 100 : 0;

                return (
                  <div key={idx} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold">{trend.date}</span>
                      <span className="text-sm text-gray-600">
                        Total: {trend.total_records}
                      </span>
                    </div>
                    <div className="flex gap-2 h-8 rounded overflow-hidden">
                      <div
                        className="bg-green-500 flex items-center justify-center text-white text-xs font-semibold"
                        style={{ width: `${successPercent}%` }}
                      >
                        {trend.success_count > 0 && trend.success_count}
                      </div>
                      <div
                        className="bg-red-500 flex items-center justify-center text-white text-xs font-semibold"
                        style={{ width: `${failurePercent}%` }}
                      >
                        {trend.failure_count > 0 && trend.failure_count}
                      </div>
                    </div>
                    <div className="flex items-center justify-between mt-2 text-xs text-gray-600">
                      <span>✓ {trend.success_count} success</span>
                      <span>✗ {trend.failure_count} failures</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Actions</CardTitle>
          <CardDescription>Manage failed syncs and operations</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={handleRetryFailed} disabled={retrying || stats.error_count === 0}>
            <RefreshCw className={`w-4 h-4 mr-2 ${retrying ? 'animate-spin' : ''}`} />
            {retrying ? 'Retrying...' : `Retry Failed Syncs (${stats.error_count})`}
          </Button>
          {stats.error_count === 0 && (
            <p className="text-sm text-gray-500 mt-2">No failed syncs to retry</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
