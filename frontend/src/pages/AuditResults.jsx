import { useState, useEffect } from "react";
import axios from "axios";
import { API } from "../App";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { toast } from "sonner";
import { Eye, FileAudio, Clock, CheckCircle, XCircle } from "lucide-react";
import { format } from "date-fns";

export default function AuditResults() {
  const [audits, setAudits] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchAudits();
    const interval = setInterval(fetchAudits, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchAudits = async () => {
    try {
      const response = await axios.get(`${API}/audits`);
      setAudits(response.data);
    } catch (error) {
      toast.error("Failed to fetch audits");
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case "failed":
        return <XCircle className="w-5 h-5 text-red-600" />;
      case "processing":
        return <Clock className="w-5 h-5 text-blue-600 animate-spin" />;
      default:
        return <Clock className="w-5 h-5 text-gray-600" />;
    }
  };

  const getStatusBadge = (status) => {
    const variants = {
      completed: "default",
      pending: "secondary",
      processing: "outline",
      failed: "destructive",
    };
    return (
      <Badge variant={variants[status] || "secondary"}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    );
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
    <div data-testid="audit-results-page">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Space Grotesk' }}>
          Audit Results
        </h1>
        <p className="text-gray-600">View and analyze call audit results</p>
      </div>

      {audits.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <FileAudio className="w-16 h-16 text-gray-400 mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Audits Yet</h3>
            <p className="text-gray-600 mb-4">Upload your first audio file to get started</p>
            <Button data-testid="empty-state-upload-button" onClick={() => navigate("/upload")} className="bg-gradient-to-r from-indigo-600 to-purple-600">
              Upload Audio
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {audits.map((audit) => (
            <Card key={audit.id} className="card-hover" data-testid={`audit-card-${audit.id}`}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4 flex-1">
                    <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-lg flex items-center justify-center flex-shrink-0">
                      {getStatusIcon(audit.status)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="text-lg font-semibold">{audit.audio_filename}</h3>
                        {getStatusBadge(audit.status)}
                        {audit.compliance_result && (
                          <Badge className={`${
                            audit.compliance_result === 'PASS' 
                              ? 'bg-green-500 text-white' 
                              : 'bg-red-500 text-white'
                          }`}>
                            {audit.compliance_result === 'PASS' ? '✓ Compliant' : '✗ Non-Compliant'}
                          </Badge>
                        )}
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <span className="text-gray-600">Agent:</span>
                          <p className="font-medium">{audit.agent_number}</p>
                        </div>
                        <div>
                          <span className="text-gray-600">Customer:</span>
                          <p className="font-medium">{audit.customer_number}</p>
                        </div>
                        <div>
                          <span className="text-gray-600">Call Date:</span>
                          <p className="font-medium">
                            {format(new Date(audit.call_date), "MMM dd, yyyy")}
                          </p>
                        </div>
                        {audit.overall_score !== null && (
                          <div>
                            <span className="text-gray-600">Score:</span>
                            <p className={`font-bold text-lg ${getScoreColor(audit.overall_score)}`}>
                              {audit.overall_score.toFixed(1)}%
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  {audit.status === "completed" && (
                    <Button
                      data-testid={`view-audit-${audit.id}`}
                      onClick={() => navigate(`/audits/${audit.id}`)}
                      variant="outline"
                      size="sm"
                    >
                      <Eye className="w-4 h-4 mr-1" />
                      View Details
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
