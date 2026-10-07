import markdown2
from django.shortcuts import redirect, render
from . import util
from .models import Entry

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
        title = request.POST.get("title")
        content = request.POST.get("content")
        image = request.FILES.get("image")

        if Entry.objects.filter(title=title).exists():
            return render(request, "encyclopedia/newpage.html", {
                "error": "Title already exists"
            })
        else:
            entry = Entry(
                title=title,
                content=content,
                image=image
            )
            entry.save()

            return redirect("entry", title=title)

    else:
        return render(request, "encyclopedia/newpage.html")
         