import random
import string
from collections import defaultdict
import re

class AdaptiveTextGenerator:
    def __init__(self, word_list_path=None):
        # Common words for different difficulty levels
        self.easy_words = [
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
            'was', 'how', 'its', 'our', 'who', 'get', 'day', 'out', 'use', 'she'
        ]
        
        self.medium_words = [
            'which', 'there', 'their', 'about', 'would', 'these', 'other', 'words',
            'could', 'write', 'first', 'water', 'after', 'where', 'right', 'think',
            'years', 'thing', 'looks', 'never', 'under', 'might', 'while', 'house'
        ]
        
        self.hard_words = [
            'through', 'thought', 'against', 'between', 'another', 'because',
            'country', 'example', 'however', 'important', 'language', 'national',
            'possible', 'program', 'question', 'remember', 'sentence', 'together'
        ]
        
        # Special focus patterns
        self.vowel_combinations = ['ae', 'ai', 'ao', 'au', 'ea', 'ei', 'eo', 'eu', 
                                  'ia', 'ie', 'io', 'iu', 'oa', 'oe', 'oi', 'ou', 
                                  'ua', 'ue', 'ui', 'uo']
        self.consonant_clusters = ['str', 'thr', 'spr', 'scr', 'spl', 'shr', 
                                  'cht', 'nth', 'rth', 'lth']
        
        # Initialize with basic patterns
        self.focus_patterns = []
        self.mastered_patterns = []
    
    def generate_text(self, mode='controlled', length_words=10, focus_areas=None, mastered_items=None):
        """Generate adaptive text based on training mode"""
        
        if focus_areas is None:
            focus_areas = []
        if mastered_items is None:
            mastered_items = []
        
        # Dispatch to specific mode generator
        if mode == 'foundational':
            return self._generate_foundational(length_words, focus_areas)
        elif mode == 'performance':
            return self._generate_performance(length_words, focus_areas, mastered_items)
        else:
            # Default to controlled language
            return self._generate_controlled(length_words, focus_areas)
    
    def _generate_foundational(self, length_words, focus_areas):
        """Mode 1: Mechanics and repetition (Drills)"""
        # Extract problematic keys
        target_keys = []
        for area in focus_areas:
            if area['type'] == 'high_error_keys':
                target_keys.extend(area['items'])
        
        # If no specific targets, use common home row/easy keys
        if not target_keys:
            target_keys = ['a', 's', 'd', 'f', 'j', 'k', 'l', ';']
            
        # Generate drill patterns (e.g., "f f f j j j fj fj")
        chunks = []
        for _ in range(length_words):
            key = random.choice(target_keys)
            # 50% chance of single key repetition, 50% chance of alternating
            if random.random() < 0.5:
                chunk = f"{key}{key}{key}"
            else:
                other = random.choice(target_keys)
                chunk = f"{key}{other}{key}{other}"
            chunks.append(chunk)
            
        return ' '.join(chunks)
    
    def _generate_controlled(self, length_words, focus_areas):
        """Mode 2: Controlled Language (Rhythm and Flow)"""
        words = []
        
        # Include focus patterns if any
        focus_words = []
        for area in focus_areas:
            if area['type'] == 'high_error_keys':
                for key in area['items']:
                    # Create words containing the problematic key
                    for word in self.easy_words:
                        if key in word and len(word) <= 5:
                            focus_words.append(word)
        
        # Mix focus words with regular words
        for i in range(length_words):
            if focus_words and random.random() < 0.4:  # 40% focus words
                words.append(random.choice(focus_words))
            else:
                words.append(random.choice(self.easy_words))
            
            # Add simple punctuation occasionally
            if i > 0 and i % 5 == 0 and random.random() < 0.3:
                words[-1] += random.choice([',', '.'])
        
        return ' '.join(words)

    def _generate_performance(self, length_words, focus_areas, mastered_items):
        """Mode 3: Performance (Precision at Speed)"""
        components = []
        
        # Build sentence structures
        sentence_templates = [
            "The {adj} {noun} {verb} {adv} through the {place}.",
            "{Name} quickly {verb} the {adj} {noun} from the {place}.",
            "Although the {noun} was {adj}, it {verb} {adv}.",
            "When {name} {verb} the {noun}, everything {verb} {adj}.",
            "{Number} {adj} {noun} {verb} {adv} toward the {place}."
        ]
        
        # Word banks
        adjectives = ['quick', 'brown', 'lazy', 'bright', 'dark', 'clever', 'simple']
        nouns = ['fox', 'dog', 'cat', 'horse', 'bird', 'program', 'system']
        verbs = ['jumps', 'runs', 'flies', 'types', 'codes', 'thinks', 'learns']
        adverbs = ['quickly', 'slowly', 'carefully', 'eagerly', 'quietly']
        places = ['forest', 'house', 'garden', 'office', 'library']
        names = ['Alex', 'Taylor', 'Jordan', 'Casey', 'Morgan']
        
        # Generate 2-3 sentences
        num_sentences = random.randint(2, 3)
        words_used = 0
        
        for _ in range(num_sentences):
            if words_used >= length_words:
                break
                
            template = random.choice(sentence_templates)
            sentence = template.format(
                adj=random.choice(adjectives),
                noun=random.choice(nouns),
                verb=random.choice(verbs),
                adv=random.choice(adverbs),
                place=random.choice(places),
                name=random.choice(names),
                Name=random.choice(names),
                Number=random.randint(2, 10)
            )
            
            # Inject focus patterns if any
            if focus_areas:
                sentence = self._inject_focus_patterns(sentence, focus_areas)
            
            # Remove mastered patterns if any
            if mastered_items:
                sentence = self._reduce_mastered_patterns(sentence, mastered_items)
            
            components.append(sentence)
            words_used += len(sentence.split())
        
        # If we need more words, add additional phrases
        while words_used < length_words:
            additional = random.choice([
                "Meanwhile, ",
                "However, ",
                "Therefore, ",
                "In conclusion, ",
                "For example, "
            ]) + random.choice(self.hard_words) + "."
            components.append(additional)
            words_used += len(additional.split())
        
        return ' '.join(components)
    
    def _create_word_with_bigram(self, bigram):
        """Create or find a word containing the specified bigram"""
        # Check existing word lists
        all_words = self.easy_words + self.medium_words + self.hard_words
        matching_words = [w for w in all_words if bigram in w]
        
        if matching_words:
            return random.choice(matching_words)
        
        # Try to create a plausible word
        vowels = 'aeiou'
        consonants = 'bcdfghjklmnpqrstvwxyz'
        
        # Simple word creation around the bigram
        if len(bigram) == 2:
            if bigram[0] in consonants and bigram[1] in vowels:
                # CV pattern
                prefix = random.choice(consonants) if random.random() < 0.5 else ''
                suffix = random.choice(vowels + 's') if random.random() < 0.5 else ''
                return prefix + bigram + suffix
            elif bigram[0] in vowels and bigram[1] in consonants:
                # VC pattern
                prefix = random.choice(vowels) if random.random() < 0.5 else ''
                suffix = random.choice(consonants + 's') if random.random() < 0.5 else ''
                return prefix + bigram + suffix
        
        return None
    
    def _inject_focus_patterns(self, text, focus_areas):
        """Inject focus patterns into text"""
        words = text.split()
        
        for area in focus_areas:
            if area['type'] == 'high_error_keys' and random.random() < 0.7:
                # Replace some words with ones containing focus keys
                for key in area['items'][:2]:  # First 2 focus keys
                    for i in range(len(words)):
                        if random.random() < 0.3:
                            # Find a word containing this key
                            possible = [w for w in self.medium_words if key in w]
                            if possible:
                                words[i] = random.choice(possible)
        
        return ' '.join(words)
    
    def _reduce_mastered_patterns(self, text, mastered_items):
        """Reduce frequency of mastered patterns"""
        words = text.split()
        
        for item in mastered_items:
            if item['type'] == 'mastered_keys' and random.random() < 0.6:
                # Avoid overusing mastered keys
                for key in item['items'][:3]:  # First 3 mastered keys
                    for i in range(len(words)):
                        if key in words[i] and random.random() < 0.4:
                            # Replace with a word without this key
                            alternatives = [w for w in self.medium_words 
                                          if key not in w and len(w) <= len(words[i]) + 2]
                            if alternatives:
                                words[i] = random.choice(alternatives)
        
        return ' '.join(words)