import { useState, useEffect } from "react";
import axios from "axios";
import { API } from "../App";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Separator } from "../components/ui/separator";
import { toast } from "sonner";
import { ArrowLeft, TrendingUp, MessageSquare, Target, AlertCircle } from "lucide-react";
import { format } from "date-fns";

export default function AuditDetail() {
  const { auditId } = useParams();
  const navigate = useNavigate();
  const [audit, setAudit] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAuditDetail();
  }, [auditId]);

  const fetchAuditDetail = async () => {
    try {
      const response = await axios.get(`${API}/audits/${auditId}`);
      setAudit(response.data);
    } catch (error) {
      toast.error("Failed to fetch audit details");
      navigate("/audits");
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return "text-green-600";
    if (score >= 60) return "text-yellow-600";
    return "text-red-600";
  };

  const getScoreBackground = (score) => {
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

  if (!audit || !audit.analysis) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-600">Audit details not available</p>
        <Button onClick={() => navigate("/audits")} className="mt-4">
          Back to Audits
        </Button>
      </div>
    );
  }

  const analysis = audit.analysis;

  return (
    <div data-testid="audit-detail-page">
      <Button
        data-testid="back-to-audits-button"
        onClick={() => navigate("/audits")}
        variant="ghost"
        className="mb-4"
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Audits
      </Button>

      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Space Grotesk' }}>
          Audit Details
        </h1>
        <p className="text-gray-600">{audit.audio_filename}</p>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
        <Card className={`border-2 ${getScoreBackground(audit.overall_score)}`}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Overall Score</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-4xl font-bold ${getScoreColor(audit.overall_score)}`}>
              {audit.overall_score.toFixed(1)}%
            </div>
            {audit.compliance_result && (
              <Badge className={`mt-3 ${
                audit.compliance_result === 'PASS' 
                  ? 'bg-green-500 text-white' 
                  : 'bg-red-500 text-white'
              }`}>
                {audit.compliance_result === 'PASS' ? '✓ COMPLIANT' : '✗ NON-COMPLIANT'}
              </Badge>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Script Adherence</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-4xl font-bold ${getScoreColor(analysis.script_adherence_score)}`}>
              {analysis.script_adherence_score}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Communication</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-4xl font-bold ${getScoreColor(analysis.communication_score)}`}>
              {analysis.communication_score}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Sentiment</CardTitle>
          </CardHeader>
          <CardContent>
            <Badge className={`text-sm mt-2 ${
              analysis.sentiment === 'positive' ? 'bg-green-100 text-green-700' :
              analysis.sentiment === 'negative' ? 'bg-red-100 text-red-700' :
              'bg-gray-100 text-gray-700'
            }`}>
              {analysis.sentiment?.toUpperCase()}
            </Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Lead Status</CardTitle>
          </CardHeader>
          <CardContent>
            <Badge className="text-sm mt-2">
              {analysis.lead_status?.replace("_", " ").toUpperCase()}
            </Badge>
            <p className={`text-sm mt-2 ${analysis.outcome_achieved ? 'text-green-600' : 'text-red-600'}`}>
              {analysis.outcome_achieved ? "✓ Outcome Achieved" : "✗ Outcome Not Achieved"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Performance Metrics */}
      {analysis.performance_metrics && (
        <Card className="mb-6 border-2 border-blue-200">
          <CardHeader className="bg-blue-50">
            <CardTitle>Performance Metrics</CardTitle>
            <CardDescription>Key performance indicators for this call</CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-white rounded-lg border">
                <p className="text-sm text-gray-600 mb-1">Script Followed</p>
                <p className={`font-bold text-2xl ${analysis.script_followed ? 'text-green-600' : 'text-red-600'}`}>
                  {analysis.script_followed ? '✓ Yes' : '✗ No'}
                </p>
              </div>
              <div className="text-center p-4 bg-white rounded-lg border">
                <p className="text-sm text-gray-600 mb-1">Lead Qualified</p>
                <p className={`font-bold text-2xl ${analysis.lead_qualified ? 'text-green-600' : 'text-red-600'}`}>
                  {analysis.lead_qualified ? '✓ Yes' : '✗ No'}
                </p>
              </div>
              <div className="text-center p-4 bg-white rounded-lg border">
                <p className="text-sm text-gray-600 mb-1">Site Visit Confirmed</p>
                <p className={`font-bold text-2xl ${analysis.site_visit_confirmed ? 'text-green-600' : 'text-red-600'}`}>
                  {analysis.site_visit_confirmed ? '✓ Yes' : '✗ No'}
                </p>
              </div>
              <div className="text-center p-4 bg-white rounded-lg border">
                <p className="text-sm text-gray-600 mb-1">Call Duration</p>
                <p className="font-bold text-2xl text-blue-600">
                  {analysis.call_duration_seconds ? `${Math.floor(analysis.call_duration_seconds / 60)}m ${analysis.call_duration_seconds % 60}s` : 'N/A'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Call Information */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Call Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Agent Number:</span>
              <p className="font-medium">{audit.agent_number}</p>
            </div>
            <div>
              <span className="text-gray-600">Customer Number:</span>
              <p className="font-medium">{audit.customer_number}</p>
            </div>
            <div>
              <span className="text-gray-600">Call Date:</span>
              <p className="font-medium">{format(new Date(audit.call_date), "MMM dd, yyyy HH:mm")}</p>
            </div>
            <div>
              <span className="text-gray-600">Processed:</span>
              <p className="font-medium">{format(new Date(audit.processed_at), "MMM dd, yyyy HH:mm")}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Script Details - Expected Outcomes */}
      {audit.script_details && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center">
              <Target className="w-5 h-5 mr-2 text-blue-600" />
              Expected Script & Outcomes
            </CardTitle>
            <CardDescription>The telecalling script used for this audit</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">Script: {audit.script_details.title}</h4>
              <Badge variant="secondary">{audit.script_details.category}</Badge>
            </div>
            <Separator />
            <div>
              <h4 className="font-semibold text-blue-700 mb-2">📋 Script Content</h4>
              <div className="bg-blue-50 p-4 rounded-lg">
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{audit.script_details.content}</p>
              </div>
            </div>
            <Separator />
            <div>
              <h4 className="font-semibold text-purple-700 mb-2">🎯 Expected Outcomes</h4>
              <ul className="list-disc list-inside space-y-1 bg-purple-50 p-4 rounded-lg">
                {audit.script_details.expected_outcomes?.map((outcome, idx) => (
                  <li key={idx} className="text-sm text-gray-700">{outcome}</li>
                ))}
              </ul>
            </div>
            <Separator />
            <div>
              <h4 className="font-semibold text-indigo-700 mb-2">🔑 Key Points to Cover</h4>
              <ul className="list-disc list-inside space-y-1 bg-indigo-50 p-4 rounded-lg">
                {audit.script_details.key_points?.map((point, idx) => (
                  <li key={idx} className="text-sm text-gray-700">{point}</li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Transcript */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center">
            <MessageSquare className="w-5 h-5 mr-2" />
            Actual Conversation Transcript
          </CardTitle>
          <CardDescription>What was actually said during the call</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="bg-gray-50 p-4 rounded-lg max-h-64 overflow-y-auto">
            <p className="text-sm whitespace-pre-wrap">{audit.transcript}</p>
          </div>
        </CardContent>
      </Card>

      {/* Script Adherence Details */}
      {analysis.script_adherence_details && (
        <Card className="mb-6 border-2 border-orange-200">
          <CardHeader className="bg-orange-50">
            <CardTitle className="flex items-center">
              <Target className="w-5 h-5 mr-2 text-orange-600" />
              Script Adherence Analysis
            </CardTitle>
            <CardDescription>Comparison of expected vs actual performance</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-6">
            <div className="bg-green-50 p-4 rounded-lg border border-green-200">
              <h4 className="font-semibold text-green-700 mb-3 flex items-center">
                <span className="text-xl mr-2">✓</span>
                Key Points Successfully Followed
              </h4>
              <ul className="space-y-2">
                {analysis.script_adherence_details.followed_points?.map((point, idx) => (
                  <li key={idx} className="text-sm text-gray-700 flex items-start">
                    <span className="text-green-600 mr-2 mt-0.5">•</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>
            <Separator />
            <div className="bg-red-50 p-4 rounded-lg border border-red-200">
              <h4 className="font-semibold text-red-700 mb-3 flex items-center">
                <span className="text-xl mr-2">✗</span>
                Key Points Missed or Not Addressed
              </h4>
              <ul className="space-y-2">
                {analysis.script_adherence_details.missed_points?.map((point, idx) => (
                  <li key={idx} className="text-sm text-gray-700 flex items-start">
                    <span className="text-red-600 mr-2 mt-0.5">•</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>
            {analysis.script_adherence_details.deviations && (
              <>
                <Separator />
                <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                  <h4 className="font-semibold text-yellow-700 mb-3 flex items-center">
                    <span className="text-xl mr-2">⚠</span>
                    Deviations from Script
                  </h4>
                  <p className="text-sm text-gray-700">{analysis.script_adherence_details.deviations}</p>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* Communication Analysis */}
      {analysis.communication_analysis && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center">
              <TrendingUp className="w-5 h-5 mr-2" />
              Communication Analysis
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">Tone</p>
                <p className="font-semibold capitalize">{analysis.communication_analysis.tone}</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">Clarity</p>
                <p className="font-semibold text-lg">{analysis.communication_analysis.clarity}%</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">Listening Skills</p>
                <p className="font-semibold text-lg">{analysis.communication_analysis.listening_skills}%</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">Objection Handling</p>
                <p className="font-semibold text-lg">{analysis.communication_analysis.objection_handling}%</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Strengths & Improvements */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-green-700">Strengths</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {analysis.strengths?.map((strength, idx) => (
                <li key={idx} className="flex items-start">
                  <span className="text-green-600 mr-2">✓</span>
                  <span className="text-sm">{strength}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-orange-700">Areas for Improvement</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {analysis.areas_for_improvement?.map((area, idx) => (
                <li key={idx} className="flex items-start">
                  <AlertCircle className="w-4 h-4 text-orange-600 mr-2 mt-0.5" />
                  <span className="text-sm">{area}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-700">{analysis.summary}</p>
        </CardContent>
      </Card>
    </div>
  );
}
