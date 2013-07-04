from django.conf.urls import patterns, include

urlpatterns = patterns("",
    ("^profile/", include("entree.host.urls")),
    ("^", include("entree.enauth.urls")),
)
