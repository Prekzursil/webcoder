import json
import mimetypes
import os
import io
import tempfile
import zipfile
import shutil
from itertools import chain
from zipfile import BadZipfile, ZipFile

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.forms import BaseModelFormSet, HiddenInput, ModelForm, NumberInput, Select, formset_factory
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.views.generic import DetailView
from django import forms

from judge.highlight_code import highlight_code
from judge.models import Problem, ProblemData, ProblemTestCase, Submission, problem_data_storage
from judge.utils.problem_data import ProblemDataCompiler
from judge.utils.unicode import utf8text
from judge.utils.views import TitleMixin
from judge.views.problem import ProblemMixin

from django.conf import settings

mimetypes.init()
mimetypes.add_type('application/x-yaml', '.yml')

def remove_from_zip(zipfname, *filenames):
    tempdir = tempfile.mkdtemp()
    try:
        tempname = os.path.join(tempdir, 'new.zip')
        with zipfile.ZipFile(zipfname, 'r') as zipread:
            with zipfile.ZipFile(tempname, 'w') as zipwrite:
                for item in zipread.infolist():
                    if item.filename not in filenames:
                        data = zipread.read(item.filename)
                        zipwrite.writestr(item, data)
        shutil.move(tempname, zipfname)
    finally:
        shutil.rmtree(tempdir)

def checker_args_cleaner(self):
    data = self.cleaned_data['checker_args']
    if not data or data.isspace():
        return ''
    try:
        if not isinstance(json.loads(data), dict):
            raise ValidationError(_('Checker arguments must be a JSON object'))
    except ValueError:
        raise ValidationError(_('Checker arguments is invalid JSON'))
    return data


class ProblemDataForm(ModelForm):
    def clean_zipfile(self):
        if hasattr(self, 'zip_valid') and not self.zip_valid:
            raise ValidationError(_('Your zip file is invalid!'))
        return self.cleaned_data['zipfile']

    clean_checker_args = checker_args_cleaner

    class Meta:
        model = ProblemData
        fields = ['zipfile', 'generator', 'output_limit', 'output_prefix', 'checker', 'checker_args']
        widgets = {
            'checker_args': HiddenInput,
        }


class ProblemCaseForm(ModelForm):
    clean_checker_args = checker_args_cleaner

    class Meta:
        model = ProblemTestCase
        fields = ('order', 'type', 'input_file', 'output_file', 'input_text', 'output_text', 'points',
                  'is_pretest', 'is_example', 'output_limit', 'output_prefix', 'checker', 'checker_args', 'generator_args')
        widgets = {
            'generator_args': HiddenInput,
            'type': Select(attrs={'style': 'width: 100%'}),
            'points': NumberInput(attrs={'style': 'width: 4em'}),
            'input_text': forms.Textarea(attrs={'placeholder': _('Select a file above if you want to overwrite it or leave it blank to automatically name this test case.'), 'style': 'width: 100%'}),
            'output_text': forms.Textarea(attrs={'placeholder': _('Select a file above if you want to overwrite it or leave it blank to automatically name this test case.'), 'style': 'width: 100%'}),
            'output_prefix': NumberInput(attrs={'style': 'width: 4.5em'}),
            'output_limit': NumberInput(attrs={'style': 'width: 6em'}),
            'checker_args': HiddenInput,
        }


class ProblemCaseFormSet(formset_factory(ProblemCaseForm, formset=BaseModelFormSet, extra=1, max_num=1,
                                         can_delete=True)):
    model = ProblemTestCase

    def __init__(self, *args, **kwargs):
        self.valid_files = kwargs.pop('valid_files', None)
        super(ProblemCaseFormSet, self).__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        form = super(ProblemCaseFormSet, self)._construct_form(i, **kwargs)
        form.valid_files = self.valid_files
        return form

class ProblemManagerMixin(LoginRequiredMixin, ProblemMixin, DetailView):
    def get_object(self, queryset=None):
        problem = super(ProblemManagerMixin, self).get_object(queryset)
        if problem.is_manually_managed:
            raise Http404()
        if self.request.user.is_superuser or problem.is_editable_by(self.request.user):
            return problem
        raise Http404()


