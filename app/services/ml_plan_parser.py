from typing import Dict, List, Optional
import re
from datetime import datetime, timedelta
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import spacy
from app.config import settings

class MLPlanParser:
    def __init__(self):
        # Load spaCy model for NLP
        self.nlp = spacy.load("en_core_web_sm")
        
        # Initialize TF-IDF vectorizer for text similarity
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=1000
        )
        
        # Common workout patterns and their features
        self.workout_patterns = {
            'easy_run': {
                'keywords': ['easy', 'recovery', 'steady', 'conversational'],
                'distance_range': (3, 10),  # km
                'intensity': 'low'
            },
            'intervals': {
                'keywords': ['intervals', 'repeats', 'sprints', 'fartlek'],
                'distance_range': (0.2, 2),  # km per interval
                'intensity': 'high'
            },
            'long_run': {
                'keywords': ['long', 'endurance', 'distance'],
                'distance_range': (10, 30),  # km
                'intensity': 'moderate'
            }
        }
        
        # Initialize the vectorizer with common workout descriptions
        self._initialize_vectorizer()

    def _initialize_vectorizer(self):
        """Initialize the TF-IDF vectorizer with common workout patterns."""
        sample_texts = []
        for pattern in self.workout_patterns.values():
            sample_texts.extend(pattern['keywords'])
        self.vectorizer.fit(sample_texts)

    def parse_plan(self, plan_text: str) -> Dict:
        """Parse a training plan using ML-based approach."""
        # Split the plan into weeks
        weeks = self._split_into_weeks(plan_text)
        
        structured_plan = {
            "plan_title": self._extract_plan_title(plan_text),
            "start_date": datetime.now().isoformat(),
            "duration_weeks": len(weeks),
            "weekly_structure": [],
            "workouts": []
        }
        
        for week_num, week_text in enumerate(weeks, 1):
            week_data = self._parse_week(week_text, week_num)
            structured_plan["weekly_structure"].append(week_data)
            structured_plan["workouts"].extend(week_data["workouts"])
        
        return structured_plan

    def _split_into_weeks(self, plan_text: str) -> List[str]:
        """Split the plan text into individual weeks."""
        week_pattern = r'📊\s*Week\s*\d+.*?(?=📊\s*Week|\Z)'
        weeks = re.findall(week_pattern, plan_text, re.DOTALL)
        return weeks

    def _extract_plan_title(self, plan_text: str) -> str:
        """Extract the plan title using NLP."""
        doc = self.nlp(plan_text)
        # Look for the first sentence or line that doesn't contain week information
        for sent in doc.sents:
            if not re.search(r'Week\s*\d+', sent.text):
                return sent.text.strip()
        return "Training Plan"

    def _parse_week(self, week_text: str, week_num: int) -> Dict:
        """Parse a single week of the training plan."""
        # Extract total distance and other metrics
        total_distance = self._extract_total_distance(week_text)
        
        # Split into individual workouts
        workout_texts = self._split_into_workouts(week_text)
        
        workouts = []
        for workout_text in workout_texts:
            workout = self._parse_workout(workout_text)
            if workout:
                workouts.append(workout)
        
        return {
            "week_number": week_num,
            "total_distance": total_distance,
            "workouts": workouts
        }

    def _extract_total_distance(self, week_text: str) -> float:
        """Extract the total distance for the week."""
        distance_match = re.search(r'Total Distance\s*(\d+(?:\.\d+)?)\s*km', week_text)
        if distance_match:
            return float(distance_match.group(1))
        return 0.0

    def _split_into_workouts(self, week_text: str) -> List[str]:
        """Split the week text into individual workouts."""
        # Look for workout sections starting with day names
        workout_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday).*?(?=(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)|\Z)'
        workouts = re.findall(workout_pattern, week_text, re.DOTALL)
        return workouts

    def _parse_workout(self, workout_text: str) -> Optional[Dict]:
        """Parse a single workout using ML-based approach."""
        # Extract basic information
        day_match = re.search(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', workout_text)
        if not day_match:
            return None
        
        # Use NLP to understand the workout type and description
        doc = self.nlp(workout_text)
        
        # Determine workout type using ML
        workout_type = self._classify_workout_type(workout_text)
        
        # Extract distance using ML-enhanced pattern matching
        distance = self._extract_distance(workout_text, workout_type)
        
        # Extract description
        description = self._extract_description(workout_text)
        
        return {
            "day": day_match.group(1),
            "workout_type": workout_type,
            "description": description,
            "distance": str(distance) if distance else None
        }

    def _classify_workout_type(self, workout_text: str) -> str:
        """Classify the workout type using ML."""
        # Transform the workout text
        text_vector = self.vectorizer.transform([workout_text])
        
        # Compare with known patterns
        max_similarity = 0
        best_type = "Easy Run"  # default
        
        for workout_type, pattern in self.workout_patterns.items():
            pattern_vector = self.vectorizer.transform([' '.join(pattern['keywords'])])
            similarity = cosine_similarity(text_vector, pattern_vector)[0][0]
            
            if similarity > max_similarity:
                max_similarity = similarity
                best_type = workout_type.replace('_', ' ').title()
        
        return best_type

    def _extract_distance(self, workout_text: str, workout_type: str) -> Optional[float]:
        """Extract distance using ML-enhanced pattern matching."""
        # Look for distance patterns
        distance_patterns = [
            r'(\d+(?:\.\d+)?)\s*miles?',
            r'(\d+(?:\.\d+)?)\s*km',
            r'(\d+(?:\.\d+)?)\s*m'
        ]
        
        for pattern in distance_patterns:
            match = re.search(pattern, workout_text, re.IGNORECASE)
            if match:
                distance = float(match.group(1))
                # Convert to kilometers if needed
                if 'miles' in pattern:
                    distance *= 1.60934
                elif 'm' in pattern and not 'km' in pattern:
                    distance /= 1000
                return round(distance, 2)
        
        # If no distance found, use ML to estimate based on workout type
        if workout_type in self.workout_patterns:
            pattern = self.workout_patterns[workout_type.lower().replace(' ', '_')]
            return np.mean(pattern['distance_range'])
        
        return None

    def _extract_description(self, workout_text: str) -> str:
        """Extract the workout description using NLP."""
        # Remove the day and workout type
        description = re.sub(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday).*?\n', '', workout_text)
        description = re.sub(r'^(🏃|⚡|🏃‍♂️)\s*.*?\n', '', description)
        
        # Clean up the description
        description = description.strip()
        return description

    def verify_parsed_plan(self, parsed_plan: Dict) -> Dict:
        """Verify the correctness of the parsed plan using ML-based approach."""
        verification = {
            "is_valid": True,
            "confidence_score": 0.0,
            "issues": []
        }
        
        # Check basic structure
        if not parsed_plan.get("weekly_structure"):
            verification["is_valid"] = False
            verification["issues"].append("Missing weekly structure")
            return verification
        
        # Calculate confidence score
        confidence_scores = []
        
        for week_data in parsed_plan.get("weekly_structure", []):
            # Verify week structure
            if not week_data.get("workouts"):
                verification["issues"].append(f"Week {week_data.get('week_number')} has no workouts")
                continue
            
            # Verify workout consistency
            for workout in week_data.get("workouts", []):
                # Check required fields
                if not all(workout.get(field) for field in ["day", "workout_type", "description"]):
                    verification["issues"].append(f"Missing required fields in {workout.get('day')} workout")
                    continue
                
                # Calculate confidence for this workout
                workout_confidence = self._calculate_workout_confidence(workout)
                confidence_scores.append(workout_confidence)
        
        # Calculate overall confidence score
        if confidence_scores:
            verification["confidence_score"] = np.mean(confidence_scores)
            verification["is_valid"] = verification["confidence_score"] > 0.7
        
        return verification

    def _calculate_workout_confidence(self, workout: Dict) -> float:
        """Calculate confidence score for a single workout."""
        confidence_scores = []
        
        # Check workout type consistency
        workout_type = workout.get("workout_type", "").lower()
        description = workout.get("description", "").lower()
        
        # Compare with known patterns
        for pattern_type, pattern in self.workout_patterns.items():
            if pattern_type.replace('_', ' ') in workout_type:
                # Check if description contains expected keywords
                keyword_matches = sum(1 for kw in pattern['keywords'] if kw in description)
                confidence_scores.append(keyword_matches / len(pattern['keywords']))
        
        # Check distance consistency
        if workout.get("distance"):
            try:
                distance = float(workout["distance"])
                if workout_type in self.workout_patterns:
                    pattern = self.workout_patterns[workout_type.lower().replace(' ', '_')]
                    if pattern['distance_range'][0] <= distance <= pattern['distance_range'][1]:
                        confidence_scores.append(1.0)
                    else:
                        confidence_scores.append(0.5)
            except ValueError:
                confidence_scores.append(0.0)
        
        return np.mean(confidence_scores) if confidence_scores else 0.0 