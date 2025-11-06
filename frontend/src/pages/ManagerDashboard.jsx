import { useState, useEffect } from "react";
import axios from "axios";
import { API } from "../App";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Progress } from "../components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { 
  TrendingUp, 
  Users, 
  PhoneCall, 
  Target, 
  Award,
  AlertTriangle,
  CheckCircle,
  BarChart3,
  ThumbsUp,
  ThumbsDown,
  Lightbulb,
  Download,
  FileText
} from "lucide-react";
import { Button } from "../components/ui/button";
import { toast } from "sonner";

export default function ManagerDashboard() {
  const [overview, setOverview] = useState(null);
  const [agents, setAgents] = useState([]);
  const [sentiment, setSentiment] = useState(null);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      const [overviewRes, agentsRes, sentimentRes, insightsRes] = await Promise.all([
        axios.get(`${API}/manager/analytics/overview`),
        axios.get(`${API}/manager/analytics/agents`),
        axios.get(`${API}/manager/analytics/sentiment`),
        axios.get(`${API}/manager/analytics/leadership-insights`)
      ]);
      
      setOverview(overviewRes.data);
      setAgents(agentsRes.data);
      setSentiment(sentimentRes.data);
      setInsights(insightsRes.data);
    } catch (error) {
      console.error("Failed to fetch analytics", error);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return "text-green-600";
    if (score >= 60) return "text-yellow-600";
    return "text-red-600";
  };

  const getScoreBg = (score) => {
    if (score >= 80) return "bg-green-50 border-green-200";
    if (score >= 60) return "bg-yellow-50 border-yellow-200";
    return "bg-red-50 border-red-200";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  const totalSentiment = sentiment ? sentiment.positive + sentiment.neutral + sentiment.negative : 1;
  const positivePercent = sentiment ? (sentiment.positive / totalSentiment * 100).toFixed(1) : 0;
  const neutralPercent = sentiment ? (sentiment.neutral / totalSentiment * 100).toFixed(1) : 0;
  const negativePercent = sentiment ? (sentiment.negative / totalSentiment * 100).toFixed(1) : 0;

  const handleExport = async (format) => {
    try {
      const response = await axios.get(`${API}/analytics/export?format=${format}`, {
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const extension = format === 'csv' ? 'csv' : 'txt';
      link.setAttribute('download', `audit_report_${new Date().toISOString().split('T')[0]}.${extension}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success(`Report exported successfully as ${format.toUpperCase()}`);
    } catch (error) {
      console.error('Export failed:', error);
      toast.error('Failed to export report');
    }
  };

  return (
    <div data-testid="manager-dashboard-page">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Space Grotesk' }}>
              Manager Dashboard
            </h1>
            <p className="text-gray-600">Comprehensive analytics and team performance insights</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => handleExport('csv')}>
              <Download className="w-4 h-4 mr-2" />
              Export CSV
            </Button>
            <Button variant="outline" onClick={() => handleExport('pdf')}>
              <FileText className="w-4 h-4 mr-2" />
              Export PDF
            </Button>
          </div>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3 max-w-2xl">
          <TabsTrigger value="overview" data-testid="tab-overview">Overview</TabsTrigger>
          <TabsTrigger value="agents" data-testid="tab-agents">Agent Performance</TabsTrigger>
          <TabsTrigger value="insights" data-testid="tab-insights">Leadership Insights</TabsTrigger>
        </TabsList>

        {/* OVERVIEW TAB */}
        <TabsContent value="overview" className="space-y-6">
          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="border-2 border-blue-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center">
                  <PhoneCall className="w-4 h-4 mr-2 text-blue-600" />
                  Total Audits
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-blue-600">{overview?.total_audits || 0}</div>
                <p className="text-xs text-gray-600 mt-1">
                  {overview?.completed_audits || 0} completed
                </p>
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
                <div className="text-3xl font-bold text-green-600">{overview?.total_site_visits || 0}</div>
                <p className="text-xs text-gray-600 mt-1">
                  {overview?.overall_conversion_rate || 0}% conversion
                </p>
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
                <div className="text-3xl font-bold text-purple-600">{overview?.total_qualified_leads || 0}</div>
                <p className="text-xs text-gray-600 mt-1">
                  {overview?.overall_qualification_rate || 0}% qualification rate
                </p>
              </CardContent>
            </Card>

            <Card className="border-2 border-orange-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center">
                  <TrendingUp className="w-4 h-4 mr-2 text-orange-600" />
                  Avg Score
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-3xl font-bold ${getScoreColor(overview?.avg_overall_score || 0)}`}>
                  {overview?.avg_overall_score || 0}%
                </div>
                <p className="text-xs text-gray-600 mt-1">Overall performance</p>
              </CardContent>
            </Card>
          </div>

          {/* Performance Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Performance Scores</CardTitle>
                <CardDescription>Average scores across all completed calls</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm font-medium">Script Adherence</span>
                    <span className="text-sm font-bold">{overview?.avg_script_score || 0}%</span>
                  </div>
                  <Progress value={overview?.avg_script_score || 0} className="h-2" />
                </div>
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm font-medium">Communication Quality</span>
                    <span className="text-sm font-bold">{overview?.avg_communication_score || 0}%</span>
                  </div>
                  <Progress value={overview?.avg_communication_score || 0} className="h-2" />
                </div>
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm font-medium">Overall Performance</span>
                    <span className="text-sm font-bold">{overview?.avg_overall_score || 0}%</span>
                  </div>
                  <Progress value={overview?.avg_overall_score || 0} className="h-2" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Customer Sentiment</CardTitle>
                <CardDescription>Sentiment distribution across all calls</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <ThumbsUp className="w-5 h-5 text-green-600 mr-2" />
                    <span className="text-sm font-medium">Positive</span>
                  </div>
                  <div className="flex items-center">
                    <span className="text-2xl font-bold text-green-600 mr-2">{sentiment?.positive || 0}</span>
                    <Badge className="bg-green-100 text-green-700">{positivePercent}%</Badge>
                  </div>
                </div>
                <Progress value={parseFloat(positivePercent)} className="h-2 bg-green-100" />

                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <BarChart3 className="w-5 h-5 text-gray-600 mr-2" />
                    <span className="text-sm font-medium">Neutral</span>
                  </div>
                  <div className="flex items-center">
                    <span className="text-2xl font-bold text-gray-600 mr-2">{sentiment?.neutral || 0}</span>
                    <Badge className="bg-gray-100 text-gray-700">{neutralPercent}%</Badge>
                  </div>
                </div>
                <Progress value={parseFloat(neutralPercent)} className="h-2 bg-gray-100" />

                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <ThumbsDown className="w-5 h-5 text-red-600 mr-2" />
                    <span className="text-sm font-medium">Negative</span>
                  </div>
                  <div className="flex items-center">
                    <span className="text-2xl font-bold text-red-600 mr-2">{sentiment?.negative || 0}</span>
                    <Badge className="bg-red-100 text-red-700">{negativePercent}%</Badge>
                  </div>
                </div>
                <Progress value={parseFloat(negativePercent)} className="h-2 bg-red-100" />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* AGENT PERFORMANCE TAB */}
        <TabsContent value="agents" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Users className="w-5 h-5 mr-2" />
                Agent Performance Comparison
              </CardTitle>
              <CardDescription>
                Detailed metrics for each telecalling agent
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {agents.length === 0 ? (
                  <p className="text-center text-gray-500 py-8">No agent data available yet</p>
                ) : (
                  agents.map((agent, index) => (
                    <Card key={agent.agent_id} className={`${getScoreBg(agent.conversion_rate)} border-2`}>
                      <CardContent className="pt-6">
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex items-center">
                            <div className="w-12 h-12 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-full flex items-center justify-center text-white font-bold mr-4">
                              #{index + 1}
                            </div>
                            <div>
                              <h3 className="text-xl font-bold">{agent.agent_id}</h3>
                              <p className="text-sm text-gray-600">{agent.total_calls} calls processed</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className={`text-3xl font-bold ${getScoreColor(agent.conversion_rate)}`}>
                              {agent.conversion_rate}%
                            </div>
                            <p className="text-xs text-gray-600">Conversion Rate</p>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                          <div className="text-center p-3 bg-white rounded-lg">
                            <p className="text-xs text-gray-600 mb-1">Overall Score</p>
                            <p className={`text-xl font-bold ${getScoreColor(agent.avg_overall_score)}`}>
                              {agent.avg_overall_score}%
                            </p>
                          </div>
                          <div className="text-center p-3 bg-white rounded-lg">
                            <p className="text-xs text-gray-600 mb-1">Script</p>
                            <p className={`text-xl font-bold ${getScoreColor(agent.script_adherence_rate)}`}>
                              {agent.script_adherence_rate}%
                            </p>
                          </div>
                          <div className="text-center p-3 bg-white rounded-lg">
                            <p className="text-xs text-gray-600 mb-1">Qualified</p>
                            <p className={`text-xl font-bold ${getScoreColor(agent.lead_qualification_rate)}`}>
                              {agent.lead_qualification_rate}%
                            </p>
                          </div>
                          <div className="text-center p-3 bg-white rounded-lg">
                            <p className="text-xs text-gray-600 mb-1">Site Visits</p>
                            <p className="text-xl font-bold text-green-600">{agent.site_visits_confirmed}</p>
                          </div>
                          <div className="text-center p-3 bg-white rounded-lg">
                            <p className="text-xs text-gray-600 mb-1">Positive</p>
                            <p className="text-xl font-bold text-blue-600">
                              {agent.positive_sentiment_rate}%
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* LEADERSHIP INSIGHTS TAB */}
        <TabsContent value="insights" className="space-y-6">
          {/* Key Insights Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="border-2 border-green-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center text-green-700">
                  <Award className="w-4 h-4 mr-2" />
                  Top Performers
                </CardTitle>
              </CardHeader>
              <CardContent>
                {insights?.top_performers?.length > 0 ? (
                  <div className="space-y-2">
                    {insights.top_performers.map((agent, idx) => (
                      <div key={idx} className="flex justify-between items-center p-2 bg-green-50 rounded">
                        <span className="font-semibold">{agent.agent_id}</span>
                        <Badge className="bg-green-600 text-white">{agent.conversion_rate}%</Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No data yet</p>
                )}
              </CardContent>
            </Card>

            <Card className="border-2 border-orange-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center text-orange-700">
                  <AlertTriangle className="w-4 h-4 mr-2" />
                  Needs Training
                </CardTitle>
              </CardHeader>
              <CardContent>
                {insights?.needs_training?.length > 0 ? (
                  <div className="space-y-2">
                    {insights.needs_training.map((agent, idx) => (
                      <div key={idx} className="flex justify-between items-center p-2 bg-orange-50 rounded">
                        <span className="font-semibold">{agent.agent_id}</span>
                        <Badge className="bg-orange-600 text-white">{agent.conversion_rate}%</Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">All agents performing well</p>
                )}
              </CardContent>
            </Card>

            <Card className="border-2 border-blue-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center text-blue-700">
                  <TrendingUp className="w-4 h-4 mr-2" />
                  Forecast
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="text-center p-2 bg-blue-50 rounded">
                    <p className="text-xs text-gray-600">Monthly Bookings</p>
                    <p className="text-2xl font-bold text-blue-600">
                      {insights?.forecasted_monthly_bookings || 0}
                    </p>
                  </div>
                  <div className="text-center p-2 bg-blue-50 rounded">
                    <p className="text-xs text-gray-600">Avg Conversion</p>
                    <p className="text-2xl font-bold text-blue-600">
                      {insights?.avg_conversion_rate || 0}%
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Recommendations */}
          <Card className="border-2 border-purple-200">
            <CardHeader className="bg-purple-50">
              <CardTitle className="flex items-center text-purple-700">
                <Lightbulb className="w-5 h-5 mr-2" />
                Leadership Recommendations
              </CardTitle>
              <CardDescription>AI-powered insights for management decisions</CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="space-y-3">
                {insights?.recommendations?.map((rec, idx) => (
                  <div key={idx} className="flex items-start p-4 bg-white rounded-lg border-l-4 border-purple-400">
                    <span className="text-2xl mr-3">{rec.substring(0, 2)}</span>
                    <p className="text-sm flex-1">{rec.substring(2).trim()}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Training Gaps */}
          {insights?.common_training_gaps?.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Common Training Gaps</CardTitle>
                <CardDescription>Most frequently missed script points across all agents</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {insights.common_training_gaps.map((gap, idx) => (
                    <div key={idx} className="flex justify-between items-center p-3 bg-red-50 rounded-lg border border-red-200">
                      <span className="text-sm flex-1">{gap.point}</span>
                      <Badge className="bg-red-600 text-white">Missed {gap.frequency}x</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