class ProblemSubmissionDiff(TitleMixin, ProblemMixin, DetailView):
    template_name = 'problem/submission-diff.html'

    def get_title(self):
        return _('Comparing submissions for {0}').format(self.object.name)

    def get_content_title(self):
        return format_html(_('Comparing submissions for <a href="{1}">{0}</a>'), self.object.name,
                           reverse('problem_detail', args=[self.object.code]))

    def get_object(self, queryset=None):
        problem = super(ProblemSubmissionDiff, self).get_object(queryset)
        if self.request.user.is_superuser or problem.is_editable_by(self.request.user):
            return problem
        raise Http404()

    def get_context_data(self, **kwargs):
        context = super(ProblemSubmissionDiff, self).get_context_data(**kwargs)
        try:
            ids = self.request.GET.getlist('id')
            subs = Submission.objects.filter(id__in=ids)
        except ValueError:
            raise Http404
        if not subs:
            raise Http404

        context['submissions'] = subs

        # If we have associated data we can do better than just guess
        data = ProblemTestCase.objects.filter(dataset=self.object, type='C')
        if data:
            num_cases = data.count()
        else:
            num_cases = subs.first().test_cases.count()
        context['num_cases'] = num_cases
        return context


class ProblemDataView(TitleMixin, ProblemManagerMixin):
    template_name = 'problem/data.html'

    def get_title(self):
        return _('Editing data for {0}').format(self.object.name)

    def get_content_title(self):
        return mark_safe(escape(_('Editing data for %s')) % (
            format_html('<a href="{1}">{0}</a>', self.object.name,
                        reverse('problem_detail', args=[self.object.code]))))

    def get_data_form(self, post=False):
        return ProblemDataForm(data=self.request.POST if post else None, prefix='problem-data',
                               files=self.request.FILES if post else None,
                               instance=ProblemData.objects.get_or_create(problem=self.object)[0])

    def get_case_formset(self, files, post=False):
        return ProblemCaseFormSet(data=self.request.POST if post else None, prefix='cases', valid_files=files,
                                  queryset=ProblemTestCase.objects.filter(dataset_id=self.object.pk).order_by('order'))

    def get_valid_files(self, data, post=False):
        try:
            if post and 'problem-data-zipfile-clear' in self.request.POST:
                return []
            elif post and 'problem-data-zipfile' in self.request.FILES:
                return ZipFile(self.request.FILES['problem-data-zipfile']).namelist()
            elif data.zipfile:
                return ZipFile(data.zipfile.path).namelist()
        except BadZipfile:
            return []
        return []

    def get_file_content(self, data, file):

        zip = ZipFile(data.zipfile.path)
        return zip.read(file) or None

    def get_files_content(self, data):

        if data.zipfile:
            zip = ZipFile(data.zipfile.path)
            return [zip.read(file).decode('utf8') for file in zip.namelist()]
        else:
            return []

    def write_file_content(self, problem, data, case, type):

        if data.zipfile:

            # print('zip file exists')
            absolute_filename = data.zipfile.path

            if type=='input':
                if case.input_file:
                    remove_from_zip(absolute_filename, case.input_file)
            else:
                if case.output_file:
                    remove_from_zip(absolute_filename, case.output_file)

            zip = ZipFile(absolute_filename, mode='a')

            if type == 'input':
                case_name = 'testcase.' + str(case.order) + '.in'
                case_content = case.input_text
            else:
                case_name = 'testcase.' + str(case.order) + '.out'
                case_content = case.output_text

            new_case = io.StringIO()
            new_case.write(case_content)

            zip.writestr(case_name, new_case.getvalue())

            zip.close()

        else:

            # print('zip file not exists')
            relative_filename = problem.code + '/testcases.zip'
            absolute_filename = settings.DMOJ_PROBLEM_DATA_ROOT + relative_filename
            # print('creating: ' + absolute_filename)

            if not os.path.exists(settings.DMOJ_PROBLEM_DATA_ROOT + problem.code):
                os.makedirs(settings.DMOJ_PROBLEM_DATA_ROOT + problem.code)

            zip = ZipFile(absolute_filename, mode='w')

            if type == 'input':
                case_name = 'testcase.' + str(case.order) + '.in'
                case_content = case.input_text
            else:
                case_name = 'testcase.' + str(case.order) + '.out'
                case_content = case.output_text

            new_case = io.StringIO()
            new_case.write(case_content)

            zip.writestr(case_name, new_case.getvalue())

            zip.close()
            data.zipfile = relative_filename
            data.save()

        return data

    def get_context_data(self, **kwargs):
        context = super(ProblemDataView, self).get_context_data(**kwargs)
        if 'data_form' not in context:
            context['data_form'] = self.get_data_form()
            valid_files = context['valid_files'] = self.get_valid_files(context['data_form'].instance)
            context['data_form'].zip_valid = valid_files is not False
            context['cases_formset'] = self.get_case_formset(valid_files)
        context['files_content'] = mark_safe(self.get_files_content(context['data_form'].instance))
        context['valid_files_json'] = mark_safe(json.dumps(context['valid_files']))
        context['valid_files'] = set(context['valid_files'])
        context['all_case_forms'] = chain(context['cases_formset'], [context['cases_formset'].empty_form])
        return context

    def post(self, request, *args, **kwargs):
        self.object = problem = self.get_object()
        data_form = self.get_data_form(post=True)
        valid_files = self.get_valid_files(data_form.instance, post=True)
        data_form.zip_valid = valid_files is not False
        cases_formset = self.get_case_formset(valid_files, post=True)
        if data_form.is_valid() and cases_formset.is_valid():
            data = data_form.save()
            for case in cases_formset.save(commit=False):

                if case.input_file:
                    input_file_content = self.get_file_content(data, case.input_file)
                    # print(input_file_content)
                    # print("\n".join(case.input_text.splitlines()).encode('utf-8'))
                    if input_file_content == "\n".join(case.input_text.splitlines()).encode('utf-8'):
                        # print('same content, do nothing')
                        pass
                    else:
                        data = self.write_file_content(problem, data, case, 'input')
                else:
                    # print('no input file, check if text to create new file')
                    if case.input_text:
                        # print('input text available, create new file')
                        data = self.write_file_content(problem, data, case, 'input')
                        case.input_file = 'testcase.' + str(case.order) + '.in'
                    else:
                        # print('no input text available, do nothing')
                        pass

                if case.output_file:
                    output_file_content = self.get_file_content(data, case.output_file)
                    # print(output_file_content)
                    # print("\n".join(case.input_text.splitlines()).encode('utf-8'))
                    if output_file_content == "\n".join(case.input_text.splitlines()).encode('utf-8'):
                        # print('same content, do nothing')
                        pass
                    else:
                        data = self.write_file_content(problem, data, case, 'output')
                else:
                    # print('no output file, check if text to create new file')
                    if case.output_text:
                        # print('output text available, create new file')
                        data = self.write_file_content(problem, data, case, 'output')
                        case.output_file = 'testcase.' + str(case.order) + '.out'
                    else:
                        # print('no output text available, do nothing')
                        pass

                case.dataset_id = problem.id
                case.save()
            for case in cases_formset.deleted_objects:
                case.delete()
            valid_files = self.get_valid_files(data_form.instance, post=True)
            data_form.zip_valid = valid_files is not False
            data.save()
            ProblemDataCompiler.generate(problem, data, problem.cases.order_by('order'), valid_files)
            return HttpResponseRedirect(request.get_full_path())
        return self.render_to_response(self.get_context_data(data_form=data_form, cases_formset=cases_formset,
                                                             valid_files=valid_files))

    put = post

