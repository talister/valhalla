from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import ugettext as _
from django.shortcuts import redirect
from django.contrib import messages

from valhalla.accounts.forms import UserForm, ProfileForm


class UserUpdateView(LoginRequiredMixin, TemplateView):
    template_name = 'auth/user_form.html'

    def get(self, request):
        context = self.get_context_data(
            user_form=UserForm(instance=self.request.user),
            profile_form=ProfileForm(instance=self.request.user.profile)
        )
        return super().render_to_response(context)

    def post(self, request):
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, _('Profile successfully updated'))
            return redirect('index')
        else:
            context = self.get_context_data(user_form=user_form, profile_form=profile_form)
            return super().render_to_response(context)