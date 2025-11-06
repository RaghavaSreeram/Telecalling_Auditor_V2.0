import { useState, useEffect } from "react";
import axios from "axios";
import { API } from "../App";
import { useAuth } from "../context/AuthContext";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Progress } from "../components/ui/progress";
import { useNavigate } from "react-router-dom";
import { CheckCircle, Target, TrendingUp, Phone, Award } from "lucide-react";

export default function AuditorDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState(null);
  const [assignedAudits, setAssignedAudits] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAuditorData();
  }, []);

  const fetchAuditorData = async () => {
    try {
      const [metricsRes, auditsRes] = await Promise.all([
        axios.get(`${API}/auditor/my-metrics`),
        axios.get(`${API}/auditor/assigned-audits`)
      ]);
      
      setMetrics(metricsRes.data);
      setAssignedAudits(auditsRes.data);
    } catch (error) {
      console.error("Failed to fetch auditor data", error);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return "text-green-600";
    if (score >= 60) return "text-yellow-600";
    return "text-red-600";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div data-testid="auditor-dashboard-page">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Space Grotesk' }}>
          My Performance Dashboard
        </h1>
        <p className="text-gray-600">Welcome back, {user?.full_name}!</p>
        <Badge className="mt-2" variant="outline">Role: Auditor</Badge>
        {user?.team_id && <Badge className="mt-2 ml-2" variant="outline">Team: {user.team_id}</Badge>}
      </div>

      {/* Personal Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <Card className="border-2 border-blue-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center">
              <Phone className="w-4 h-4 mr-2 text-blue-600" />
              Total Calls
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-600">{metrics?.total_calls || 0}</div>
            <p className="text-xs text-gray-600 mt-1">Calls processed</p>
          </CardContent>
        </Card>

        <Card className="border-2 border-green-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center">
              <Target className="w-4 h-4 mr-2 text-green-600" />
              Site Visits
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">{metrics?.site_visits_confirmed || 0}</div>
            <p className="text-xs text-gray-600 mt-1">Confirmed visits</p>
          </CardContent>
        </Card>

        <Card className="border-2 border-purple-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center">
              <CheckCircle className="w-4 h-4 mr-2 text-purple-600" />
              Qualified Leads
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-purple-600">{metrics?.leads_qualified || 0}</div>
            <p className="text-xs text-gray-600 mt-1">Successfully qualified</p>
          </CardContent>
        </Card>

        <Card className="border-2 border-orange-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center">
              <Award className="w-4 h-4 mr-2 text-orange-600" />
              My Score
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold ${getScoreColor(metrics?.avg_score || 0)}`}>
              {metrics?.avg_score || 0}%
            </div>
            <p className="text-xs text-gray-600 mt-1">Average performance</p>
          </CardContent>
        </Card>
      </div>

      {/* Performance Progress */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="flex items-center">
            <TrendingUp className="w-5 h-5 mr-2" />
            My Performance Metrics
          </CardTitle>
          <CardDescription>Your personal performance indicators</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-sm font-medium">Conversion Rate</span>
              <span className="text-sm font-bold">{metrics?.conversion_rate || 0}%</span>
            </div>
            <Progress value={metrics?.conversion_rate || 0} className="h-2" />
          </div>
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-sm font-medium">Average Score</span>
              <span className="text-sm font-bold">{metrics?.avg_score || 0}%</span>
            </div>
            <Progress value={metrics?.avg_score || 0} className="h-2" />
          </div>
        </CardContent>
      </Card>

      {/* Assigned Audits */}
      <Card>
        <CardHeader>
          <CardTitle>My Recent Calls</CardTitle>
          <CardDescription>Your assigned call audits</CardDescription>
        </CardHeader>
        <CardContent>
          {assignedAudits.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Phone className="w-12 h-12 mx-auto mb-3 text-gray-400" />
              <p>No audits assigned yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {assignedAudits.slice(0, 10).map((audit) => (
                <div
                  key={audit.id}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer"
                  onClick={() => navigate(`/audits/${audit.id}`)}
                >
                  <div className="flex-1">
                    <h4 className="font-semibold">{audit.audio_filename}</h4>
                    <p className="text-sm text-gray-600">Customer: {audit.customer_number}</p>
                  </div>
                  <div className="text-right">
                    <Badge variant={audit.status === 'completed' ? 'default' : 'secondary'}>
                      {audit.status}
                    </Badge>
                    {audit.overall_score && (
                      <p className={`text-lg font-bold mt-1 ${getScoreColor(audit.overall_score)}`}>
                        {audit.overall_score.toFixed(1)}%
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
