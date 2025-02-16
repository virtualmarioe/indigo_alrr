import os
import re
from scholarly import scholarly

# Replace with your Google Scholar user ID.
author_id = 'L2v2k5QAAAAJ'
# Fetch the author profile.
author = scholarly.search_author_id(author_id)
author = scholarly.fill(author, sections=['publications'])

# Ensure the _publications folder exists.
output_dir = "_publications"
os.makedirs(output_dir, exist_ok=True)

def slugify(title):
    # Create a simple slug from the title.
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
    return slug

for pub in author.get('publications', []):
    # Fill in details for each publication.
    publication = scholarly.fill(pub)
    bib = publication.get('bib', {})
    title = bib.get('title', 'Untitled Publication')
    # Use the publication year if available; otherwise, default to current year.
    year = bib.get('pub_year', '2022')
    # Create a slug for the filename.
    slug = slugify(title)
    filename = f"{year}-{slug}.md"
    filepath = os.path.join(output_dir, filename)
    
    # In this example we use a fixed time stamp.
    # You may want to improve the date by parsing more info if available.
    date_field = f"{year}-10-03 10:00"
    
    # The abstract might not always be available from Google Scholar.
    abstract = bib.get('abstract', 'No abstract available.')
    
    # Extract the Journal's name from the bib info.
    journal = bib.get('venue', 'No Journal Available')
    
    md_content = f"""---
title: "{title}"
layout: post
date: {date_field}
tag: 
- Research
- Attention
- MCI
image: /assets/images/NI2-Fig.jpeg
headerImage: true
projects: true
hidden: false
description: "{journal}"
category: publication
author: adrianaruiz
externalLink: false
---

## Abstract
{abstract}
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Created: {filepath}")
