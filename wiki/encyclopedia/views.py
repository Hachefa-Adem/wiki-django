import logging

import markdown2
from django.db import transaction
from django.shortcuts import redirect, render

from . import util
from .models import Entry

logger = logging.getLogger(__name__)

def index(request):
    return render(request, "encyclopedia/index.html", {
        "entries": Entry.objects.all()
    })

def entry(request, title):
    entry = Entry.objects.get(title=title)

    content = markdown2.markdown(entry.content)

    return render(
        request,
        "encyclopedia/entry.html",
        {"content": content, "entry": entry}
    )
            
def search(request):
    query = request.GET.get("q")
    entries = util.list_entries()

    if query in entries:
        with open(f"entries/{query}.md", "r") as f:
            content = f.read()
        content = markdown2.markdown(content)
        return render(request, "encyclopedia/entry.html", {"content": content})

    matches = [entry for entry in entries if query.lower() in entry.lower()]
    return render(request, "encyclopedia/index.html", {"entries": matches})
        

def newpage(request):
    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        content = request.POST.get("content") or ""
        image = request.FILES.get("image")

        if not title:
            return render(request, "encyclopedia/newpage.html", {
                "error": "Title is required"
            })

        if len(title) > 100:
            return render(request, "encyclopedia/newpage.html", {
                "error": "Title must be 100 characters or fewer"
            })

        if Entry.objects.filter(title=title).exists():
            return render(request, "encyclopedia/newpage.html", {
                "error": "Title already exists"
            })

        try:
            with transaction.atomic():
                entry = Entry(
                    title=title,
                    content=content,
                    image=image or None,
                )
                entry.save()
                entry.refresh_from_db()
        except Exception:
            logger.exception("Failed to save encyclopedia entry.")
            return render(request, "encyclopedia/newpage.html", {
                "error": "The page could not be saved. Check the title and image, then try again."
            })

        return redirect("entry", title=entry.title)

    else:
        return render(request, "encyclopedia/newpage.html")
         