"""
Transcript Service
Handles transcript fetching, parsing, and mock data generation
"""
import json
import random
from typing import List, Dict, Any
from models import TranscriptSegment


class TranscriptService:
    """Service for managing call transcripts"""
    
    @staticmethod
    async def fetch_transcript(call_reference_id: str, transcript_url: str = None) -> List[TranscriptSegment]:
        """
        Fetch transcript from external source or generate mock data
        In production, this would call AWS S3, CRM API, etc.
        """
        # For now, return mock transcript data
        return TranscriptService.generate_mock_transcript()
    
    @staticmethod
    def generate_mock_transcript() -> List[TranscriptSegment]:
        """Generate realistic mock transcript for demo purposes"""
        conversations = [
            # Real estate cold call example
            [
                TranscriptSegment(speaker="agent", text="Good morning! This is Priya from Radiance Realty. Am I speaking with Mr. Sharma?", start_time=0.0, end_time=4.5, confidence=0.95),
                TranscriptSegment(speaker="customer", text="Yes, this is Sharma speaking.", start_time=4.8, end_time=6.2, confidence=0.98),
                TranscriptSegment(speaker="agent", text="Great! I'm calling regarding our premium property development in Whitefield, Bangalore. Are you currently looking for a property investment opportunity?", start_time=6.5, end_time=14.2, confidence=0.92),
                TranscriptSegment(speaker="customer", text="Well, I have been thinking about it. What are you offering?", start_time=14.5, end_time=18.0, confidence=0.96),
                TranscriptSegment(speaker="agent", text="Excellent! We have exclusive 2 and 3 BHK apartments with world-class amenities including a swimming pool, gym, clubhouse, and 24/7 security. The location is very prime with easy access to IT parks and schools.", start_time=18.3, end_time=32.8, confidence=0.94),
                TranscriptSegment(speaker="customer", text="That sounds interesting. What's the price range?", start_time=33.1, end_time=36.0, confidence=0.97),
                TranscriptSegment(speaker="agent", text="The starting price for 2 BHK is 85 lakhs with easy EMI options available. We also have some early bird discounts running this month. May I know your budget range?", start_time=36.3, end_time=48.2, confidence=0.93),
                TranscriptSegment(speaker="customer", text="Around 80 to 90 lakhs would work for me.", start_time=48.5, end_time=51.5, confidence=0.95),
                TranscriptSegment(speaker="agent", text="Perfect! That's exactly in our range. Are you looking for self-use or investment?", start_time=51.8, end_time=56.5, confidence=0.96),
                TranscriptSegment(speaker="customer", text="Self-use. I work in the IT sector.", start_time=56.8, end_time=59.5, confidence=0.98),
                TranscriptSegment(speaker="agent", text="Wonderful! When are you planning to make the purchase decision?", start_time=59.8, end_time=63.5, confidence=0.94),
                TranscriptSegment(speaker="customer", text="Within the next 3 to 4 months.", start_time=63.8, end_time=66.0, confidence=0.96),
                TranscriptSegment(speaker="agent", text="Great timing! Our project has RERA approval and possession is scheduled for 2026. Would you like to visit our sample flat this Saturday? We can arrange a free cab pickup from your location.", start_time=66.3, end_time=80.5, confidence=0.92),
                TranscriptSegment(speaker="customer", text="Yes, Saturday works for me.", start_time=80.8, end_time=83.0, confidence=0.97),
                TranscriptSegment(speaker="agent", text="Excellent! Can I have your email to send you the details and brochure?", start_time=83.3, end_time=88.0, confidence=0.95),
                TranscriptSegment(speaker="customer", text="Sure, it's sharma.raj@email.com", start_time=88.3, end_time=91.5, confidence=0.93),
                TranscriptSegment(speaker="agent", text="Perfect! You'll receive all the details within 30 minutes. Thank you for your time, Mr. Sharma. Looking forward to seeing you on Saturday!", start_time=91.8, end_time=102.0, confidence=0.94),
                TranscriptSegment(speaker="customer", text="Thank you, bye.", start_time=102.3, end_time=103.5, confidence=0.98),
            ],
            # Follow-up call example
            [
                TranscriptSegment(speaker="agent", text="Hello! This is Amit from Radiance Realty. Am I speaking with Mrs. Patel?", start_time=0.0, end_time=5.0, confidence=0.96),
                TranscriptSegment(speaker="customer", text="Yes, speaking.", start_time=5.3, end_time=6.5, confidence=0.98),
                TranscriptSegment(speaker="agent", text="I'm calling to follow up on your site visit last week. How did you like the property?", start_time=6.8, end_time=12.0, confidence=0.94),
                TranscriptSegment(speaker="customer", text="It was nice, but I'm still thinking about it.", start_time=12.3, end_time=15.5, confidence=0.95),
                TranscriptSegment(speaker="agent", text="I understand. Do you have any specific concerns I can help address?", start_time=15.8, end_time=20.5, confidence=0.93),
                TranscriptSegment(speaker="customer", text="Well, the price is a bit higher than my budget.", start_time=20.8, end_time=24.0, confidence=0.96),
                TranscriptSegment(speaker="agent", text="I completely understand. Let me check if we have any flexible payment plans or special offers that could work for your budget. What's your comfortable range?", start_time=24.3, end_time=35.0, confidence=0.92),
                TranscriptSegment(speaker="customer", text="I was thinking around 75 lakhs maximum.", start_time=35.3, end_time=38.5, confidence=0.94),
                TranscriptSegment(speaker="agent", text="Let me speak with my manager and see what we can arrange. Can I call you back tomorrow with some options?", start_time=38.8, end_time=46.0, confidence=0.95),
                TranscriptSegment(speaker="customer", text="Yes, that would be helpful.", start_time=46.3, end_time=48.5, confidence=0.97),
                TranscriptSegment(speaker="agent", text="Great! I'll call you tomorrow afternoon. Thank you for your time, Mrs. Patel.", start_time=48.8, end_time=54.0, confidence=0.96),
                TranscriptSegment(speaker="customer", text="Thank you, bye.", start_time=54.3, end_time=55.5, confidence=0.98),
            ]
        ]
        
        # Return random conversation
        return random.choice(conversations)
    
    @staticmethod
    def format_transcript_for_display(segments: List[TranscriptSegment]) -> str:
        """Format transcript segments for text display"""
        formatted = []
        for segment in segments:
            time_str = TranscriptService.format_timestamp(segment.start_time)
            speaker_label = segment.speaker.upper()
            formatted.append(f"[{time_str}] {speaker_label}: {segment.text}")
        return "\n".join(formatted)
    
    @staticmethod
    def format_timestamp(seconds: float) -> str:
        """Format seconds to MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    @staticmethod
    def parse_transcript_json(json_data: str) -> List[TranscriptSegment]:
        """Parse transcript from JSON format"""
        try:
            data = json.loads(json_data)
            segments = []
            for item in data.get("segments", []):
                segments.append(TranscriptSegment(**item))
            return segments
        except Exception as e:
            raise ValueError(f"Failed to parse transcript JSON: {str(e)}")
    
    @staticmethod
    def search_transcript(segments: List[TranscriptSegment], query: str) -> List[int]:
        """Search for keywords in transcript, return segment indices"""
        query_lower = query.lower()
        matching_indices = []
        
        for i, segment in enumerate(segments):
            if query_lower in segment.text.lower():
                matching_indices.append(i)
        
        return matching_indices
