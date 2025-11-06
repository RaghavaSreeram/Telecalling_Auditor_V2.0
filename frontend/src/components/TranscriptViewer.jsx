import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Input } from "./ui/input";
import { 
  MessageSquare, 
  User, 
  Clock, 
  Search, 
  Flag,
  CheckCircle,
  AlertCircle,
  StickyNote
} from "lucide-react";

export default function TranscriptViewer({ 
  transcript = [], 
  onHighlight, 
  highlights = [],
  readOnly = false 
}) {
  const [selectedSegment, setSelectedSegment] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [noteText, setNoteText] = useState("");
  const [flagType, setFlagType] = useState("neutral");
  const [activeHighlights, setActiveHighlights] = useState(highlights);
  const transcriptRef = useRef(null);

  useEffect(() => {
    setActiveHighlights(highlights);
  }, [highlights]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSegmentClick = (segment, index) => {
    if (readOnly) return;
    setSelectedSegment({ ...segment, index });
  };

  const handleAddHighlight = () => {
    if (!selectedSegment) return;

    const newHighlight = {
      id: `hl-${Date.now()}`,
      segment_index: selectedSegment.index,
      text: selectedSegment.text,
      note: noteText,
      flag_type: flagType,
      created_at: new Date().toISOString()
    };

    const updated = [...activeHighlights, newHighlight];
    setActiveHighlights(updated);
    
    if (onHighlight) {
      onHighlight(updated);
    }

    // Reset
    setNoteText("");
    setSelectedSegment(null);
  };

  const removeHighlight = (highlightId) => {
    const updated = activeHighlights.filter(h => h.id !== highlightId);
    setActiveHighlights(updated);
    if (onHighlight) {
      onHighlight(updated);
    }
  };

  const getHighlightForSegment = (index) => {
    return activeHighlights.find(h => h.segment_index === index);
  };

  const filteredTranscript = transcript.filter(segment => {
    if (!searchQuery) return true;
    return segment.text.toLowerCase().includes(searchQuery.toLowerCase());
  });

  const getFlagColor = (type) => {
    switch (type) {
      case "positive": return "bg-green-100 border-green-300";
      case "negative": return "bg-red-100 border-red-300";
      default: return "bg-yellow-100 border-yellow-300";
    }
  };

  const getFlagIcon = (type) => {
    switch (type) {
      case "positive": return <CheckCircle className="w-4 h-4 text-green-600" />;
      case "negative": return <AlertCircle className="w-4 h-4 text-red-600" />;
      default: return <Flag className="w-4 h-4 text-yellow-600" />;
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Transcript Display */}
      <div className="lg:col-span-2">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center">
                <MessageSquare className="w-5 h-5 mr-2" />
                Call Transcript
              </CardTitle>
              <Badge>{transcript.length} segments</Badge>
            </div>
            <div className="mt-4">
              <div className="relative">
                <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="Search transcript..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div ref={transcriptRef} className="space-y-3 max-h-[600px] overflow-y-auto">
              {filteredTranscript.map((segment, index) => {
                const highlight = getHighlightForSegment(index);
                const isSelected = selectedSegment?.index === index;

                return (
                  <div
                    key={index}
                    onClick={() => handleSegmentClick(segment, index)}
                    className={`p-4 rounded-lg border-2 transition-all cursor-pointer ${
                      isSelected ? 'border-indigo-500 bg-indigo-50' :
                      highlight ? getFlagColor(highlight.flag_type) :
                      'border-gray-200 hover:border-gray-300 bg-white'
                    }`}
                  >
                    <div className="flex items-start space-x-3">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                        segment.speaker === 'agent' ? 'bg-blue-100' : 'bg-gray-100'
                      }`}>
                        <User className={`w-5 h-5 ${
                          segment.speaker === 'agent' ? 'text-blue-600' : 'text-gray-600'
                        }`} />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1">
                          <Badge variant={segment.speaker === 'agent' ? 'default' : 'secondary'}>
                            {segment.speaker.toUpperCase()}
                          </Badge>
                          <span className="text-xs text-gray-500 flex items-center">
                            <Clock className="w-3 h-3 mr-1" />
                            {formatTime(segment.start_time)}
                          </span>
                          {segment.confidence && (
                            <span className="text-xs text-gray-500">
                              {Math.round(segment.confidence * 100)}% confidence
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-800">{segment.text}</p>
                        {highlight && (
                          <div className="mt-2 p-2 bg-white rounded border flex items-start justify-between">
                            <div className="flex items-start space-x-2 flex-1">
                              {getFlagIcon(highlight.flag_type)}
                              <span className="text-xs text-gray-700">{highlight.note}</span>
                            </div>
                            {!readOnly && (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  removeHighlight(highlight.id);
                                }}
                                className="h-6 px-2"
                              >
                                Remove
                              </Button>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Highlight Panel */}
      <div>
        <Card className="sticky top-4">
          <CardHeader>
            <CardTitle className="flex items-center">
              <StickyNote className="w-5 h-5 mr-2" />
              Add Note & Flag
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {selectedSegment ? (
              <>
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-600 mb-1">Selected segment:</p>
                  <p className="text-sm font-medium">{selectedSegment.text.substring(0, 60)}...</p>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Flag Type</label>
                  <div className="flex space-x-2">
                    <Button
                      size="sm"
                      variant={flagType === "positive" ? "default" : "outline"}
                      onClick={() => setFlagType("positive")}
                      className={flagType === "positive" ? "bg-green-600" : ""}
                    >
                      <CheckCircle className="w-4 h-4 mr-1" />
                      Positive
                    </Button>
                    <Button
                      size="sm"
                      variant={flagType === "negative" ? "default" : "outline"}
                      onClick={() => setFlagType("negative")}
                      className={flagType === "negative" ? "bg-red-600" : ""}
                    >
                      <AlertCircle className="w-4 h-4 mr-1" />
                      Negative
                    </Button>
                    <Button
                      size="sm"
                      variant={flagType === "neutral" ? "default" : "outline"}
                      onClick={() => setFlagType("neutral")}
                      className={flagType === "neutral" ? "bg-yellow-600" : ""}
                    >
                      <Flag className="w-4 h-4 mr-1" />
                      Neutral
                    </Button>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Note</label>
                  <Textarea
                    placeholder="Add your observation or comment..."
                    value={noteText}
                    onChange={(e) => setNoteText(e.target.value)}
                    rows={4}
                  />
                </div>

                <Button 
                  onClick={handleAddHighlight} 
                  className="w-full"
                  disabled={!noteText.trim()}
                >
                  Add Highlight
                </Button>
              </>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <StickyNote className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                <p className="text-sm">Click on any segment to add a note or flag</p>
              </div>
            )}

            {activeHighlights.length > 0 && (
              <div className="mt-6">
                <h4 className="text-sm font-semibold mb-2">Your Highlights ({activeHighlights.length})</h4>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {activeHighlights.map(h => (
                    <div key={h.id} className={`p-2 rounded border text-xs ${getFlagColor(h.flag_type)}`}>
                      <div className="flex items-start justify-between">
                        <span className="flex-1">{h.note}</span>
                        {getFlagIcon(h.flag_type)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
