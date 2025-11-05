import { useState, useEffect } from "react";
import axios from "axios";
import { API } from "../App";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Badge } from "../components/ui/badge";
import { toast } from "sonner";
import { Plus, Edit, Trash2, FileText } from "lucide-react";

export default function Scripts() {
  const [scripts, setScripts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingScript, setEditingScript] = useState(null);
  const [formData, setFormData] = useState({
    title: "",
    content: "",
    category: "general",
    expected_outcomes: "",
    key_points: "",
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
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const payload = {
      ...formData,
      expected_outcomes: formData.expected_outcomes.split(",").map((s) => s.trim()).filter(Boolean),
      key_points: formData.key_points.split(",").map((s) => s.trim()).filter(Boolean),
    };

    try {
      if (editingScript) {
        await axios.put(`${API}/scripts/${editingScript.id}`, payload);
        toast.success("Script updated successfully");
      } else {
        await axios.post(`${API}/scripts`, payload);
        toast.success("Script created successfully");
      }
      setDialogOpen(false);
      resetForm();
      fetchScripts();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save script");
    }
  };

  const handleEdit = (script) => {
    setEditingScript(script);
    setFormData({
      title: script.title,
      content: script.content,
      category: script.category,
      expected_outcomes: script.expected_outcomes.join(", "),
      key_points: script.key_points.join(", "),
    });
    setDialogOpen(true);
  };

  const handleDelete = async (scriptId) => {
    if (!window.confirm("Are you sure you want to delete this script?")) return;

    try {
      await axios.delete(`${API}/scripts/${scriptId}`);
      toast.success("Script deleted successfully");
      fetchScripts();
    } catch (error) {
      toast.error("Failed to delete script");
    }
  };

  const resetForm = () => {
    setFormData({
      title: "",
      content: "",
      category: "general",
      expected_outcomes: "",
      key_points: "",
    });
    setEditingScript(null);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div data-testid="scripts-page">
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Space Grotesk' }}>
            Scripts Management
          </h1>
          <p className="text-gray-600">Create and manage your telecalling scripts</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) resetForm();
        }}>
          <DialogTrigger asChild>
            <Button data-testid="create-script-button" className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700">
              <Plus className="w-4 h-4 mr-2" />
              Create Script
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{editingScript ? "Edit Script" : "Create New Script"}</DialogTitle>
              <DialogDescription>
                {editingScript ? "Update your telecalling script" : "Add a new telecalling script"}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="title">Script Title</Label>
                <Input
                  id="title"
                  data-testid="script-title-input"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="category">Category</Label>
                <Input
                  id="category"
                  data-testid="script-category-input"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  placeholder="e.g., general, follow-up, cold-call"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="content">Script Content</Label>
                <Textarea
                  id="content"
                  data-testid="script-content-input"
                  value={formData.content}
                  onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                  rows={8}
                  placeholder="Enter the complete script..."
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="expected_outcomes">Expected Outcomes (comma-separated)</Label>
                <Input
                  id="expected_outcomes"
                  data-testid="script-outcomes-input"
                  value={formData.expected_outcomes}
                  onChange={(e) => setFormData({ ...formData, expected_outcomes: e.target.value })}
                  placeholder="Schedule site visit, Qualify lead, Close deal"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="key_points">Key Points (comma-separated)</Label>
                <Input
                  id="key_points"
                  data-testid="script-keypoints-input"
                  value={formData.key_points}
                  onChange={(e) => setFormData({ ...formData, key_points: e.target.value })}
                  placeholder="Introduce company, Ask qualifying questions, Present offer"
                  required
                />
              </div>

              <div className="flex justify-end space-x-2">
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                  Cancel
                </Button>
                <Button data-testid="save-script-button" type="submit" className="bg-gradient-to-r from-indigo-600 to-purple-600">
                  {editingScript ? "Update" : "Create"}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {scripts.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <FileText className="w-16 h-16 text-gray-400 mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Scripts Yet</h3>
            <p className="text-gray-600 mb-4">Create your first telecalling script to get started</p>
            <Button data-testid="empty-state-create-button" onClick={() => setDialogOpen(true)} className="bg-gradient-to-r from-indigo-600 to-purple-600">
              <Plus className="w-4 h-4 mr-2" />
              Create Script
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {scripts.map((script) => (
            <Card key={script.id} className="card-hover" data-testid={`script-card-${script.id}`}>
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <CardTitle className="text-xl mb-2">{script.title}</CardTitle>
                    <Badge variant="secondary">{script.category}</Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <p className="text-sm font-semibold text-gray-700 mb-1">Script Preview:</p>
                    <p className="text-sm text-gray-600 line-clamp-3">{script.content}</p>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Used: {script.usage_count} times</span>
                    <span className="text-gray-600">Avg: {script.avg_score.toFixed(1)}%</span>
                  </div>
                  <div className="flex space-x-2 pt-2">
                    <Button
                      data-testid={`edit-script-${script.id}`}
                      size="sm"
                      variant="outline"
                      className="flex-1"
                      onClick={() => handleEdit(script)}
                    >
                      <Edit className="w-4 h-4 mr-1" />
                      Edit
                    </Button>
                    <Button
                      data-testid={`delete-script-${script.id}`}
                      size="sm"
                      variant="destructive"
                      className="flex-1"
                      onClick={() => handleDelete(script.id)}
                    >
                      <Trash2 className="w-4 h-4 mr-1" />
                      Delete
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