@login_required
def DownloadTestCase(request, problem, name):
    object = get_object_or_404(Problem, code=problem)
    if not object.is_editable_by(request.user):
        raise Http404()

    response = HttpResponse()


    data_object = get_object_or_404(ProblemData, problem=object)

    try:
        zip = ZipFile(data_object.zipfile.path)
        response.content = zip.read(name)
    except Exception:
        raise Http404()

    response['Content-Type'] = 'application/octet-stream'
    return response

@login_required
def problem_data_file(request, problem, path):
    object = get_object_or_404(Problem, code=problem)
    if not object.is_editable_by(request.user):
        raise Http404()

    response = HttpResponse()
    if hasattr(settings, 'DMOJ_PROBLEM_DATA_INTERNAL') and request.META.get('SERVER_SOFTWARE', '').startswith('nginx/'):
        response['X-Accel-Redirect'] = '%s/%s/%s' % (settings.DMOJ_PROBLEM_DATA_INTERNAL, problem, path)
    else:
        try:
            with problem_data_storage.open(os.path.join(problem, path), 'rb') as f:
                response.content = f.read()
        except IOError:
            raise Http404()

    response['Content-Type'] = 'application/octet-stream'
    return response

@login_required
def problem_init_view(request, problem):
    problem = get_object_or_404(Problem, code=problem)
    if not problem.is_editable_by(request.user):
        raise Http404()

    try:
        with problem_data_storage.open(os.path.join(problem.code, 'init.yml'), 'rb') as f:
            data = utf8text(f.read()).rstrip('\n')
    except IOError:
        raise Http404()

    return render(request, 'problem/yaml.html', {
        'raw_source': data, 'highlighted_source': highlight_code(data, 'yaml'),
        'title': _('Generated init.yml for %s') % problem.name,
        'content_title': mark_safe(escape(_('Generated init.yml for %s')) % (
            format_html('<a href="{1}">{0}</a>', problem.name,
                        reverse('problem_detail', args=[problem.code])))),
    })
