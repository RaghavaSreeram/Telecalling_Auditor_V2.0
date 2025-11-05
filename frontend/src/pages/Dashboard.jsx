import { useState, useEffect } from "react";
import axios from "axios";
import { API } from "../App";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { FileAudio, CheckCircle, Clock, FileText, TrendingUp } from "lucide-react";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/stats`);
      setStats(response.data);
    } catch (error) {
      console.error("Failed to fetch stats", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  const statCards = [
    {
      title: "Total Audits",
      value: stats?.total_audits || 0,
      icon: FileAudio,
      color: "from-blue-500 to-cyan-500",
      testId: "total-audits-stat"
    },
    {
      title: "Completed",
      value: stats?.completed_audits || 0,
      icon: CheckCircle,
      color: "from-green-500 to-emerald-500",
      testId: "completed-audits-stat"
    },
    {
      title: "Pending",
      value: stats?.pending_audits || 0,
      icon: Clock,
      color: "from-yellow-500 to-orange-500",
      testId: "pending-audits-stat"
    },
    {
      title: "Total Scripts",
      value: stats?.total_scripts || 0,
      icon: FileText,
      color: "from-purple-500 to-pink-500",
      testId: "total-scripts-stat"
    },
    {
      title: "Average Score",
      value: `${stats?.average_score || 0}%`,
      icon: TrendingUp,
      color: "from-indigo-500 to-purple-500",
      testId: "average-score-stat"
    },
  ];

  return (
    <div data-testid="dashboard-page">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Space Grotesk' }}>
          Dashboard
        </h1>
        <p className="text-gray-600">Welcome to your telecalling auditor dashboard</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {statCards.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <Card key={index} className="card-hover" data-testid={stat.testId}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-gray-600">
                  {stat.title}
                </CardTitle>
                <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${stat.color} flex items-center justify-center`}>
                  <Icon className="w-5 h-5 text-white" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold" style={{ fontFamily: 'Space Grotesk' }}>
                  {stat.value}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Get started with common tasks</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <a
              href="/upload"
              data-testid="quick-action-upload"
              className="block p-4 rounded-lg border border-gray-200 hover:border-indigo-500 hover:bg-indigo-50 transition-colors"
            >
              <div className="flex items-center">
                <FileAudio className="w-5 h-5 text-indigo-600 mr-3" />
                <div>
                  <h3 className="font-semibold">Upload Audio</h3>
                  <p className="text-sm text-gray-600">Upload new call recording for analysis</p>
                </div>
              </div>
            </a>
            <a
              href="/scripts"
              data-testid="quick-action-scripts"
              className="block p-4 rounded-lg border border-gray-200 hover:border-purple-500 hover:bg-purple-50 transition-colors"
            >
              <div className="flex items-center">
                <FileText className="w-5 h-5 text-purple-600 mr-3" />
                <div>
                  <h3 className="font-semibold">Manage Scripts</h3>
                  <p className="text-sm text-gray-600">Create and edit telecalling scripts</p>
                </div>
              </div>
            </a>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>System Overview</CardTitle>
            <CardDescription>Current system status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                <span className="text-sm font-medium">AssemblyAI Integration</span>
                <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-semibold">Active</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                <span className="text-sm font-medium">OpenAI Analysis</span>
                <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-semibold">Active</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                <span className="text-sm font-medium">Database</span>
                <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-semibold">Connected</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
