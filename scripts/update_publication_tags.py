import os
import re
import yaml
from pathlib import Path

def extract_key_terms(abstract, num_terms=4):
    # Simple extraction of capitalized phrases and technical terms
    # This could be improved with NLP libraries like spacy or nltk
    terms = re.findall(r'([A-Z][a-zA-Z-]+(?: [A-Z][a-zA-Z-]+)*|\([A-Z]+\))', abstract)
    # Remove duplicates and limit to num_terms
    unique_terms = list(dict.fromkeys(terms))[:num_terms]
    return unique_terms

def update_publication_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Split front matter and content
    parts = content.split('---\n', 2)
    if len(parts) < 3:
        print(f"Skipping {filepath}: No valid front matter found")
        return

    # Parse front matter
    front_matter = yaml.safe_load(parts[1])
    
    # Extract abstract
    abstract_match = re.search(r'## Abstract\n(.*?)(?=\n\n|$)', parts[2], re.DOTALL)
    if abstract_match:
        abstract = abstract_match.group(1)
        key_terms = extract_key_terms(abstract)
        
        # Update front matter tags
        front_matter['tag'] = key_terms
        
        # Reconstruct the file
        new_content = "---\n"
        new_content += yaml.dump(front_matter, allow_unicode=True)
        new_content += "---\n"
        new_content += parts[2]
        
        # Write back to file
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"Updated {filepath} with tags: {key_terms}")

def main():
    publications_dir = Path('/Users/virtualmario/Documents/Repos/indigo_alrr/_publications')
    for file in publications_dir.glob('*.md'):
        update_publication_file(file)

if __name__ == "__main__":
    main()
