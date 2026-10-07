import logging

import cloudinary
import markdown2
from cloudinary.exceptions import Error as CloudinaryError
from django.db import DatabaseError, transaction
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

        if image:
            cloudinary_config = cloudinary.config()
            if not all((
                cloudinary_config.cloud_name,
                cloudinary_config.api_key,
                cloudinary_config.api_secret,
            )):
                return render(request, "encyclopedia/newpage.html", {
                    "error": (
                        "Cloudinary is not configured on this deployment. Set "
                        "CLOUDINARY_URL or all three CLOUDINARY_CLOUD_NAME, "
                        "CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET variables."
                    ),
                    "title": title,
                    "content": content,
                })

        if not title:
            return render(request, "encyclopedia/newpage.html", {
                "error": "Title is required",
                "title": title,
                "content": content,
            })

        if len(title) > 100:
            return render(request, "encyclopedia/newpage.html", {
                "error": "Title must be 100 characters or fewer",
                "title": title,
                "content": content,
            })

        if Entry.objects.filter(title=title).exists():
            return render(request, "encyclopedia/newpage.html", {
                "error": "Title already exists",
                "title": title,
                "content": content,
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
        except CloudinaryError:
            logger.exception("Failed to save encyclopedia entry.")
            return render(request, "encyclopedia/newpage.html", {
                "error": (
                    "Cloudinary could not upload this image. Check the Vercel "
                    "Cloudinary variables and the deployment logs."
                ),
                "title": title,
                "content": content,
            })
        except DatabaseError:
            logger.exception("Failed to save encyclopedia entry in PostgreSQL.")
            return render(request, "encyclopedia/newpage.html", {
                "error": "The image upload succeeded, but PostgreSQL could not save the page.",
                "title": title,
                "content": content,
            })
        except Exception:
            logger.exception("Unexpected error while saving encyclopedia entry.")
            return render(request, "encyclopedia/newpage.html", {
                "error": "An unexpected error prevented the page from being saved. Check the deployment logs.",
                "title": title,
                "content": content,
            })

        return redirect("entry", title=entry.title)

    else:
        return render(request, "encyclopedia/newpage.html")
         