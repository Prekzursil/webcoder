from django.contrib import admin
from django.forms import ModelForm, ModelMultipleChoiceField
from django.utils.translation import gettext_lazy as _
from django.db.models import Count

from judge.models import Problem, ProblemGroup
from judge.models.problem import ProblemGroupTranslation
from judge.widgets import AdminHeavySelect2MultipleWidget
from mptt.admin import DraggableMPTTAdmin


class ProblemGroupForm(ModelForm):

    def __init__(self,*args,**kwargs):
        super (ProblemGroupForm,self ).__init__(*args,**kwargs) # populates the post
        instance = getattr(self, 'instance', None)
        self.fields['parent'].queryset = ProblemGroup.objects.annotate(count=Count('problem')).filter(parent__isnull=True).exclude(count__gte=1).exclude(id=instance.id)
        if instance.children.all().count() > 0:
            self.fields['parent'].disabled = True
            self.fields['problems'].disabled = True

    problems = ModelMultipleChoiceField(
        label=_('Included problems'),
        queryset=Problem.objects.all(),
        required=False,
        help_text=_('These problems are included in this group of problems'),
        widget=AdminHeavySelect2MultipleWidget(data_view='problem_select2'))

class ProblemGroupTranslationInline(admin.StackedInline):
    model = ProblemGroupTranslation
    fields = ('language', 'full_name')
    extra = 0

class ProblemGroupAdmin(DraggableMPTTAdmin):
    list_display = DraggableMPTTAdmin.list_display + ('name',)
    fields = ('name', 'full_name', 'parent', 'problems')
    list_editable = ()  # Bug in SortableModelAdmin: 500 without list_editable being set
    mptt_level_indent = 20
    inlines = (ProblemGroupTranslationInline,)
    form = ProblemGroupForm
    sortable = 'order'

    def display_name(self, obj):
        if obj.parent:
            return obj.parent.full_name + ' > ' + obj.full_name
        else:
            return obj.full_name

    def is_parent(self, obj):
        if obj.parent:
            return False
        else:
            return True

    def save_model(self, request, obj, form, change):
        super(ProblemGroupAdmin, self).save_model(request, obj, form, change)
        obj.problem_set.set(form.cleaned_data['problems'])
        obj.save()

    def get_form(self, request, obj=None, **kwargs):
        self.form.base_fields['problems'].initial = [o.pk for o in obj.problem_set.all()] if obj else []
        return super(ProblemGroupAdmin, self).get_form(request, obj, **kwargs)


class ProblemTypeForm(ModelForm):
    problems = ModelMultipleChoiceField(
        label=_('Included problems'),
        queryset=Problem.objects.all(),
        required=False,
        help_text=_('These problems are included in this type of problems'),
        widget=AdminHeavySelect2MultipleWidget(data_view='problem_select2'))


class ProblemTypeAdmin(admin.ModelAdmin):
    fields = ('name', 'full_name', 'problems')
    form = ProblemTypeForm

    def save_model(self, request, obj, form, change):
        super(ProblemTypeAdmin, self).save_model(request, obj, form, change)
        obj.problem_set.set(form.cleaned_data['problems'])
        obj.save()

    def get_form(self, request, obj=None, **kwargs):
        self.form.base_fields['problems'].initial = [o.pk for o in obj.problem_set.all()] if obj else []
        return super(ProblemTypeAdmin, self).get_form(request, obj, **kwargs)
