---
layout: blog
---

<div style="text-align: left">
  Welcome to the blog! Here are the latest posts:
  <ul>
    {% for post in site.posts %}
      <li>
        <a href="{{ post.url }}">{{ post.title }}</a>
      </li>
    {% endfor %}
  </ul>
</div>
