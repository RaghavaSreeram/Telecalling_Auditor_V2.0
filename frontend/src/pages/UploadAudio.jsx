import { useState, useEffect } from "react";
import axios from "axios";
import { API } from "../App";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { toast } from "sonner";
import { Upload, FileAudio } from "lucide-react";

export default function UploadAudio() {
  const [scripts, setScripts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [file, setFile] = useState(null);
  const [formData, setFormData] = useState({
    agent_number: "",
    customer_number: "",
    script_id: "",
    call_date: new Date().toISOString().slice(0, 16),
  });

  useEffect(() => {
    fetchScripts();
  }, []);

  const fetchScripts = async () => {
    try {
      const response = await axios.get(`${API}/scripts`);
      setScripts(response.data);
    } catch (error) {
      toast.error("Failed to fetch scripts");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!file) {
      toast.error("Please select an audio file");
      return;
    }

    if (!formData.script_id) {
      toast.error("Please select a script");
      return;
    }

    setLoading(true);

    try {
      const uploadFormData = new FormData();
      uploadFormData.append("audio_file", file);
      uploadFormData.append("agent_number", formData.agent_number);
      uploadFormData.append("customer_number", formData.customer_number);
      uploadFormData.append("script_id", formData.script_id);
      uploadFormData.append("call_date", formData.call_date);

      const response = await axios.post(`${API}/audits/upload`, uploadFormData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      toast.success("Audio uploaded successfully! Processing started.");
      setFile(null);
      setFormData({
        agent_number: "",
        customer_number: "",
        script_id: "",
        call_date: new Date().toISOString().slice(0, 16),
      });

      // Reset file input
      const fileInput = document.getElementById("audio-file");
      if (fileInput) fileInput.value = "";
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to upload audio");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="upload-audio-page">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Space Grotesk' }}>
          Upload Audio
        </h1>
        <p className="text-gray-600">Upload call recordings for automated analysis</p>
      </div>

      <div className="max-w-2xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>New Audio Audit</CardTitle>
            <CardDescription>Upload a call recording and provide details for analysis</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="audio-file">Audio File</Label>
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-indigo-500 transition-colors">
                  <FileAudio className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <Input
                    id="audio-file"
                    data-testid="audio-file-input"
                    type="file"
                    accept="audio/*"
                    onChange={(e) => setFile(e.target.files[0])}
                    className="max-w-xs mx-auto"
                    required
                  />
                  {file && (
                    <p className="mt-2 text-sm text-gray-600">Selected: {file.name}</p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="agent_number">Agent Number</Label>
                  <Input
                    id="agent_number"
                    data-testid="agent-number-input"
                    value={formData.agent_number}
                    onChange={(e) => setFormData({ ...formData, agent_number: e.target.value })}
                    placeholder="e.g., AG001"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="customer_number">Customer Number</Label>
                  <Input
                    id="customer_number"
                    data-testid="customer-number-input"
                    value={formData.customer_number}
                    onChange={(e) => setFormData({ ...formData, customer_number: e.target.value })}
                    placeholder="e.g., +1234567890"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="script_id">Select Script</Label>
                <Select
                  value={formData.script_id}
                  onValueChange={(value) => setFormData({ ...formData, script_id: value })}
                  required
                >
                  <SelectTrigger data-testid="script-select">
                    <SelectValue placeholder="Choose a script" />
                  </SelectTrigger>
                  <SelectContent>
                    {scripts.map((script) => (
                      <SelectItem key={script.id} value={script.id} data-testid={`script-option-${script.id}`}>
                        {script.title} ({script.category})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="call_date">Call Date & Time</Label>
                <Input
                  id="call_date"
                  data-testid="call-date-input"
                  type="datetime-local"
                  value={formData.call_date}
                  onChange={(e) => setFormData({ ...formData, call_date: e.target.value })}
                  required
                />
              </div>

              <Button
                data-testid="submit-upload-button"
                type="submit"
                className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4 mr-2" />
                    Upload & Process
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <h3 className="font-semibold text-blue-900 mb-2">Processing Information</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• Audio will be transcribed using AssemblyAI</li>
            <li>• Transcript will be analyzed against selected script</li>
            <li>• Processing typically takes 2-5 minutes</li>
            <li>• You'll receive a detailed performance report</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
