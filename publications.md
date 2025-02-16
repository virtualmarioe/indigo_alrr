---
layout: page
title: "Publications"
permalink: /publications/
---

<section class="list">
    {% assign sorted_pubs = site.publications | sort: "date" | reverse %}
    {% for pub in sorted_pubs %}
        {% include pub-post.html item=pub %}
    {% endfor %}
</section>