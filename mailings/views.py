# views.py
from django.views.generic import FormView
from unfold.views import UnfoldModelAdminViewMixin
from django import forms

class FeedbackForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'unfold-input'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'unfold-input'})
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'unfold-textarea'})
    )

class FeedbackView(UnfoldModelAdminViewMixin, FormView):
    title = "Форма обратной связи"
    template_name = "admin/feedback_form.html"
    form_class = FeedbackForm
    permission_required = ()
    
    def form_valid(self, form):
        name = form.cleaned_data['name']
        email = form.cleaned_data['email']
        message = form.cleaned_data['message']
        
        print(f"Получено сообщение от {name} ({email}): {message}")
        
        from django.contrib import messages
        messages.success(self.request, 'Сообщение успешно отправлено')
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return self.model_admin.get_admin_url('changelist')