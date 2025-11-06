import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import { Checkbox } from "./ui/checkbox";
import { RadioGroup, RadioGroupItem } from "./ui/radio-group";
import { Progress } from "./ui/progress";
import { Badge } from "./ui/badge";
import { Save, Send, Star } from "lucide-react";

export default function AuditForm({ 
  formSchema, 
  initialResponses = {},
  onSaveDraft,
  onSubmit,
  readOnly = false 
}) {
  const [responses, setResponses] = useState(initialResponses);
  const [overallScore, setOverallScore] = useState(0);
  const [comments, setComments] = useState("");

  useEffect(() => {
    calculateScore();
  }, [responses]);

  const calculateScore = () => {
    if (!formSchema) return;
    
    let totalScore = 0;
    let totalWeight = 0;

    formSchema.fields.forEach(field => {
      const response = responses[field.id];
      const weight = field.weight || 1.0;

      if (field.type === "number" || field.type === "rating") {
        const value = parseFloat(response) || 0;
        const maxValue = field.max_value || 10;
        totalScore += (value / maxValue) * weight * 100;
        totalWeight += weight;
      } else if (field.type === "checkbox") {
        totalScore += response ? weight * 100 : 0;
        totalWeight += weight;
      }
    });

    const score = totalWeight > 0 ? totalScore / totalWeight : 0;
    setOverallScore(Math.round(score));
  };

  const handleFieldChange = (fieldId, value) => {
    setResponses(prev => ({
      ...prev,
      [fieldId]: value
    }));
  };

  const handleSaveDraft = () => {
    if (onSaveDraft) {
      onSaveDraft({ responses, comments, overall_score: overallScore });
    }
  };

  const handleSubmit = () => {
    if (onSubmit) {
      onSubmit({ responses, comments, overall_score: overallScore });
    }
  };

  const renderField = (field) => {
    const value = responses[field.id];

    switch (field.type) {
      case "number":
        return (
          <div key={field.id} className="space-y-2">
            <Label htmlFor={field.id}>
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            <Input
              id={field.id}
              type="number"
              min={field.min_value}
              max={field.max_value}
              value={value || ""}
              onChange={(e) => handleFieldChange(field.id, e.target.value)}
              disabled={readOnly}
              placeholder={`${field.min_value || 0} - ${field.max_value || 100}`}
            />
            {field.weight && (
              <p className="text-xs text-gray-500">Weight: {field.weight}x</p>
            )}
          </div>
        );

      case "rating":
        return (
          <div key={field.id} className="space-y-2">
            <Label>
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            <div className="flex items-center space-x-2">
              {[...Array(field.max_value || 5)].map((_, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => !readOnly && handleFieldChange(field.id, i + 1)}
                  disabled={readOnly}
                  className="p-1"
                >
                  <Star
                    className={`w-6 h-6 ${
                      (value || 0) > i ? "fill-yellow-400 text-yellow-400" : "text-gray-300"
                    }`}
                  />
                </button>
              ))}
              <span className="text-sm text-gray-600 ml-2">{value || 0} / {field.max_value || 5}</span>
            </div>
          </div>
        );

      case "checkbox":
        return (
          <div key={field.id} className="flex items-center space-x-2">
            <Checkbox
              id={field.id}
              checked={value || false}
              onCheckedChange={(checked) => handleFieldChange(field.id, checked)}
              disabled={readOnly}
            />
            <Label htmlFor={field.id} className="cursor-pointer">
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </Label>
          </div>
        );

      case "text":
      case "textarea":
        return (
          <div key={field.id} className="space-y-2">
            <Label htmlFor={field.id}>
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            <Textarea
              id={field.id}
              value={value || ""}
              onChange={(e) => handleFieldChange(field.id, e.target.value)}
              disabled={readOnly}
              rows={3}
            />
          </div>
        );

      case "select":
        return (
          <div key={field.id} className="space-y-2">
            <Label htmlFor={field.id}>
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            <RadioGroup
              value={value}
              onValueChange={(val) => handleFieldChange(field.id, val)}
              disabled={readOnly}
            >
              {field.options?.map((option, idx) => (
                <div key={idx} className="flex items-center space-x-2">
                  <RadioGroupItem value={option} id={`${field.id}-${idx}`} />
                  <Label htmlFor={`${field.id}-${idx}`} className="cursor-pointer">
                    {option}
                  </Label>
                </div>
              ))}
            </RadioGroup>
          </div>
        );

      default:
        return null;
    }
  };

  if (!formSchema) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-gray-500">
          No audit form schema loaded
        </CardContent>
      </Card>
    );
  }

  const completedFields = Object.keys(responses).length;
  const totalFields = formSchema.fields.filter(f => f.required).length;
  const progress = totalFields > 0 ? (completedFields / totalFields) * 100 : 0;

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

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle>{formSchema.name}</CardTitle>
            {formSchema.description && (
              <CardDescription>{formSchema.description}</CardDescription>
            )}
          </div>
          <div className={`text-center p-4 rounded-lg border-2 ${getScoreBg(overallScore)}`}>
            <div className={`text-3xl font-bold ${getScoreColor(overallScore)}`}>
              {overallScore}%
            </div>
            <p className="text-xs text-gray-600 mt-1">Current Score</p>
          </div>
        </div>
        {!readOnly && (
          <div className="mt-4">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-600">Progress</span>
              <span className="text-gray-600">{completedFields} / {totalFields} required fields</span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-6">
        {formSchema.fields.map(field => renderField(field))}

        <div className="space-y-2 pt-4 border-t">
          <Label htmlFor="comments">Additional Comments</Label>
          <Textarea
            id="comments"
            value={comments}
            onChange={(e) => setComments(e.target.value)}
            disabled={readOnly}
            rows={4}
            placeholder="Add any additional observations or comments..."
          />
        </div>

        {!readOnly && (
          <div className="flex space-x-4 pt-4">
            <Button
              variant="outline"
              onClick={handleSaveDraft}
              className="flex-1"
            >
              <Save className="w-4 h-4 mr-2" />
              Save Draft
            </Button>
            <Button
              onClick={handleSubmit}
              className="flex-1 bg-gradient-to-r from-indigo-600 to-purple-600"
              disabled={progress < 100}
            >
              <Send className="w-4 h-4 mr-2" />
              Submit Audit
            </Button>
          </div>
        )}

        {readOnly && (
          <div className="pt-4">
            <Badge variant="secondary" className="text-sm">
              Audit Completed
            </Badge>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
