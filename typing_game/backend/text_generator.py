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
        
        self.expert_words = [
            'philosophical', 'mathematical', 'interpretation', 'configuration',
            'authentication', 'transformation', 'implementation', 'consciousness',
            'comprehensive', 'environmental', 'unprecedented', 'simultaneously',
            'acknowledgment', 'investigation', 'communication', 'representation',
            'significance', 'infrastructure', 'collaboration', 'extraordinary'
        ]
        
        self.grandmaster_words = [
            'characterization', 'multidimensional', 'counterintuitive', 'interdisciplinary',
            'telecommunications', 'indistinguishable', 'microarchitecture', 'cryptographically',
            'misunderstanding', 'responsibilities', 'industrialization', 'institutionalized',
            'compartmentalized', 'unconstitutionally', 'disproportionately', 'inappropriateness',
            'enthusiastically', 'interchangeability', 'underestimated', 'misrepresentation'
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
            
    def _generate_neural_text(self, prompt_context):
        """
        [DEEP LEARNING PLACEHOLDER]
        This is where you would integrate a Transformer model (e.g., GPT-2, BERT).
        
        Example Logic:
        1. Load model: model = GPT2LMHeadModel.from_pretrained('gpt2')
        2. Encode context: inputs = tokenizer.encode(prompt_context, return_tensors='pt')
        3. Generate: outputs = model.generate(inputs, max_length=50, do_sample=True)
        4. Return decoded text
        """
        # For now, return a placeholder string
        return "The neural network is dreaming of electric sheep."
    
    def _generate_foundational(self, length_words, focus_areas):
        """Mode 1: Mechanics and repetition (Phonetic Drills)"""
        # Extract problematic keys
        target_keys = []
        for area in focus_areas:
            if area['type'] == 'high_error_keys':
                target_keys.extend(area['items'])
        
        # Ensure we have a base set if targets are sparse
        if not target_keys:
            target_keys = ['a', 's', 'd', 'f', 'j', 'k', 'l']
            
        # Create a pool that includes vowels to ensure pronounceability
        pool = set(target_keys)
        
        # If the pool lacks vowels, add basic ones to allow word formation
        if not any(k in 'aeiou' for k in pool):
            pool.update(['a', 'e'])
            
        # If the pool is too small, add common consonants
        if len(pool) < 4:
            pool.update(['t', 'n', 'r'])
            
        pool_list = list(pool)
        vowels = [k for k in pool_list if k in 'aeiou']
        consonants = [k for k in pool_list if k not in 'aeiou']
        
        # Fallbacks just in case
        if not vowels: vowels = ['a', 'e']
        if not consonants: consonants = ['t', 'n']

        # Generate pronounceable pseudo-words (Keybr style)
        words = []
        for _ in range(length_words):
            # Randomly choose a structure: CVC, CV, VC, CVCV, etc.
            structure = random.choice(['cvc', 'cv', 'vc', 'cvcv', 'vcc', 'cvcc'])
            word = ''
            for char_type in structure:
                if char_type == 'c':
                    word += random.choice(consonants)
                else:
                    word += random.choice(vowels)
            words.append(word)
            
        return ' '.join(words)
    
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
            
        return ' '.join(words)

    def _generate_performance(self, length_words, focus_areas, mastered_items):
        """Mode 3: Performance (Precision at Speed)"""
        components = []
        
        # Determine difficulty tier based on length (which comes from WPM)
        is_grandmaster = length_words > 80
        is_expert = length_words > 40
        
        # Select word banks and templates based on tier
        if is_grandmaster:
            complex_words = self.grandmaster_words
            sentence_templates = [
                "The {complex} {noun} {verb} {adv} despite the {complex} {noun}",
                "Understanding {complex} requires {adj} {noun} and {complex} {noun}",
                "The {noun} {verb} {adv} because of the {complex} {noun}",
                "Although {complex} is {adj} the {noun} {verb} {complex}",
                "The {complex} {noun} and {complex} {noun} {verb} {adv}",
                "It was {complex} that the {noun} {verb} the {complex} {noun}",
                "The {adj} {noun} demonstrated {complex} during the {complex} {noun}"
            ]
        elif is_expert:
            complex_words = self.expert_words
            sentence_templates = [
                "The {adj} {noun} {verb} {adv} through the {place}",
                "The {complex} {noun} {verb} the {adj} {noun}",
                "Because of {complex} the {noun} {verb} {adv}",
                "{Name} {verb} the {complex} {noun} from the {place}",
                "The {adj} {noun} is {complex} and {adj}",
                "While {name} {verb} the {noun} the {complex} {noun} {verb} {adv}"
            ]
        else:
            complex_words = self.hard_words
            sentence_templates = [
                "The {adj} {noun} {verb} {adv} through the {place}",
                "{Name} quickly {verb} the {adj} {noun} from the {place}",
                "Although the {noun} was {adj} it {verb} {adv}",
                "When {name} {verb} the {noun} everything {verb} {adj}",
                "{Number} {adj} {noun} {verb} {adv} toward the {place}",
                "The {adj} {noun} and the {adj} {noun} {verb} {adv} together"
            ]
        
        # Word banks
        adjectives = ['quick', 'brown', 'lazy', 'bright', 'dark', 'clever', 'simple', 'rapid', 'silent', 'efficient']
        nouns = ['fox', 'dog', 'cat', 'horse', 'bird', 'program', 'system', 'algorithm', 'network', 'interface']
        verbs = ['jumps', 'runs', 'flies', 'types', 'codes', 'thinks', 'learns', 'processes', 'computes', 'analyzes']
        adverbs = ['quickly', 'slowly', 'carefully', 'eagerly', 'quietly', 'efficiently', 'precisely', 'instantly']
        places = ['forest', 'house', 'garden', 'office', 'library', 'server', 'database', 'mainframe']
        names = ['Alex', 'Taylor', 'Jordan', 'Casey', 'Morgan', 'Sam', 'Riley']
        
        words_used = 0
        
        while words_used < length_words:
            template = random.choice(sentence_templates)
            
            # Helper to get a complex word
            def get_complex():
                return random.choice(complex_words)

            sentence = template.format(
                adj=random.choice(adjectives),
                noun=random.choice(nouns),
                verb=random.choice(verbs),
                adv=random.choice(adverbs),
                place=random.choice(places),
                name=random.choice(names),
                Name=random.choice(names),
                Number=random.randint(2, 10),
                complex=get_complex()
            )
            
            # Inject focus patterns if any
            if focus_areas:
                sentence = self._inject_focus_patterns(sentence, focus_areas)
            
            # Remove mastered patterns if any
            if mastered_items:
                sentence = self._reduce_mastered_patterns(sentence, mastered_items)
            
            components.append(sentence)
            words_used += len(sentence.split())
        
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