---
layout: post
title: "Publications"
permalink: /publications/
---
Some Content 10.10.2022 v9
<section class="list">

{% for post in site.posts %}
  {% if post.category == 'publication' %}
    {% if post.hidden != true %}
      {% include blog-post.html %}
    {% endif %}
  {% endif %}
{% endfor %}

<section>