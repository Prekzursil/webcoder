from django.shortcuts import render, get_object_or_404
from badges.models import Badge
from django.utils.translation import gettext as _, gettext_lazy

def overview(request, extra_context={}):
    badges = Badge.objects.all().order_by('level', 'id')

    context = locals()
    context['title'] = _('Badges')
    context.update(extra_context)
    return render(request, "badges/badges.html", context)